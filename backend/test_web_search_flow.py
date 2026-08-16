import asyncio
from app.services.chat_service import chat_service

async def test_web_search():
    pregunta = "¿Quién es el actual rector de la Universidad Industrial de Santander UIS y qué dice la web institucional de él?"
    user_dict = {"user_id": 2, "username": "2226666"}
    
    print("=" * 70)
    print(f"Pregunta enviada: {pregunta}")
    print("=" * 70)
    
    resp = await chat_service.process_user_message(pregunta, user_dict=user_dict)
    
    print("\n--- RESULTADOS DEL CHATBOT ---")
    print(f"Herramientas ejecutadas: {resp.herramientas_usadas}")
    print(f"Tokens consumidos: {resp.tokens_usados}")
    print(f"\nRespuesta generada:\n{resp.respuesta}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_web_search())
