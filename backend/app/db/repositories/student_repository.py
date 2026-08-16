"""
IPRED Chatbot - Repositorio de estudiantes.
Aísla las consultas SQL directas sobre las tablas de estudiantes y usuarios.
"""
import json
import logging
from typing import Optional, List, Dict, Tuple, Any, Set
import aiosqlite

from app.db.database import get_db
from app.models.academic import StudentProfile, Subject, ScheduleItem

logger = logging.getLogger(__name__)

# Micro-caché en memoria RAM para perfiles (sub-milisegundo)
_PROFILE_CACHE: Dict[int, StudentProfile] = {}
_SUBJECTS_CACHE: Dict[int, List[Subject]] = {}


class StudentRepository:
    """Acceso a datos de estudiantes y su carga académica con aceleración por Vistas Materializadas."""

    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db

    async def _get_conn(self) -> aiosqlite.Connection:
        if self._db is not None:
            return self._db
        return await get_db()

    async def get_profile_by_code(self, codigo_est: int) -> Optional[StudentProfile]:
        """Obtiene el perfil del estudiante con micro-caché y vista materializada."""
        if not codigo_est or codigo_est <= 0:
            return None

        # 1. Micro-caché en RAM (0.01 ms)
        if codigo_est in _PROFILE_CACHE:
            return _PROFILE_CACHE[codigo_est]

        db = await self._get_conn()

        # 2. Intento vía Vista Materializada Pre-calculada (0.2 ms)
        try:
            cur_mat = await db.execute(
                "SELECT perfil_academico FROM vista_carga_estudiantes WHERE codigo_est = ?",
                (codigo_est,),
            )
            row_mat = await cur_mat.fetchone()
            if row_mat:
                raw = row_mat["perfil_academico"]
                data = json.loads(raw) if isinstance(raw, str) else dict(raw)
                p_nombre = data.get("primer_nombre") or ""
                p_apellido = data.get("primer_apellido") or ""
                profile = StudentProfile(
                    codigo_est=data["codigo_est"],
                    primer_nombre=p_nombre,
                    primer_apellido=p_apellido,
                    nombre_completo=f"{p_nombre} {p_apellido}".strip(),
                    programa_academico=data.get("programa_academico"),
                    nombre_programa=data.get("nombre_programa"),
                    codigo_sede=data.get("codigo_sede"),
                    nombre_sede=data.get("nombre_sede"),
                    grupo=data.get("grupo"),
                )
                _PROFILE_CACHE[codigo_est] = profile
                return profile
        except Exception:
            pass

        # 3. Fallback a tabla relacional
        query = """
            SELECT 
                codigo_est,
                TRIM(primer_nombre) as primer_nombre,
                TRIM(primer_apellido) as primer_apellido,
                programa_academico,
                TRIM(nombre_programa) as nombre_programa,
                codigo_sede,
                TRIM(nombre_sede) as nombre_sede,
                TRIM(grupo) as grupo
            FROM estudiantes
            WHERE codigo_est = ?
            LIMIT 1
        """
        try:
            cursor = await db.execute(query, (codigo_est,))
            row = await cursor.fetchone()
            if not row:
                return None

            data = dict(row)
            p_nombre = data.get("primer_nombre") or ""
            p_apellido = data.get("primer_apellido") or ""
            nombre_completo = f"{p_nombre} {p_apellido}".strip()

            profile = StudentProfile(
                codigo_est=data["codigo_est"],
                primer_nombre=p_nombre,
                primer_apellido=p_apellido,
                nombre_completo=nombre_completo,
                programa_academico=data.get("programa_academico"),
                nombre_programa=data.get("nombre_programa"),
                codigo_sede=data.get("codigo_sede"),
                nombre_sede=data.get("nombre_sede"),
                grupo=data.get("grupo"),
            )
            _PROFILE_CACHE[codigo_est] = profile
            return profile
        except Exception as e:
            logger.error("Error consultando perfil de estudiante %d: %s", codigo_est, e)
            return None

    async def get_enrolled_subjects(self, codigo_est: int) -> List[Subject]:
        """Obtiene todas las asignaturas matriculadas vía Vista Materializada pre-calculada."""
        if not codigo_est or codigo_est <= 0:
            return []

        # 1. Micro-caché en RAM
        if codigo_est in _SUBJECTS_CACHE:
            return _SUBJECTS_CACHE[codigo_est]

        db = await self._get_conn()

        # 2. Vista Materializada Pre-calculada (JSONB Instantáneo)
        try:
            cur_mat = await db.execute(
                "SELECT perfil_academico FROM vista_carga_estudiantes WHERE codigo_est = ?",
                (codigo_est,),
            )
            row_mat = await cur_mat.fetchone()
            if row_mat:
                raw = row_mat["perfil_academico"]
                data = json.loads(raw) if isinstance(raw, str) else dict(raw)
                asigs = data.get("asignaturas", [])
                result = [
                    Subject(
                        codigo_asignatura=str(a.get("codigo_asignatura")),
                        nombre_asignatura=a.get("nombre_asignatura"),
                        grupo=a.get("grupo"),
                        nombre_programa=data.get("nombre_programa"),
                        profesor=a.get("profesor"),
                        correo_profesor=a.get("correo_profesor"),
                        id_semestre=str(a.get("id_semestre") or ""),
                    )
                    for a in asigs
                ]
                _SUBJECTS_CACHE[codigo_est] = result
                return result
        except Exception:
            pass

        # 3. Fallback a consulta relacional deduplicada y optimizada
        query = """
            SELECT DISTINCT
                TRIM(e.codigo_asignatura) as codigo_asignatura,
                TRIM(e.nombre_asignatura) as nombre_asignatura,
                TRIM(e.grupo) as grupo,
                TRIM(e.nombre_programa) as nombre_programa,
                TRIM(a.nombre_completo) as profesor,
                TRIM(a.correo_institucional) as correo_profesor,
                a.id_semestre
            FROM estudiantes e
            LEFT JOIN asignaturas a 
                ON TRIM(e.codigo_asignatura) = TRIM(a.codigo_asignatura)
                AND TRIM(e.grupo) = TRIM(a.grupo)
            WHERE e.codigo_est = ?
            ORDER BY codigo_asignatura ASC
        """
        try:
            cursor = await db.execute(query, (codigo_est,))
            rows = await cursor.fetchall()
            if not rows:
                return []

            # Agrupar estrictamente por asignatura y grupo
            grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
            for r in rows:
                cod_asig = str(r["codigo_asignatura"]).strip()
                grp = str(r["grupo"]).strip()
                key = (cod_asig, grp)
                if key not in grouped:
                    raw_sem = str(r["id_semestre"] or "").strip()
                    sem_val = int(raw_sem) if raw_sem.isdigit() else None
                    grouped[key] = {
                        "codigo_asignatura": int(cod_asig) if cod_asig.isdigit() else 0,
                        "nombre_asignatura": str(r["nombre_asignatura"]).strip().upper(),
                        "grupo": grp,
                        "nombre_programa": str(r["nombre_programa"] or "").strip(),
                        "profesores": set(),
                        "correos": set(),
                        "id_semestre": sem_val,
                    }
                prof = str(r["profesor"] or "").strip()
                correo = str(r["correo_profesor"] or "").strip()
                if prof:
                    grouped[key]["profesores"].add(prof)
                if correo and "@" in correo:
                    grouped[key]["correos"].add(correo.lower())

            result = []
            for item in grouped.values():
                profs_list = sorted(list(item["profesores"]))
                correos_list = sorted(list(item["correos"]))
                docente_final = " / ".join(profs_list) if profs_list else "Docente Titular UIS"
                correo_final = " / ".join(correos_list) if correos_list else "Coordinación IPRED"
                
                result.append(
                    Subject(
                        codigo_asignatura=item["codigo_asignatura"],
                        nombre_asignatura=item["nombre_asignatura"],
                        grupo=item["grupo"],
                        nombre_programa=item["nombre_programa"],
                        profesor=docente_final,
                        correo_profesor=correo_final,
                        id_semestre=item["id_semestre"],
                    )
                )

            _SUBJECTS_CACHE[codigo_est] = result
            return result
        except Exception as e:
            logger.error("Error consultando asignaturas de estudiante %d: %s", codigo_est, e)
            return []

    async def get_student_schedule(self, codigo_est: int, fecha: Optional[str] = None) -> List[ScheduleItem]:
        """Consulta el cronograma/horario de tutorías del estudiante sin duplicados y con nombres limpios."""
        if not codigo_est or codigo_est <= 0:
            return []

        db = await self._get_conn()
        try:
            # 1. Obtener las asignaturas y grupos que el estudiante tiene realmente matriculadas
            enrolled_query = """
                SELECT DISTINCT codigo_asignatura, TRIM(grupo) as grupo, TRIM(nombre_asignatura) as nombre_asignatura
                FROM estudiantes
                WHERE codigo_est = ?
            """
            cursor = await db.execute(enrolled_query, (codigo_est,))
            enrolled_rows = await cursor.fetchall()
            if not enrolled_rows:
                return []

            enrolled_map = {(r["codigo_asignatura"], r["grupo"]): r["nombre_asignatura"] for r in enrolled_rows}

            # 2. Consultar horarios para las materias matriculadas
            placeholders = ",".join(["(?, ?)"] * len(enrolled_map))
            flat_params = [item for k in enrolled_map.keys() for item in k]

            schedule_query = f"""
                SELECT DISTINCT
                    h.codigo_asignatura,
                    TRIM(h.grupo) as grupo,
                    h.fecha_tutoria,
                    h.hora_inicio,
                    h.hora_fin,
                    h.tipo_tutoria
                FROM horarios h
                WHERE (h.codigo_asignatura, TRIM(h.grupo)) IN (VALUES {placeholders})
            """
            if fecha:
                schedule_query += " AND h.fecha_tutoria = ?"
                flat_params.append(fecha)

            schedule_query += " ORDER BY h.fecha_tutoria ASC, h.hora_inicio ASC"

            cursor = await db.execute(schedule_query, flat_params)
            horarios_rows = await cursor.fetchall()
            if not horarios_rows:
                return []

            # 3. Obtener el mapa de docentes y correos limpios
            prof_params = [item for k in enrolled_map.keys() for item in k]
            prof_query = f"""
                SELECT DISTINCT
                    a.codigo_asignatura,
                    TRIM(a.grupo) as grupo,
                    TRIM(a.nombre_completo) as profesor,
                    TRIM(a.correo_institucional) as correo
                FROM asignaturas a
                WHERE (a.codigo_asignatura, TRIM(a.grupo)) IN (VALUES {placeholders})
            """
            cursor = await db.execute(prof_query, prof_params)
            prof_rows = await cursor.fetchall()

            prof_map: Dict[Tuple[int, str], Dict[str, Set[str]]] = {}
            for pr in prof_rows:
                key = (pr["codigo_asignatura"], pr["grupo"])
                if key not in prof_map:
                    prof_map[key] = {"profesores": set(), "correos": set()}
                if pr["profesor"]:
                    clean_name = " ".join(pr["profesor"].strip().title().split())
                    prof_map[key]["profesores"].add(clean_name)
                if pr["correo"] and "@" in pr["correo"]:
                    prof_map[key]["correos"].add(pr["correo"].strip().lower())

            # 4. Construir lista final
            result = []
            for h in horarios_rows:
                key = (h["codigo_asignatura"], h["grupo"])
                p_info = prof_map.get(key, {"profesores": set(), "correos": set()})
                docente = " / ".join(sorted(p_info["profesores"])) if p_info["profesores"] else "Docente Titular UIS"
                correo = " / ".join(sorted(p_info["correos"])) if p_info["correos"] else None
                nombre_asig = enrolled_map.get(key) or "Tutoría"

                result.append(
                    ScheduleItem(
                        codigo_asignatura=h["codigo_asignatura"],
                        nombre_asignatura=nombre_asig,
                        grupo=h["grupo"],
                        profesor=docente,
                        correo_profesor=correo,
                        fecha_tutoria=str(h["fecha_tutoria"]),
                        hora_inicio=str(h["hora_inicio"]),
                        hora_fin=str(h["hora_fin"]),
                        tipo_tutoria=h["tipo_tutoria"],
                    )
                )

            return result
        except Exception as e:
            logger.error("Error consultando horario de estudiante %d: %s", codigo_est, e)
            return []


student_repo = StudentRepository()

