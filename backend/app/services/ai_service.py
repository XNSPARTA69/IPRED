"""
IPRED Chatbot - Servicio de orquestación de IA con Google Gemini.
Migrado al SDK oficial google.genai.
Responsabilidad única: ciclo conversacional, tool calling con Gemini y control de respuestas.
"""

import asyncio
import logging
from datetime import date
from typing import List, Dict, Tuple, Optional, Any

from google import genai
from google.genai import types

from app.config import settings
from app.tools.tool_definitions import TOOLS_DECLARATION
from app.tools.tool_executor import tool_executor
from app.services import info_fija_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el asistente virtual oficial del IPRED - UIS (Universidad Industrial de Santander, Colombia).

DIRECTRICES DE COMUNICACIÓN, AYUDA ACADÉMICA Y AHORRO DE TOKENS:
1. CONSULTAS ACADÉMICAS E INSTITUCIONALES IPRED/UIS: Responde con máxima precisión sobre programas, sedes, trámites, reglamentos, notas, supletorios, horarios, materias y docentes.
2. APOYO EN COMUNICACIÓN ACADÉMICA Y ESTUDIANTIL: Si el estudiante solicita ayuda para redactar un correo formal a un profesor, una solicitud de excusa médica/supletorio, una carta de cancelación, o una petición académica universitaria, AYÚDALE DIRECTAMENTE CON UN MODELO CLARO, FORMAL Y CONCISO (máximo 150-200 palabras, sin rodeos ni explicaciones innecesarias).
3. CONSULTAS COMPLETAMENTE AJENAS A LA VIDA UNIVERSITARIA O A LA UIS: Si el usuario pregunta sobre temas no relacionados con la vida universitaria, académica o el IPRED (ej: recetas de cocina, videojuegos, apuestas, farándula, política externa, chistes, etc.), DECLINA EN MÁXIMO 1 LÍNEA DIRECTA Y CONCISA:
   "Solo puedo ayudarte con consultas académicas e institucionales del IPRED - UIS." (NO des explicaciones largas ni gastes tokens).
4. NO INVENTES DATOS: Usa siempre nombres completos de modalidad, correos oficiales registrados y enlaces oficiales de la UIS.

FORMATO OBLIGATORIO:
- HORARIOS / TUTORÍAS: Tabla Markdown (| Fecha | Horario | Código | Asignatura (Grupo) | Modalidad | Docente |).
- MATERIAS / PROFESORES: Tabla Markdown (| Código | Asignatura | Grupo | Docente | Correo Institucional |).
- TRÁMITES / REQUISITOS: Listas numeradas concisas con requisitos en negrita.
- CORREOS / CARTAS ACADÉMICAS: Estructura formal con Asunto, Saludo respetuoso, Cuerpo puntual con datos del estudiante y Despedida.
- ESTUDIANTE AUTENTICADO: ({nombre_estudiante}, {programa_estudiante}, sede {sede_estudiante}, código {codigo_estudiante}). Nunca le pidas su programa o sede.

