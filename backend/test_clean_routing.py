import asyncio
from app.services.chat_service import chat_service

async def test_conversational_vs_zero_ai():
    queries = [
        ("1. Boton Saludo", "Hola, buenos dias"),
        ("2. Boton Mis Materias", "mis materias"),
        ("3. Boton Mis Tutorias", "mis tutorias"),
        ("4. Boton Calendario", "calendario academico"),
        ("5. Boton Mis Profesores", "mis profesores"),
        ("6. Boton Quien Soy", "quien soy"),
        ("7. Conversacional Compleja (Gemini AI)", "¿Qué recomendaciones me das si tengo cruce de materias con mi trabajo los sábados?"),
        ("8. Conversacional de Horarios (Gemini AI + Tool Calling)", "Oye, explícame qué materias veo el 22 de agosto y con qué profes"),
        ("9. Out of domain (0 tokens)", "¿Cómo hacer arroz chino?"),
    ]

    user_dict = {"user_id": 2, "username": "2226666"}
    for title, q in queries:
        resp = await chat_service.process_user_message(q, user_dict=user_dict)
        tools = resp.herramientas_usadas or []
        tokens = resp.tokens_usados or 0
        tipo = "✅ ZERO-AI ($0.00 / 0 Tok)" if ("zero_ai_directa" in tools or tokens == 0) else f"🤖 GEMINI AI ({tokens} Tokens, tools={tools})"
        print(f"[{title}]")
        print(f"Q: \"{q}\"")
        print(f"Routing: {tipo}")
        clean_first = resp.respuesta.replace("\n", " ")[:110]
        print(f"R: {clean_first}...")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(test_conversational_vs_zero_ai())
