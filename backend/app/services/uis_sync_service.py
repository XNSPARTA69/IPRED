"""
IPRED Chatbot - Servicio de Sincronización Global con el Portal UIS (Cronograma Público).
Consume los endpoints web oficiales de la UIS, normaliza datos y los almacena en SQLite en modo WAL.
Diseñado para alta resiliencia ante caídas de red o servidor UIS (Zero-AI tokens, $0.00 costo).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import httpx
import aiosqlite

from app.db.database import get_db
from app.config import get_colombia_now

logger = logging.getLogger(__name__)

# Configuración institucional por defecto
DEFAULT_SEMESTRE = "20262"  # Semestre 2026-2
DEFAULT_FECHA_INICIO = "2026-07-13"
DEFAULT_FECHA_FIN = "2027-02-16"
DEFAULT_SYNC_INTERVAL_SECONDS = 1800  # 30 minutos

UIS_BASE_URL = "https://ipredtic.uis.edu.co/plataformaticv2/"
ENDPOINT_SEDES_PROG = f"{UIS_BASE_URL}?ajax=CronogramaPublico&action=consultarSedesProgramas"
ENDPOINT_BUSCAR_CRONO = f"{UIS_BASE_URL}?ajax=CronogramaPublico&action=buscarCronograma"

# Mapeo oficial de códigos de actividad UIS
ACTIVITY_TYPE_MAP = {
    "1": "TP - Presencial",
    "5": "E - Examen",
    "6": "O - Opcional",
    "9": "S-S - Sustentación",
    "14": "BD - Biblioteca",
    "43": "Tutoría Remota",
    "49": "AA-A - Asincrónica",
    "51": "AH - Aula Híbrida",
}


class UISSyncService:
    """Sincronizador resiliente de cronogramas y asignaturas desde la UIS."""

    def __init__(self):
        self._is_syncing: bool = False
        self._background_task: Optional[asyncio.Task] = None

    @property
    def is_syncing(self) -> bool:
        return self._is_syncing

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_syncing": self._is_syncing,
            "has_background_task": self._background_task is not None and not self._background_task.done(),
            "sync_interval_seconds": DEFAULT_SYNC_INTERVAL_SECONDS,
            "semestre": DEFAULT_SEMESTRE,
        }

    async def fetch_sedes_and_programs(
        self, client: httpx.AsyncClient, semestre: str = DEFAULT_SEMESTRE
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Consulta los programas y sedes activos para el semestre en la UIS.
        El endpoint devuelve una lista con 2 elementos: [programas, sedes].
        """
        payload = {"semestre": str(semestre)}
        for intento in range(1, 4):
            try:
                response = await client.post(ENDPOINT_SEDES_PROG, data=payload, timeout=12.0)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) >= 2:
                        programas = data[0] or []
                        sedes = data[1] or []
                        return programas, sedes
                    elif isinstance(data, dict):
                        return data.get("programas", []), data.get("sedes", [])
                else:
                    logger.warning("Intento %d: UIS respondió status %d en sedes/programas", intento, response.status_code)
            except Exception as e:
                logger.warning("Intento %d: Error consultando sedes/programas UIS: %s", intento, e)
            await asyncio.sleep(intento * 1.0)

        logger.error("No se pudo obtener la lista de sedes y programas de la UIS.")
        return [], []

    async def fetch_cronograma_node(
        self,
        client: httpx.AsyncClient,
        semestre: str,
        id_programa: str,
        id_sede: str,
        jornada: str = "1",
        fecha_inicio: str = DEFAULT_FECHA_INICIO,
        fecha_fin: str = DEFAULT_FECHA_FIN,
    ) -> List[Any]:
        """
        Descarga el cronograma para una combinación (programa, sede, jornada).
        """
        payload = {
            "semestre": str(semestre),
            "programa": str(id_programa),
            "sede": str(id_sede),
            "jornada": str(jornada),
            "fechaInicial": fecha_inicio,
            "fechaFinal": fecha_fin,
        }
        for intento in range(1, 3):
            try:
                response = await client.post(ENDPOINT_BUSCAR_CRONO, data=payload, timeout=18.0)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "cronograma" in data:
                        return data["cronograma"]
                    return []
            except Exception as e:
                logger.debug("Error descargando cronograma prog=%s sede=%s intento %d: %s", id_programa, id_sede, intento, e)
            await asyncio.sleep(0.5)
        return []

    def _extract_records_from_tree(
        self, raw_data: List[Any], semestre_int: int, codigo_programa: int, codigo_sede: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extrae asignaturas y sesiones de horarios normalizados a partir del árbol JSON de la UIS.
        Estructura oficial:
        - raw_data[0]: Diccionario {prog_id: {jornada: [cursos]}}
        - raw_data[3]: Diccionario {prog_id: {'plan': [...], 'electivas': [...]}} para nombres oficiales
        """
        asignaturas_map: Dict[str, Dict[str, Any]] = {}
        horarios_list: List[Dict[str, Any]] = []

        if not raw_data or not isinstance(raw_data, list):
            return [], []

        # 1. Mapa de nombres de asignaturas desde el catálogo (raw_data[3])
        names_map: Dict[int, str] = {}
        if len(raw_data) > 3 and isinstance(raw_data[3], dict):
            prog_plan = raw_data[3].get(str(codigo_programa), {})
            if isinstance(prog_plan, dict):
                for item in prog_plan.get("plan", []) + prog_plan.get("electivas", []):
                    if isinstance(item, dict) and "codigo" in item:
                        try:
                            names_map[int(item["codigo"])] = (item.get("nombre") or "").strip()
                        except ValueError:
                            pass

        # 2. Cursos y Actividades desde raw_data[0]
        courses_root = raw_data[0] if len(raw_data) > 0 and isinstance(raw_data[0], dict) else {}
        prog_courses = courses_root.get(str(codigo_programa), {}) if isinstance(courses_root, dict) else {}

        # Iterar jornadas ("1": Sábados, "2": Noches, etc.)
        for jornada_key, courses in prog_courses.items():
            if not isinstance(courses, list):
                continue

            for course in courses:
                if not isinstance(course, dict):
                    continue

                cod_asig = course.get("codigo_asignatura")
                grupo = str(course.get("grupo") or "0").strip()
                if not cod_asig:
                    continue

                try:
                    cod_asig_int = int(cod_asig)
                except ValueError:
                    continue

                nom_asig = (course.get("nombre_asignatura") or names_map.get(cod_asig_int) or f"Asignatura {cod_asig_int}").strip()
                docente = (course.get("nombre_profesor") or "").strip()

                asig_key = f"{codigo_programa}_{codigo_sede}_{cod_asig_int}_{grupo}_{semestre_int}"
                asignaturas_map[asig_key] = {
                    "codigo_programa": codigo_programa,
                    "nombre_programa": course.get("nombre_programa", ""),
                    "codigo_sede": codigo_sede,
                    "codigo_asignatura": cod_asig_int,
                    "nombre_asignatura": nom_asig,
                    "id_semestre": semestre_int,
                    "grupo": grupo,
                    "nombre_completo": docente,
                    "correo_institucional": "",
                }

                # Sesiones de tutoría y actividades
                actividades = course.get("actividades", []) or course.get("tutoria", [])
                if isinstance(actividades, list):
                    for act in actividades:
                        if not isinstance(act, dict):
                            continue

                        f_ini_str = str(act.get("fecha_inicio") or "").strip()
                        f_fin_str = str(act.get("fecha_fin") or "").strip()

                        if not f_ini_str or not f_fin_str:
                            continue

                        partes_ini = f_ini_str.split()
                        partes_fin = f_fin_str.split()

                        fecha_tutoria = partes_ini[0]
                        hora_inicio = partes_ini[1][:5] if len(partes_ini) > 1 else "00:00"
                        hora_fin = partes_fin[1][:5] if len(partes_fin) > 1 else "00:00"

                        tipo_desc = act.get("nombre_tipo_actividad") or ACTIVITY_TYPE_MAP.get(
                            str(act.get("codigo_tipo_actividad") or ""), "Tutoría"
                        )

                        horarios_list.append({
                            "codigo_asignatura": cod_asig_int,
                            "grupo": grupo,
                            "fecha_tutoria": fecha_tutoria,
                            "hora_inicio": hora_inicio,
                            "hora_fin": hora_fin,
                            "tipo_tutoria": tipo_desc,
                        })

        return list(asignaturas_map.values()), horarios_list

    async def execute_full_sync(
        self,
        semestre: str = DEFAULT_SEMESTRE,
        fecha_inicio: str = DEFAULT_FECHA_INICIO,
        fecha_fin: str = DEFAULT_FECHA_FIN,
        is_manual: bool = False,
    ) -> Dict[str, Any]:
        """
        Ejecuta la sincronización global completa contra la plataforma UIS.
        Asegura transaccionalidad atómica y persistencia en SQLite sin bloquear lecturas.
        """
        if self._is_syncing:
            logger.info("Sincronización UIS ya en curso. Omitiendo invocación duplicada.")
            return {"status": "ALREADY_RUNNING", "mensaje": "Sincronización en curso."}

        self._is_syncing = True
        inicio_dt = get_colombia_now()
        db = await get_db()

        # Registrar inicio en sync_metadata con zona horaria de Colombia
        cursor = await db.execute(
            """INSERT INTO sync_metadata (semestre, inicio_sync, estado)
               VALUES (?, ?, 'EN_PROCESO')""",
            (semestre, inicio_dt.isoformat()),
        )
        sync_id = cursor.lastrowid
        await db.commit()

        logger.info("=== INICIANDO SINCRONIZACIÓN GLOBAL UIS (Semestre: %s, ID: %d) ===", semestre, sync_id)

        semestre_int = int(semestre) if semestre.isdigit() else 20262
        total_asig_count = 0
        total_horarios_count = 0
        programas_count = 0
        sedes_count = 0
        error_msg: Optional[str] = None

        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "IPRED-Chatbot-Sync/1.0 (UIS-Academic-Assistant)"},
                follow_redirects=True,
            ) as client:
                programas, sedes = await self.fetch_sedes_and_programs(client, semestre=semestre)

                if not programas or not sedes:
                    raise RuntimeError("No se obtuvieron sedes o programas válidos desde el portal UIS.")

                programas_count = len(programas)
                sedes_count = len(sedes)
                logger.info("Encontrados %d programas y %d sedes para sincronizar.", programas_count, sedes_count)

                # Semáforo para controlar concurrencia de peticiones a la UIS
                semaphore = asyncio.Semaphore(16)

                async def sync_one(prog: Dict, sede: Dict, jornada: str) -> Tuple[List[Dict], List[Dict]]:
                    p_id = str(prog.get("CodigoPrograma") or prog.get("id_programa") or prog.get("id") or "")
                    s_id = str(sede.get("CodigoSede") or sede.get("id_sede") or sede.get("id") or "")
                    if not p_id or not s_id:
                        return [], []

                    async with semaphore:
                        raw = await self.fetch_cronograma_node(
                            client, semestre, p_id, s_id, jornada, fecha_inicio, fecha_fin
                        )
                        if not raw:
                            return [], []

                        p_int = int(p_id) if p_id.isdigit() else 0
                        s_int = int(s_id) if s_id.isdigit() else 0
                        return self._extract_records_from_tree(raw, semestre_int, p_int, s_int)

                # Construir matriz de tareas
                tasks = []
                for p in programas:
                    for s in sedes:
                        for j in ["1", "2"]:  # Jornada Sábados (1) y Noches (2)
                            tasks.append(sync_one(p, s, j))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                all_asignaturas: Dict[str, Dict[str, Any]] = {}
                all_horarios: Dict[str, Dict[str, Any]] = {}

                for res in results:
                    if isinstance(res, Exception):
                        logger.warning("Excepción en hilo de descarga: %s", res)
                        continue
                    asigs, hors = res
                    for a in asigs:
                        k = f"{a['codigo_programa']}_{a['codigo_sede']}_{a['codigo_asignatura']}_{a['grupo']}_{a['id_semestre']}"
                        all_asignaturas[k] = a
                    for h in hors:
                        hk = f"{h['codigo_asignatura']}_{h['grupo']}_{h['fecha_tutoria']}_{h['hora_inicio']}"
                        all_horarios[hk] = h

                total_asig_count = len(all_asignaturas)
                total_horarios_count = len(all_horarios)

                logger.info("Descarga completada: %d asignaturas y %d sesiones de horario.", total_asig_count, total_horarios_count)

                # Inserción y actualización atómica en lotes no bloqueantes (Batching para alta concurrencia)
                BATCH_SIZE = 250
                if all_asignaturas:
                    asig_rows = [
                        (
                            int(a["codigo_programa"]) if str(a.get("codigo_programa", "")).isdigit() else 0,
                            str(a.get("nombre_programa", "")),
                            int(a["codigo_sede"]) if str(a.get("codigo_sede", "")).isdigit() else 0,
                            str(a["codigo_asignatura"]),
                            str(a.get("nombre_asignatura", "")),
                            str(a.get("id_semestre", "20262")),
                            str(a.get("grupo", "0")),
                            str(a.get("nombre_completo", "")),
                            str(a.get("correo_institucional", ""))
                        )
                        for a in all_asignaturas.values()
                    ]
                    for i in range(0, len(asig_rows), BATCH_SIZE):
                        chunk = asig_rows[i:i + BATCH_SIZE]
                        await db.executemany(
                            """INSERT OR REPLACE INTO asignaturas (
                                codigo_programa, nombre_programa, codigo_sede,
                                codigo_asignatura, nombre_asignatura, id_semestre,
                                grupo, nombre_completo, correo_institucional
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            chunk,
                        )
                        await db.commit()
                        await asyncio.sleep(0.005)

                if all_horarios:
                    hor_rows = [
                        (
                            str(h["codigo_asignatura"]), str(h["grupo"]), h["fecha_tutoria"],
                            h["hora_inicio"], h["hora_fin"], h["tipo_tutoria"]
                        )
                        for h in all_horarios.values()
                    ]
                    for i in range(0, len(hor_rows), BATCH_SIZE):
                        chunk = hor_rows[i:i + BATCH_SIZE]
                        await db.executemany(
                            """INSERT OR REPLACE INTO horarios (
                                codigo_asignatura, grupo, fecha_tutoria,
                                hora_inicio, hora_fin, tipo_tutoria
                            ) VALUES (?, ?, ?, ?, ?, ?)""",
                            chunk,
                        )
                        await db.commit()
                        await asyncio.sleep(0.005)

                # Refrescar vista materializada de carga de estudiantes
                try:
                    await db.execute("REFRESH MATERIALIZED VIEW vista_carga_estudiantes;")
                except Exception as ex_view:
                    logger.warning("No se pudo refrescar vista materializada: %s", ex_view)

        except Exception as e:
            error_msg = str(e)
            logger.error("Error crítico durante la sincronización UIS: %s", e, exc_info=True)

        finally:
            fin_dt = get_colombia_now()
            estado_final = "EXITOSO" if error_msg is None else "FALLIDO"

            await db.execute(
                """UPDATE sync_metadata
                   SET fin_sync = ?, estado = ?, programas_procesados = ?,
                       sedes_procesadas = ?, asignaturas_actualizadas = ?,
                       horarios_actualizados = ?, error_detalle = ?
                   WHERE id = ?""",
                (
                    fin_dt.isoformat(), estado_final, programas_count,
                    sedes_count, total_asig_count, total_horarios_count,
                    error_msg, sync_id
                ),
            )
            await db.commit()
            self._is_syncing = False

        duration = (get_colombia_now() - inicio_dt).total_seconds()
        logger.info(
            "=== SINCRONIZACIÓN FINALIZADA (%s en %.2fs) - Asignaturas: %d, Horarios: %d ===",
            estado_final, duration, total_asig_count, total_horarios_count
        )

        return {
            "sync_id": sync_id,
            "estado": estado_final,
            "duracion_segundos": duration,
            "programas": programas_count,
            "sedes": sedes_count,
            "asignaturas_guardadas": total_asig_count,
            "horarios_guardados": total_horarios_count,
            "error": error_msg,
        }

    async def get_latest_sync_status(self) -> Dict[str, Any]:
        """Consulta el último estado de sincronización registrado."""
        db = await get_db()
        cursor = await db.execute(
            """SELECT id, semestre, inicio_sync, fin_sync, estado,
                      programas_procesados, sedes_procesadas,
                      asignaturas_actualizadas, horarios_actualizados, error_detalle
               FROM sync_metadata
               ORDER BY id DESC LIMIT 1"""
        )
        row = await cursor.fetchone()
        if not row:
            return {"estado": "SIN_REGISTRO", "mensaje": "No hay sincronizaciones previas registradas."}
        return dict(row)

    async def start_periodic_sync(self, interval_seconds: int = DEFAULT_SYNC_INTERVAL_SECONDS):
        """Tarea en segundo plano que corre periódicamente de forma no bloqueante."""
        logger.info("Iniciando cron asíncrono de sincronización UIS (intervalo: %ds)", interval_seconds)
        try:
            db = await get_db()
            c = await db.execute("SELECT COUNT(*) FROM horarios")
            count = (await c.fetchone())[0]
            if count > 0:
                logger.info("Base de datos ya cuenta con %d horarios sincronizados. Siguiente ciclo en %ds.", count, interval_seconds)
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("Error comprobando estado previo de base de datos: %s", e)

        while True:
            try:
                await self.execute_full_sync()
            except asyncio.CancelledError:
                logger.info("Cron de sincronización UIS detenido.")
                break
            except Exception as e:
                logger.error("Error no capturado en cron de sincronización UIS: %s", e)
            await asyncio.sleep(interval_seconds)


uis_sync_service = UISSyncService()

