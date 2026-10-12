"""
IPRED Chatbot - Ejecutor seguro de herramientas de IA.
Valida permisos, aplica identidades autenticadas y controla el consumo de tokens.
"""

import logging
from typing import Dict, Any, Union, List

from app.tools.tool_definitions import ToolName
from app.db.repositories.student_repository import student_repo
from app.services import info_fija_service, busqueda_web_service, perfil_service

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Ejecutor centralizado y seguro de herramientas."""

    @staticmethod
    async def execute(tool_name: str, args: Dict[str, Any], codigo_est: int) -> Union[Dict[str, Any], List[Any]]:
        """
        Ejecuta la herramienta especificada garantizando que las consultas de datos personales
        utilicen estrictamente el `codigo_est` autenticado, previniendo suplantación.
        """
        # Redactar información en logs de observabilidad
        logger.info("Ejecutando tool: %s con args: %s (estudiante autenticado: %d)", tool_name, args, codigo_est)

        try:
            # 1. Consultar horario
            if tool_name == ToolName.CONSULTAR_HORARIO.value:
                if not codigo_est or codigo_est <= 0:
                    return {"mensaje": "No se ha identificado una sesión de estudiante activa para consultar horarios."}

                fecha = args.get("fecha")
                horario = await student_repo.get_student_schedule(codigo_est, fecha=fecha)
                if not horario:
                    return {"mensaje": "No se encontraron tutorías o clases programadas para los criterios seleccionados."}

                # Si no se solicitó una fecha histórica específica, filtrar solo sesiones de hoy en adelante
                if not fecha:
                    from app.config import get_colombia_now
                    today_str = get_colombia_now().date().isoformat()
                    future_h = [h for h in horario if str(h.fecha_tutoria) >= today_str]
                    if future_h:
                        horario = future_h

                # Compresión compacta estructurada con código de asignatura para Gemini
                compressed = [
                    f"Código: {h.codigo_asignatura} | {h.nombre_asignatura} (G{h.grupo}) | Fecha: {h.fecha_tutoria} | Horario: {str(h.hora_inicio)[:5]}-{str(h.hora_fin)[:5]} | Docente: {h.profesor or 'Por asignar'} ({h.correo_profesor or 'Sin correo'}) | Modalidad: [{h.tipo_tutoria or 'Tutoría'}]"
                    for h in horario[:8]
                ]
                return {"horario_tutorias": compressed}

            # 2. Consultar asignaturas y docentes
            elif tool_name == ToolName.CONSULTAR_ASIGNATURAS.value:
                if not codigo_est or codigo_est <= 0:
                    return {"mensaje": "No se ha identificado una sesión de estudiante activa."}

                asignaturas = await student_repo.get_enrolled_subjects(codigo_est)
                if not asignaturas:
                    return {"mensaje": "No tienes asignaturas matriculadas registradas en el sistema."}

                resumen = [
                    f"Código: {a.codigo_asignatura} | Asignatura: {a.nombre_asignatura} (Grupo {a.grupo}) | Docente: {a.profesor or 'No asignado'} ({a.correo_profesor or 'Sin correo'})"
                    for a in asignaturas
                ]
                return {"asignaturas_matriculadas": resumen}

            # 3. Búsqueda en conocimiento institucional fijo (FTS5 / JSON)
            elif tool_name == ToolName.BUSCAR_INFORMACION_FIJA.value:
                texto = args.get("texto_busqueda", "").strip()
                if not texto:
                    return {"error": "El texto de búsqueda es obligatorio."}

                categoria = args.get("categoria")
                resultados = await info_fija_service.buscar_fts5(texto, limite=2)
                if resultados:
                    return {
                        "informacion_institucional": [
                            {"titulo": r["titulo"], "contenido": r["contenido"][:800], "categoria": r.get("categoria", "")}
                            for r in resultados
                        ]
                    }
                return {"mensaje": "No se encontró información institucional directa sobre ese tema."}

            # 4. Obtener perfil de usuario
            elif tool_name == ToolName.OBTENER_PERFIL_USUARIO.value:
                if not codigo_est or codigo_est <= 0:
                    return {"mensaje": "Usuario invitado sin perfil registrado."}
                perfil = await student_repo.get_profile_by_code(codigo_est)
                if perfil:
                    return {
                        "estudiante": perfil.nombre_completo,
                        "programa": perfil.nombre_programa,
                        "sede": perfil.nombre_sede,
                        "grupo": perfil.grupo,
                    }
                return {"mensaje": "No se encontró ficha de perfil para este código."}

            # 5. Actualizar perfil de usuario
            elif tool_name == ToolName.ACTUALIZAR_PERFIL_USUARIO.value:
                return await perfil_service.actualizar_perfil(codigo_est, args)

            # 6. Listar sedes
            elif tool_name == ToolName.LISTAR_SEDES.value:
                sedes = await info_fija_service.obtener_sedes()
                return [
                    {"codigo": s["codigo_sede"] if "codigo_sede" in s else s.get("codigo"),
                     "nombre": s["nombre"],
                     "municipio": s.get("municipio", s.get("ciudad", ""))}
                    for s in sedes
                ]

            # 7. Listar programas
            elif tool_name == ToolName.LISTAR_PROGRAMAS.value:
                programas = await info_fija_service.obtener_programas()
                return [
                    {"codigo": p.get("codigo_programa", p.get("codigo")),
                     "nombre": p["nombre"],
                     "nivel": p.get("nivel_formacion", p.get("nivel", ""))}
                    for p in programas
                ]

            # 8. Búsqueda web
            elif tool_name == ToolName.BUSCAR_INFORMACION_WEB.value:
                consulta = args.get("consulta", "").strip()
                if not consulta:
                    return {"error": "Consulta vacía."}
                return await busqueda_web_service.buscar_web_local(consulta)

            # 9. Leer página web (protegida con whitelist SSRF)
            elif tool_name == ToolName.LEER_PAGINA_WEB.value:
                url = args.get("url", "").strip()
                if not url:
                    return {"error": "URL vacía."}
                contenido = await busqueda_web_service.leer_pagina_web(url)
                return {"contenido_extraido": contenido if contenido else "No fue posible extraer texto de la página solicitada."}

            else:
                logger.warning("Herramienta no reconocida: %s", tool_name)
                return {"error": f"Herramienta no reconocida: {tool_name}"}

        except Exception as ex:
            logger.error("Error no controlado ejecutando tool %s: %s", tool_name, ex)
            return {"error": f"Ocurrió un error al consultar los datos requeridos."}


tool_executor = ToolExecutor()