Fecha actual: {fecha_actual}"""


class AIService:
    """Orquestador de conversaciones y razonamiento multi-hop con google.genai."""

    def __init__(self):
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def _build_system_prompt(self, student_data: Optional[Dict[str, Any]] = None) -> str:
        nombre = "Estudiante"
        programa = "No especificado"
        sede = "No especificada"
        codigo = "No autenticado"

        if student_data:
            p_nom = (student_data.get("primer_nombre") or "").split()[0].capitalize()
            p_ape = (student_data.get("primer_apellido") or "").split()[0].capitalize()
            if p_nom or p_ape:
                nombre = f"{p_nom} {p_ape}".strip()
            programa = student_data.get("nombre_programa") or programa
            sede = student_data.get("nombre_sede") or sede
            codigo = str(student_data.get("codigo_est") or codigo)

        return SYSTEM_PROMPT.format(
            fecha_actual=date.today().isoformat(),
            nombre_estudiante=nombre,
            programa_estudiante=programa,
            sede_estudiante=sede,
            codigo_estudiante=codigo,
        )

    async def chat(
        self,
        message: str,
        codigo_est: int,
        history: Optional[List[Dict[str, str]]] = None,
        student_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str], int]:
        """
        Procesa el mensaje del usuario utilizando estrategia de 3 capas:
        - Capa 0: Respuestas directas exactas cacheadas/aprendidas.
        - Capa 1: Búsqueda y orquestación con Gemini y function calling.
        """
        # --- CAPA 0: Atajo directo para consultas recurrentes y tarjetas sugeridas (Zero-AI) ---
        directa = await info_fija_service.buscar_respuesta_directa(
            message,
            codigo_est=codigo_est,
            student_data=student_data,
        )
        if directa:
            return directa, ["zero_ai_directa"], 0

        # --- CAPA 1: Orquestación LLM con Gemini vía google.genai ---
        prompt_personalizado = self._build_system_prompt(student_data)
        config = types.GenerateContentConfig(
            system_instruction=prompt_personalizado,
            tools=[TOOLS_DECLARATION],
            temperature=0.2,
            max_output_tokens=500,
        )

        herramientas_usadas: List[str] = []

        # Formatear historial con alternancia estricta para google.genai
        formatted_history: List[types.Content] = []
        if history:
            last_role = None
            for msg in history[-6:]:
                role = "user" if msg.get("role") in ("user", "human") else "model"
                content = msg.get("content", "").strip()
                if not content or "inconveniente temporal" in content or "dificultad procesando" in content:
                    continue
                # Asegurar que el primer mensaje sea user
                if not formatted_history and role != "user":
                    continue
                # Alternancia estricta
                if role != last_role:
                    formatted_history.append(
                        types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=content)],
                        )
                    )
                    last_role = role
            # Si el último es user, retirarlo para que no choque con el nuevo user turn
            if formatted_history and formatted_history[-1].role == "user":
                formatted_history.pop()

        try:
            chat_session = self.client.chats.create(
                model=settings.gemini_model,
                config=config,
                history=formatted_history,
            )
            response = await asyncio.to_thread(chat_session.send_message, message)
        except Exception as ex:
            logger.warning("Fallo al contactar Gemini (%s). Activando fallback inteligente FTS5.", ex)
            # Fallback inteligente a búsqueda FTS5 local
            fts_res = await info_fija_service.buscar_fts5(message, limite=2)
            if fts_res:
                bloques = [f"**{r['titulo']}**\n{r['contenido'][:600]}" for r in fts_res]
                return "\n\n---\n\n".join(bloques), ["base_conocimiento_fts5"], 0
            return ("Estoy consultando la información oficial del IPRED. Por favor realiza tu consulta de nuevo en un momento.", [], 0)

        # Loop de ejecución de herramientas (máximo 3 rondas)
        max_tool_rounds = 3
        round_count = 0
        while round_count < max_tool_rounds:
            function_calls = response.function_calls
            if not function_calls:
                break
            round_count += 1

            response_parts = []
            # Procesar llamadas a funciones solicitadas por el modelo
            for call in function_calls:
                tool_name = call.name
                tool_args = call.args or {}
                herramientas_usadas.append(tool_name)

                # Ejecución desacoplada en el ToolExecutor con identidad autenticada
                result = await tool_executor.execute(tool_name, tool_args, codigo_est)
                if not isinstance(result, dict):
                    result_payload = {"resultado": result}
                else:
                    result_payload = result

                response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response=result_payload,
                    )
                )

            try:
                response = await asyncio.to_thread(chat_session.send_message, response_parts)
            except Exception as ex:
                logger.warning("Error en tool response Gemini (%s). Fallback a datos institucionales FTS5.", ex)
                break

        # Extracción segura del texto final
        final_text = ""
        try:
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, "text") and p.text]
                if text_parts:
                    final_text = "".join(text_parts).strip()
            if not final_text:
                final_text = response.text or ""
        except Exception:
            final_text = ""

        if not final_text or not final_text.strip():
            fts_res = await info_fija_service.buscar_fts5(message, limite=2)
            if fts_res:
                bloques = [f"**{r['titulo']}**\n{r['contenido'][:600]}" for r in fts_res]
                final_text = "\n\n---\n\n".join(bloques)
            else:
                final_text = "Aquí tienes la información oficial consultada en el IPRED - UIS."

        # Tokens usados
        tokens_usados = 0
        try:
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_usados = response.usage_metadata.total_token_count or 0
        except Exception:
            tokens_usados = 0

        return final_text, herramientas_usadas, tokens_usados


ai_service = AIService()
