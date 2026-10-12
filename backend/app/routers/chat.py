"""
IPRED Chatbot - Router de chat y mensajería.
Controlador HTTP limpio que delega la lógica de negocio al chat_service.
"""

import logging
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.user import ChatRequest, ChatResponse
from app.security.auth import get_current_user
from app.services.chat_service import chat_service
from app.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(req: ChatRequest, request: Request):
    """Envía un mensaje al chatbot y obtiene una respuesta enriquecida."""
    user = await get_current_user(request)

    message_text = req.get_message_text()
    if not message_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El mensaje no puede estar vacío")

    try:
        response = await chat_service.process_user_message(
            message_text=message_text,
            user_dict=user,
            conversacion_id=req.conversacion_id,
        )
        return response
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as ex:
        logger.error("Error procesando mensaje de chat: %s", ex)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno procesando la consulta.")


@router.post("/stream")
async def send_message_stream(req: ChatRequest, request: Request):
    """Envía un mensaje al chatbot y transmite la respuesta en tiempo real vía Server-Sent Events (SSE)."""
    user = await get_current_user(request)

    message_text = req.get_message_text()
    if not message_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El mensaje no puede estar vacío")

    try:
        generator = chat_service.process_user_message_stream(
            message_text=message_text,
            user_dict=user,
            conversacion_id=req.conversacion_id,
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as ex:
        logger.error("Error iniciando stream de chat: %s", ex)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno procesando el stream.")


@router.get("/conversations")
async def get_conversations(request: Request):
    """Lista las conversaciones activas del usuario autenticado."""
    user = await get_current_user(request)
    db = await get_db()
    cursor = await db.execute(
        """SELECT id, titulo, created_at, updated_at FROM conversaciones
           WHERE usuario_id = ? AND activa = true
           ORDER BY updated_at DESC LIMIT 30""",
        (user["user_id"],),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


from typing import Optional

@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: int, request: Request, before_id: Optional[int] = None, limit: int = 50):
    """Obtiene el historial de mensajes de una conversación con paginación por cursor ultra-rápida."""
    user = await get_current_user(request)
    db = await get_db()

    # Verificar autorización de propiedad
    cursor = await db.execute(
        "SELECT id FROM conversaciones WHERE id = ? AND usuario_id = ?",
        (conv_id, user["user_id"]),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conversación no encontrada o acceso denegado")

    if before_id:
        cursor = await db.execute(
            """SELECT id, rol, contenido, metadata_json, tokens_input, tokens_output, created_at FROM mensajes
               WHERE conversacion_id = ? AND id < ?
               ORDER BY id DESC LIMIT ?""",
            (conv_id, before_id, limit),
        )
    else:
        cursor = await db.execute(
            """SELECT id, rol, contenido, metadata_json, tokens_input, tokens_output, created_at FROM mensajes
               WHERE conversacion_id = ?
               ORDER BY id ASC LIMIT ?""",
            (conv_id, limit),
        )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        tokens = (d.get("tokens_input") or 0) + (d.get("tokens_output") or 0)
        d["tokens_usados"] = tokens
        d["es_ia"] = (tokens > 0)
        
        # Clasificador web retrospectivo
        meta_str = str(d.get("metadata_json") or "")
        d["es_web"] = ("buscar_informacion_web" in meta_str or "leer_pagina_web" in meta_str)
        result.append(d)
    return result


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conv_id: int, request: Request):
    """Elimina lógicamente una conversación del usuario autenticado."""
    user = await get_current_user(request)
    db = await get_db()

    # Verificar que pertenezca al usuario
    cursor = await db.execute(
        "SELECT id FROM conversaciones WHERE id = ? AND usuario_id = ?",
        (conv_id, user["user_id"]),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")

    await db.execute(
        "UPDATE conversaciones SET activa = false WHERE id = ?",
        (conv_id,),
    )
    await db.commit()
    return None
