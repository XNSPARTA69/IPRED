"""
IPRED Chatbot - Modelos tipados para el dominio académico y datos de estudiantes.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class StudentProfile(BaseModel):
    """Perfil consolidado del estudiante (normalizado desde múltiples filas)."""
    model_config = ConfigDict(frozen=True)

    codigo_est: int
    primer_nombre: str = ""
    primer_apellido: str = ""
    nombre_completo: str = ""
    programa_academico: Optional[int] = None
    nombre_programa: Optional[str] = None
    codigo_sede: Optional[int] = None
    nombre_sede: Optional[str] = None
    grupo: Optional[str] = None


class Subject(BaseModel):
    """Asignatura matriculada con su docente y grupo."""
    codigo_asignatura: int
    nombre_asignatura: str
    grupo: str
    nombre_programa: Optional[str] = None
    profesor: Optional[str] = None
    correo_profesor: Optional[str] = None
    id_semestre: Optional[int] = None


class ScheduleItem(BaseModel):
    """Sesión o tutoría de clase."""
    codigo_asignatura: int
    nombre_asignatura: str
    grupo: str
    profesor: Optional[str] = None
    correo_profesor: Optional[str] = None
    fecha_tutoria: str  # YYYY-MM-DD
    hora_inicio: str    # HH:MM
    hora_fin: str       # HH:MM
    tipo_tutoria: Optional[str] = None
    aula: Optional[str] = None


class KnowledgeChunk(BaseModel):
    """Fragmento de conocimiento institucional."""
    id_chunk: str
    categoria: str
    subcategoria: str = ""
    titulo: str
    contenido: str
    tags: List[str] = Field(default_factory=list)
    relevancia: Optional[float] = None


class SearchResult(BaseModel):
    """Resultado de búsqueda web o institucional."""
    titulo: str
    url: str
    snippet: str
    fuente: str = "Web UIS"
