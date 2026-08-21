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

SYSTEM_PROMPT = """Eres ÚNICAMENTE el Asistente Administrativo e Institucional del IPRED - Universidad Industrial de Santander (UIS), Colombia.

⛔ PROHIBICIONES ESTRICTAS (RECHAZO OBLIGATORIO):
NO eres un tutor académico, profesor de materias ni asistente de tareas generales.
Tienes TERMINANTEMENTE PROHIBIDO responder, explicar, resolver, programar o redactar contenido sobre:
1. Programación o Desarrollo de Software: NUNCA generes código (Python, Java, C++, JS, SQL, HTML, etc.), scripts, algoritmos ni explicaciones de programación.
2. Matemáticas y Ciencias: NUNCA resuelvas ni expliques matrices, cálculo, derivadas, integrales, álgebra, física, química ni operaciones numéricas.
3. Tareas y Trabajos de Clase: NUNCA hagas resúmenes de libros temáticos, ensayos de materias, talleres, ejercicios ni proyectos académicos.
4. Temas Generales de Estudio: NUNCA expliques conceptos teóricos de asignaturas (ej. biología, historia, filosofía, medicina, etc.).

👉 RESPUESTA OBLIGATORIA DE RECHAZO:
Si el usuario te solicita CUALQUIER cosa relacionada con las prohibiciones anteriores, DEBES responder EXACTAMENTE Y EN 1 SOLA FRASE:
"Mi función es exclusivamente de orientación administrativa e institucional en el IPRED - UIS (horarios, docentes, trámites, reglamentos y redacción de correos). No estoy habilitado para resolver tareas, código de programación, operaciones matemáticas ni trabajos académicos."
NO agregues explicaciones adicionales, ni introducciones, ni código, ni fórmulas.

✅ TEMAS EXCLUSIVOS QUE SÍ DEBES ATENDER:
1. Horarios de tutorías y clases del estudiante (en formato tabla).
2. Asignaturas matriculadas, grupos, docentes asignados y correos institucionales (en formato tabla).
3. Reglamentos estudiantiles, ponderación de notas, cancelaciones, habilitaciones, supletorios y requisitos de grado.
4. Trámites administrativos, sedes, directorio de atención, plataforma Moodle/AVA y calendario académico.
5. Redacción y corrección formal de correos y cartas a profesores o directivos de la UIS.

FORMATO:
- HORARIOS / TUTORÍAS: Tabla Markdown (| Fecha | Horario | Código | Asignatura (Grupo) | Modalidad | Docente |).
- MATERIAS / PROFESORES: Tabla Markdown (| Código | Asignatura | Grupo | Docente | Correo Institucional |).
- TRÁMITES / REQUISITOS: Listas estructuradas con viñetas y negrita.
- CORREOS / CARTAS: Estructura formal con Asunto, Saludo formal, Cuerpo respetuoso y Despedida institucional.
- Usa los datos de la sesión del estudiante sin pedírselos de nuevo."""


