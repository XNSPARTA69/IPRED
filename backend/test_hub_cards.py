import asyncio
from app.services.chat_service import chat_service

async def test_hub_cards():
    cards = [
        ("1. Tarjeta Mis Materias", "¿Cuáles son las materias que tengo matriculadas este semestre?"),
        ("2. Tarjeta Mis Tutorías", "¿Cuándo son mis próximas tutorías y horarios de clase?"),
        ("3. Tarjeta Mis Profesores", "¿Quiénes son los profesores de mis asignaturas y sus correos?"),
        ("4. Tarjeta Calendario", "¿Cuál es mi calendario académico, próximas tutorías y fechas clave?"),
    ]

    user_dict = {"user_id": 2, "username": "2226666"}
    for title, q in cards:
        resp = await chat_service.process_user_message(q, user_dict=user_dict)
        tools = resp.herramientas_usadas or []
        tokens = resp.tokens_usados or 0
        tipo = "✅ ZERO-AI ($0.00 / 0 Tok)" if ("zero_ai_directa" in tools or tokens == 0) else f"🤖 GEMINI AI ({tokens} Tokens)"
        print(f"[{title}]")
        print(f"Q: \"{q}\"")
        print(f"Routing: {tipo}")
        print(f"R: {resp.respuesta[:90].replace(chr(10), ' ')}...")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(test_hub_cards())
