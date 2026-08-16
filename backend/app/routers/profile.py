"""
IPRED Chatbot - Router de perfil de usuario.
"""

from fastapi import APIRouter, Request, HTTPException, status

from app.models.user import PerfilResponse, PerfilUpdate
from app.security.auth import get_current_user
from app.services import perfil_service

router = APIRouter(prefix="/profile", tags=["Perfil"])


def _extract_codigo_est(user_dict: dict) -> int:
    try:
        return int(user_dict.get("username", 0))
    except (ValueError, TypeError):
        return 0


@router.get("", response_model=PerfilResponse)
async def get_profile(request: Request):
    """Obtener el perfil del estudiante autenticado."""
    user = await get_current_user(request)
    codigo_est = _extract_codigo_est(user)
    perfil = await perfil_service.obtener_perfil(codigo_est)
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    return PerfilResponse(**perfil)


@router.get("/calendar")
async def get_calendar(request: Request):
    """Obtener el calendario académico completo: tutorías del estudiante + hitos institucionales UIS."""
    user = await get_current_user(request)
    codigo_est = _extract_codigo_est(user)
    
    from app.db.repositories.student_repository import StudentRepository
    repo = StudentRepository()
    
    profile = await repo.get_profile_by_code(codigo_est)
    schedules = await repo.get_student_schedule(codigo_est)
    
    # Mapear tutorías estructuradas
    tutorias_data = []
    for s in schedules:
        tutorias_data.append({
            "codigo_asignatura": s.codigo_asignatura,
            "nombre_asignatura": s.nombre_asignatura,
            "grupo": s.grupo,
            "profesor": s.profesor or "Docente Titular UIS",
            "correo_profesor": s.correo_profesor,
            "fecha_tutoria": s.fecha_tutoria,
            "hora_inicio": s.hora_inicio,
            "hora_fin": s.hora_fin,
            "tipo_tutoria": s.tipo_tutoria or "Presencial / Híbrida",
        })
        
    hitos = [
        {
            "fecha": "2026-08-04",
            "titulo": "Inicio de Clases y Tutorías 2026-2",
            "descripcion": "Apertura oficial del periodo académico en todas las sedes del IPRED.",
            "tipo": "inicio",
            "icono": "🚀",
        },
        {
            "fecha": "2026-09-26",
            "titulo": "Límite de Cancelación de Asignaturas (Semana 8)",
            "descripcion": "Último día reglamentario para cancelar materias en el portal de estudiantes.",
            "tipo": "tramite",
            "icono": "⚠️",
        },
        {
            "fecha": "2026-10-10",
            "titulo": "Cierre de Evaluaciones de Medio Término",
            "descripcion": "Reporte del 50% de calificaciones parciales en la plataforma Moodle AVA.",
            "tipo": "evaluacion",
            "icono": "📝",
        },
        {
            "fecha": "2026-11-21",
            "titulo": "Finalización de Clases y Evaluaciones Finales",
            "descripcion": "Cierre del periodo lectivo presencial y virtual en todas las asignaturas.",
            "tipo": "cierre",
            "icono": "🏁",
        },
        {
            "fecha": "2026-11-28",
            "titulo": "Cierre de Registro de Calificaciones en UISARD",
            "descripcion": "Generación del polígrafo de notas oficial definitivo con promedio ponderado.",
            "tipo": "notas",
            "icono": "📊",
        },
        {
            "fecha": "2026-12-11",
            "titulo": "Ceremonia Solemne de Grados Colectivos",
            "descripcion": "Auditorio Luis A. Calvo - Campus Principal UIS Bucaramanga.",
            "tipo": "grado",
            "icono": "🎓",
        },
    ]
    
    return {
        "codigo_est": codigo_est,
        "nombre_completo": profile.nombre_completo if profile else "Estudiante IPRED",
        "programa": profile.nombre_programa if profile else "IPRED - UIS",
        "sede": profile.nombre_sede if profile else "Bucaramanga",
        "tutorias": tutorias_data,
        "hitos_institucionales": hitos,
    }


@router.put("", response_model=PerfilResponse)
async def update_profile(req: PerfilUpdate, request: Request):
    """Actualizar preferencias del perfil del estudiante autenticado."""
    user = await get_current_user(request)
    codigo_est = _extract_codigo_est(user)
    perfil = await perfil_service.actualizar_perfil(
        codigo_est=codigo_est,
        datos=req.model_dump(exclude_unset=True) if hasattr(req, "model_dump") else req.dict(exclude_unset=True),
    )
    return PerfilResponse(**perfil)

