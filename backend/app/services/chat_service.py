"""
IPRED Chatbot - Servicio de orquestación del chat y sesiones de conversación.
Aísla la lógica de negocio del router de FastAPI.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.db.database import get_db
from app.db.repositories.student_repository import student_repo
from app.services.ai_service import ai_service
from app.services.info_fija_service import guardar_respuesta_aprendida
from app.models.user import ChatResponse
from app.config import get_colombia_now

logger = logging.getLogger(__name__)


class ChatService:
    """Manejo de conversaciones, persistencia de mensajes y atribución de fuentes."""

    @staticmethod
    def extract_student_code(user_dict: Dict[str, Any]) -> int:
        """
        Extrae el código numérico de estudiante del usuario autenticado.
        Si el username no es un número entero válido, retorna 0.
        """
        username = user_dict.get("username", "")
        try:
            return int(username)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def determine_sources(herramientas_usadas: List[str]) -> List[str]:
        """Calcula las fuentes institucionales atribuidas en función de las herramientas ejecutadas."""
        fuentes = []
        if "consultar_horario" in herramientas_usadas or "consultar_asignaturas" in herramientas_usadas:
            fuentes.append("Sistema Académico IPRED")
        if "buscar_informacion_fija" in herramientas_usadas or "respuesta_directa" in herramientas_usadas:
            fuentes.append("Reglamento y Base Oficial IPRED")
        if "buscar_informacion_web" in herramientas_usadas or "leer_pagina_web" in herramientas_usadas:
            fuentes.append("Portal Web UIS")
        if not fuentes:
            fuentes.append("Información Institucional IPRED")
        return list(dict.fromkeys(fuentes))

    async def process_user_message(
        self,
        message_text: str,
        user_dict: Dict[str, Any],
        conversacion_id: Optional[int] = None,
    ) -> ChatResponse:
        """Flujo completo de procesamiento de un mensaje de usuario."""
        user_id = user_dict["user_id"]
        codigo_est = self.extract_student_code(user_dict)
        db = await get_db()

        # 1. Obtener o crear conversación
        conv_id = conversacion_id
        if not conv_id:
            cursor = await db.execute(
                "INSERT INTO conversaciones (usuario_id, titulo) VALUES (?, ?)",
                (user_id, message_text[:50]),
            )
            await db.commit()
            conv_id = cursor.lastrowid
        else:
            # Validar autorización de propiedad de la conversación
            cursor = await db.execute(
                "SELECT id FROM conversaciones WHERE id = ? AND usuario_id = ?",
                (conv_id, user_id),
            )
            if not await cursor.fetchone():
                raise PermissionError("Conversación no encontrada o no autorizada.")

        # 2. Guardar mensaje del usuario con timestamp Colombia (UTC-5)
        ahora_co = get_colombia_now().isoformat()
        await db.execute(
            "INSERT INTO mensajes (conversacion_id, rol, contenido, created_at) VALUES (?, 'user', ?, ?)",
            (conv_id, message_text, ahora_co),
        )
        await db.commit()

        # 3. Cargar historial temporal deduplicado (máximo 6 mensajes previos)
        cursor = await db.execute(
            """SELECT rol as role, contenido as content FROM mensajes
               WHERE conversacion_id = ?
               ORDER BY created_at DESC LIMIT 6""",
            (conv_id,),
        )
        rows = await cursor.fetchall()
        # Invertir para orden cronológico
        raw_history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        # Excluir el mensaje actual que acabamos de persistir
        history = raw_history[:-1] if len(raw_history) > 1 else []

        # 4. Obtener datos del estudiante para enriquecer el contexto
        if codigo_est <= 0:
            cur_u = await db.execute("SELECT username FROM usuarios WHERE id = ?", (user_id,))
            row_u = await cur_u.fetchone()
            if row_u and row_u["username"]:
                try:
                    codigo_est = int(row_u["username"])
                except (ValueError, TypeError):
                    codigo_est = 0

        student_data = None
        if codigo_est > 0:
            profile = await student_repo.get_profile_by_code(codigo_est)
            if profile:
                student_data = profile.model_dump()

        # 5. Procesar consulta a través del ai_service (con Capa 0 de intercepción directa)
        respuesta, herramientas, tokens = await ai_service.chat(
            message=message_text,
            codigo_est=codigo_est,
            history=history,
            student_data=student_data,
        )

        # 6. Guardar respuesta del asistente de forma asíncrona de alto rendimiento
        metadata = json.dumps({
            "herramientas": herramientas,
            "tokens": tokens,
        }, ensure_ascii=False)

        ahora_asistente_co = get_colombia_now().isoformat()
        
        async def _persist_assistant_msg(cid: int, resp: str, meta: str, tok: int, ts: str):
            try:
                db_bg = await get_db()
                await db_bg.execute(
                    """INSERT INTO mensajes (conversacion_id, rol, contenido, metadata_json, tokens_input, tokens_output, created_at)
                       VALUES (?, 'assistant', ?, ?, ?, ?, ?)""",
                    (cid, resp, meta, tok // 2, tok // 2, ts),
                )
                await db_bg.execute(
                    "UPDATE conversaciones SET updated_at = ? WHERE id = ?",
                    (ts, cid),
                )
                await db_bg.commit()
            except Exception as e_bg:
                logger.error("Error persistiendo mensaje de asistente en background: %s", e_bg)

        # Disparar tarea en background sin frenar la latencia de respuesta al estudiante
        asyncio.create_task(_persist_assistant_msg(conv_id, respuesta, metadata, tokens, ahora_asistente_co))

        # 7. Aprendizaje pasivo / atajos si aplica
        if "buscar_informacion_fija" in herramientas and tokens > 0:
            await guardar_respuesta_aprendida(message_text, respuesta)

        # 8. Construir respuesta final con atribución de fuentes
        fuentes = self.determine_sources(herramientas)
        es_web = bool(herramientas and ("buscar_informacion_web" in herramientas or "leer_pagina_web" in herramientas))

        return ChatResponse(
            respuesta=respuesta,
            conversacion_id=conv_id,
            fuentes=fuentes,
            herramientas_usadas=herramientas if herramientas else None,
            tokens_usados=tokens,
            es_ia=(tokens > 0),
            es_web=es_web,
        )

    async def process_user_message_stream(
        self,
        message_text: str,
        user_dict: Dict[str, Any],
        conversacion_id: Optional[int] = None,
    ):
        """
        Generador asíncrono para streaming SSE de extremo a extremo.
        Emite strings en formato SSE: 'data: {...}\n\n'
        """
        user_id = user_dict["user_id"]
        codigo_est = self.extract_student_code(user_dict)
        db = await get_db()

        # 1. Obtener o crear conversación
        conv_id = conversacion_id
        if not conv_id:
            cursor = await db.execute(
                "INSERT INTO conversaciones (usuario_id, titulo) VALUES (?, ?)",
                (user_id, message_text[:50]),
            )
            await db.commit()
            conv_id = cursor.lastrowid
        else:
            cursor = await db.execute(
                "SELECT id FROM conversaciones WHERE id = ? AND usuario_id = ?",
                (conv_id, user_id),
            )
            if not await cursor.fetchone():
                yield f"data: {json.dumps({'type': 'error', 'detail': 'Conversación no encontrada.'})}\n\n"
                return

        # 2. Guardar mensaje del usuario
        ahora_co = get_colombia_now().isoformat()
        await db.execute(
            "INSERT INTO mensajes (conversacion_id, rol, contenido, created_at) VALUES (?, 'user', ?, ?)",
            (conv_id, message_text, ahora_co),
        )
        await db.commit()

        # Emitir evento inicial de conversación
        yield f"data: {json.dumps({'type': 'init', 'conversacion_id': conv_id})}\n\n"

        # 3. Cargar historial
        cursor = await db.execute(
            """SELECT rol as role, contenido as content FROM mensajes
               WHERE conversacion_id = ?
               ORDER BY created_at DESC LIMIT 6""",
            (conv_id,),
        )
        rows = await cursor.fetchall()
        raw_history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        history = raw_history[:-1] if len(raw_history) > 1 else []

        # 4. Datos del estudiante
        if codigo_est <= 0:
            cur_u = await db.execute("SELECT username FROM usuarios WHERE id = ?", (user_id,))
            row_u = await cur_u.fetchone()
            if row_u and row_u["username"]:
                try:
                    codigo_est = int(row_u["username"])
                except (ValueError, TypeError):
                    codigo_est = 0

        student_data = None
        if codigo_est > 0:
            profile = await student_repo.get_profile_by_code(codigo_est)
            if profile:
                student_data = profile.model_dump()

        # 5. Iterar sobre el generador de ai_service
        accumulated_text = []
        herramientas_usadas: List[str] = []
        tokens_finales = 0

        try:
            async for event in ai_service.chat_stream(
                message=message_text,
                codigo_est=codigo_est,
                history=history,
                student_data=student_data,
            ):
                event_type = event.get("type")
                if event_type == "chunk":
                    accumulated_text.append(event.get("text", ""))
                    yield f"data: {json.dumps(event)}\n\n"
                elif event_type == "tool":
                    herramientas_usadas.append(event.get("name", ""))
                    yield f"data: {json.dumps(event)}\n\n"
                elif event_type == "done":
                    tokens_finales = event.get("tokens", 0)
                    herramientas_usadas = event.get("herramientas", herramientas_usadas)

            # Persistencia de respuesta completada
            full_response = "".join(accumulated_text).strip()
            fuentes = self.determine_sources(herramientas_usadas)
            es_web = bool(herramientas_usadas and ("buscar_informacion_web" in herramientas_usadas or "leer_pagina_web" in herramientas_usadas))

            metadata = json.dumps({
                "herramientas": herramientas_usadas,
                "tokens": tokens_finales,
            }, ensure_ascii=False)

            ahora_asistente_co = get_colombia_now().isoformat()
            db_bg = await get_db()
            await db_bg.execute(
                """INSERT INTO mensajes (conversacion_id, rol, contenido, metadata_json, tokens_input, tokens_output, created_at)
                   VALUES (?, 'assistant', ?, ?, ?, ?, ?)""",
                (conv_id, full_response, metadata, tokens_finales // 2, tokens_finales // 2, ahora_asistente_co),
            )
            await db_bg.execute(
                "UPDATE conversaciones SET updated_at = ? WHERE id = ?",
                (ahora_asistente_co, conv_id),
            )
            await db_bg.commit()

            # Emitir evento final de finalización
            done_payload = {
                "type": "done",
                "conversacion_id": conv_id,
                "fuentes": fuentes,
                "herramientas_usadas": herramientas_usadas,
                "tokens_usados": tokens_finales,
                "es_ia": (tokens_finales > 0),
                "es_web": es_web,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except asyncio.CancelledError:
            logger.info("Stream cancelado por el cliente. Persistiendo texto parcial.")
            full_response = "".join(accumulated_text).strip()
            if full_response:
                try:
                    db_cancel = await get_db()
                    ahora_asistente_co = get_colombia_now().isoformat()
                    await db_cancel.execute(
                        """INSERT INTO mensajes (conversacion_id, rol, contenido, metadata_json, tokens_input, tokens_output, created_at)
                           VALUES (?, 'assistant', ?, ?, 0, 0, ?)""",
                        (conv_id, full_response + " *[Detenido]*", "{}", ahora_asistente_co),
                    )
                    await db_cancel.commit()
                except Exception as e_c:
                    logger.error("Error persistiendo mensaje cancelado: %s", e_c)
            raise


chat_service = ChatService()
