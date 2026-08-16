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


chat_service = ChatService()
