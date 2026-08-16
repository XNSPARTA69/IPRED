"""
IPRED Chatbot - Modelos Pydantic para datos del cronograma IPRED.
"""

from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================
# Modelos de la respuesta original del endpoint IPRED
# ============================================================

class ActividadIPRED(BaseModel):
    """Actividad tal como viene del endpoint IPRED (estructura original)."""
    fecha_inicio: str
    fecha_fin: str
    codigo_tipo_actividad: int
    nombre_tipo_actividad: str
    id_actividad: int


class AsignaturaBloque(BaseModel):
    """Bloque de asignatura del endpoint IPRED (estructura original)."""
    codigo_programa: int
    codigo_sede: int
    codigo_asignatura: int
    id_semestre: int
    grupo: str
    nombre_profesor: str
    nombre_asignatura: str
    actividades: list[ActividadIPRED] = Field(default_factory=list)


# ============================================================
# Modelo normalizado (lo que se envía al modelo de IA)
# ============================================================

class ActividadNormalizada(BaseModel):
    """Actividad normalizada y aplanada para consumo del modelo de IA."""
    semestre: str
    programa_codigo: str
    sede_codigo: str
    asignatura_codigo: str
    asignatura: str
    grupo: str
    profesor: str
    actividad_id: str
    tipo_actividad: str
    inicio: str  # ISO 8601
    fin: str      # ISO 8601
    aula: str | None = None
    edificio: str | None = None

    @classmethod
    def from_ipred(cls, bloque: AsignaturaBloque, actividad: ActividadIPRED) -> "ActividadNormalizada":
        """Convierte los datos del endpoint IPRED a formato normalizado."""
        # Convertir nombre de asignatura de MAYÚSCULAS a Title Case
        nombre_asig = bloque.nombre_asignatura.strip()
        if nombre_asig.isupper():
            nombre_asig = nombre_asig.title()

        # Normalizar fechas a ISO 8601
        inicio = actividad.fecha_inicio.replace(" ", "T")
        fin = actividad.fecha_fin.replace(" ", "T")

        return cls(
            semestre=str(bloque.id_semestre),
            programa_codigo=str(bloque.codigo_programa),
            sede_codigo=str(bloque.codigo_sede),
            asignatura_codigo=str(bloque.codigo_asignatura),
            asignatura=nombre_asig,
            grupo=bloque.grupo,
            profesor=bloque.nombre_profesor.strip(),
            actividad_id=str(actividad.id_actividad),
            tipo_actividad=actividad.nombre_tipo_actividad.strip(),
            inicio=inicio,
            fin=fin,
        )


# ============================================================
# Parámetros de consulta del cronograma
# ============================================================

class CronogramaQuery(BaseModel):
    """Parámetros para consultar el cronograma IPRED."""
    semestre: str
    programa: str
    sede: str
    jornada: str = "1"
    fecha_inicial: str  # YYYY-MM-DD
    fecha_final: str    # YYYY-MM-DD
    grupo: str | None = None
    asignatura: str | None = None