class AIService:
    """Orquestador de conversaciones y razonamiento multi-hop con google.genai."""

    def __init__(self):
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def _build_context_header(self, student_data: Optional[Dict[str, Any]] = None) -> str:
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

        from app.config import get_colombia_now
        return f"[Contexto Sesión: {nombre} | Código: {codigo} | Sede: {sede} | Programa: {programa} | Fecha: {get_colombia_now().date().isoformat()}]\n\n"

    def _format_history_compact(self, history: Optional[List[Dict[str, str]]]) -> List[types.Content]:
        """Formatea y compacta el historial para ahorrar tokens de entrada."""
        formatted: List[types.Content] = []
        if not history:
            return formatted

        last_role = None
        for msg in history[-6:]:
            role = "user" if msg.get("role") in ("user", "human") else "model"
            content = msg.get("content", "").strip()
            if not content or "inconveniente temporal" in content or "dificultad procesando" in content:
                continue

            # Compactar respuestas excesivamente largas del modelo en turnos anteriores
            if role == "model" and len(content) > 400:
                lines = content.split("\n")
                if len(lines) > 5:
                    content = "\n".join(lines[:4]) + "\n... [Detalle previo procesado]"

            if not formatted and role != "user":
                continue
            if role != last_role:
                formatted.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=content)],
                    )
                )
                last_role = role

        if formatted and formatted[-1].role == "user":
            formatted.pop()

        return formatted

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
        # --- CAPA 0: Atajo directo Zero-AI ---
        directa = await info_fija_service.buscar_respuesta_directa(
            message,
            codigo_est=codigo_est,
            student_data=student_data,
        )
        if directa:
            return directa, ["zero_ai_directa"], 0

        # --- CAPA 1: Orquestación LLM con Gemini vía google.genai ---
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[TOOLS_DECLARATION],
            temperature=0.2,
            max_output_tokens=500,
        )

        herramientas_usadas: List[str] = []
        formatted_history = self._format_history_compact(history)
        user_turn_text = self._build_context_header(student_data) + message

        try:
            chat_session = self.client.chats.create(
                model=settings.gemini_model,
                config=config,
                history=formatted_history,
            )
            response = await asyncio.to_thread(chat_session.send_message, user_turn_text)
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

    async def chat_stream(
        self,
        message: str,
        codigo_est: int,
        history: Optional[List[Dict[str, str]]] = None,
        student_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Generador asíncrono para streaming en tiempo real (SSE).
        Emite eventos:
        - {"type": "chunk", "text": str, "es_ia": bool}
        - {"type": "tool", "name": str, "es_ia": bool}
        - {"type": "done", "tokens": int, "herramientas": List[str], "es_ia": bool}
        """
        # --- CAPA 0: Atajo directo Zero-AI ---
        directa = await info_fija_service.buscar_respuesta_directa(
            message,
            codigo_est=codigo_est,
            student_data=student_data,
        )
        if directa:
            # Emisión limpia e instantánea para Zero-AI (es_ia: False garantizado)
            yield {"type": "chunk", "text": directa, "es_ia": False}
            yield {"type": "done", "tokens": 0, "herramientas": ["zero_ai_directa"], "es_ia": False}
            return

        # --- CAPA 1: Orquestación LLM con Gemini ---
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[TOOLS_DECLARATION],
            temperature=0.2,
            max_output_tokens=500,
        )

        herramientas_usadas: List[str] = []
        formatted_history = self._format_history_compact(history)
        user_turn_text = self._build_context_header(student_data) + message

        chat_session = None
        try:
            chat_session = self.client.chats.create(
                model=settings.gemini_model,
                config=config,
                history=formatted_history,
            )
            response = await asyncio.to_thread(chat_session.send_message, user_turn_text)
        except Exception as ex:
            logger.warning("Fallo al contactar Gemini en streaming (%s). Activando fallback FTS5.", ex)
            fts_res = await info_fija_service.buscar_fts5(message, limite=2)
            if fts_res:
                bloques = [f"**{r['titulo']}**\n{r['contenido'][:600]}" for r in fts_res]
                fallback_txt = "\n\n---\n\n".join(bloques)
            else:
                fallback_txt = "Estoy consultando la información oficial del IPRED. Por favor realiza tu consulta de nuevo en un momento."
            for chunk in fallback_txt.split(" "):
                yield {"type": "chunk", "text": chunk + " ", "es_ia": False}
                await asyncio.sleep(0.015)
            yield {"type": "done", "tokens": 0, "herramientas": ["base_conocimiento_fts5"], "es_ia": False}
            return

        # Loop de ejecución de herramientas
        max_tool_rounds = 3
        round_count = 0
        last_response_parts = None

        while round_count < max_tool_rounds:
            function_calls = response.function_calls
            if not function_calls:
                break
            round_count += 1

            response_parts = []
            for call in function_calls:
                tool_name = call.name
                tool_args = call.args or {}
                herramientas_usadas.append(tool_name)
                yield {"type": "tool", "name": tool_name, "es_ia": True}

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

            last_response_parts = response_parts
            try:
                response = await asyncio.to_thread(chat_session.send_message, response_parts)
            except Exception as ex:
                logger.warning("Error en tool response Gemini (%s).", ex)
                break

        # Extraer y emitir el texto final
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

        tokens_usados = 0
        try:
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_usados = response.usage_metadata.total_token_count or 0
        except Exception:
            tokens_usados = 0

        # Streaming progresivo de texto al cliente
        # Dividimos en chunks de palabras para entrega visual ultra fluida
        words = final_text.split(" ")
        for i, word in enumerate(words):
            yield {"type": "chunk", "text": word + (" " if i < len(words) - 1 else ""), "es_ia": True}
            await asyncio.sleep(0.012)

        yield {
            "type": "done",
            "tokens": tokens_usados,
            "herramientas": herramientas_usadas,
            "es_ia": True,
        }


ai_service = AIService()
