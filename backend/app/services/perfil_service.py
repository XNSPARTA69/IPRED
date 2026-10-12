"""
IPRED Chatbot - Servicio de perfil de usuario.
Integrado con el repositorio de estudiantes normalizado.
"""

import logging
from typing import Dict, Any, List, Optional
from app.db.repositories.student_repository import student_repo

logger = logging.getLogger(__name__)


async def obtener_perfil(codigo_est: int) -> Dict[str, Any]:
    """Obtiene el perfil del estudiante normalizado."""
    if not codigo_est or codigo_est <= 0:
        return {"usuario_id": 0}

    profile = await student_repo.get_profile_by_code(codigo_est)
    if not profile:
        return {"usuario_id": codigo_est}

    return {
        "usuario_id": profile.codigo_est,
        "codigo_est": profile.codigo_est,
        "primer_nombre": profile.primer_nombre,
        "primer_apellido": profile.primer_apellido,
        "nombre_completo": profile.nombre_completo,
        "programa_codigo": str(profile.programa_academico or ""),
        "programa_nombre": profile.nombre_programa,
        "sede_codigo": str(profile.codigo_sede or ""),
        "sede_nombre": profile.nombre_sede,
        "grupo": profile.grupo,
    }


async def actualizar_perfil(codigo_est: int = 0, datos: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    La información académica oficial es gestionada por la universidad.
    Esta función registra preferencias del estudiante en sesión.
    """
    target_code = codigo_est or user_id or 0
    logger.info("Registro de preferencias de perfil para estudiante: %d", target_code)
    return await obtener_perfil(target_code)


async def obtener_perfil_resumen(codigo_est: int) -> Dict[str, Any]:
    """Devuelve un resumen mínimo del perfil para consumo de la IA."""
    perfil = await obtener_perfil(codigo_est)
    resumen = {}
    if perfil.get("sede_nombre"):
        resumen["sede"] = perfil["sede_nombre"]
    if perfil.get("programa_nombre"):
        resumen["programa"] = perfil["programa_nombre"]
    if perfil.get("grupo"):
        resumen["grupo"] = perfil["grupo"]
    if perfil.get("primer_nombre"):
        resumen["nombre"] = perfil["primer_nombre"]
    return resumen
