"""
Test unitario y de integración para validar el endpoint y servicio de streaming SSE
"""
import asyncio
import json
from app.db.database import init_db, close_db
from app.services.chat_service import chat_service

async def run_stream_test():
    print("=== Iniciando prueba de Streaming SSE ===")
    await init_db()
    
    mock_user = {
        "user_id": 1,
        "username": "2200001",
        "codigo_est": 2200001,
        "rol": "estudiante",
    }
    
    # Prueba 1: Zero-AI Stream
    print("\n--- Test 1: Zero-AI Stream ('¿Qué es el IPRED?') ---")
    events = []
    async for raw_sse in chat_service.process_user_message_stream(
        message_text="¿Qué es el IPRED?",
        user_dict=mock_user,
        conversacion_id=None,
    ):
        line = raw_sse.strip()
        if line.startswith("data:"):
            payload = json.loads(line[5:].strip())
            events.append(payload)
            if payload.get("type") == "chunk":
                print(payload.get("text"), end="", flush=True)
    
    print(f"\nTotal eventos recibidos en Zero-AI: {len(events)}")
    done_event = next((e for e in events if e.get("type") == "done"), None)
    assert done_event is not None, "Debe existir un evento 'done'"
    print("Zero-AI Done Payload:", done_event)
    
    await close_db()
    print("\n=== Prueba de Streaming completada con éxito ===")

if __name__ == "__main__":
    asyncio.run(run_stream_test())
