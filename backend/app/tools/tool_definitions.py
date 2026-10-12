"""
IPRED Chatbot - Definiciones formales y constantes de herramientas de IA.
Migrado al nuevo SDK oficial google.genai.
"""

from enum import Enum
from google.genai import types


class ToolName(str, Enum):
    """Nombres constantes de herramientas para evitar magic strings."""
    CONSULTAR_HORARIO = "consultar_horario"
    CONSULTAR_ASIGNATURAS = "consultar_asignaturas"
    BUSCAR_INFORMACION_FIJA = "buscar_informacion_fija"
    OBTENER_PERFIL_USUARIO = "obtener_perfil_usuario"
    ACTUALIZAR_PERFIL_USUARIO = "actualizar_perfil_usuario"
    LISTAR_SEDES = "listar_sedes"
    LISTAR_PROGRAMAS = "listar_programas"
    BUSCAR_INFORMACION_WEB = "buscar_informacion_web"
    LEER_PAGINA_WEB = "leer_pagina_web"


def _str_param(description: str) -> types.Schema:
    return types.Schema(type=types.Type.STRING, description=description)


TOOLS_DECLARATION = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name=ToolName.CONSULTAR_HORARIO.value,
            description="Consulta las fechas y horas de tutorías del estudiante. Opcional: filtrar por 'fecha' (YYYY-MM-DD).",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "fecha": _str_param("Fecha en formato YYYY-MM-DD (opcional)"),
                },
            ),
        ),
        types.FunctionDeclaration(
            name=ToolName.CONSULTAR_ASIGNATURAS.value,
            description="Consulta las materias matriculadas y nombres de los profesores del estudiante.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
        types.FunctionDeclaration(
            name=ToolName.BUSCAR_INFORMACION_FIJA.value,
            description="Busca reglamentos, acuerdos, notas, habilitación, trámites, requisitos de grado, sedes y contactos de la UIS/IPRED.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "texto_busqueda": _str_param("Término o palabras clave"),
                    "categoria": _str_param("Categoría: reglamento, tramite, sede, contacto, grado (opcional)"),
                },
                required=["texto_busqueda"],
            ),
        ),
        types.FunctionDeclaration(
            name=ToolName.BUSCAR_INFORMACION_WEB.value,
            description="Busca información institucional externa en portales de la UIS cuando no está en la base local.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "consulta": _str_param("Término de búsqueda web"),
                },
                required=["consulta"],
            ),
        ),
    ]
)
