import asyncio
from app.services.chat_service import chat_service
from test_all_frontend_prompts import ALL_FRONTEND_PROMPTS

# Casos conversacionales y libres que NUNCA deben ser interceptados por Zero-AI
CONVERSATIONAL_CASES = [
    ("Conversacional 1: Cruce laboral", "¿Qué puedo hacer si tengo cruce de materias con mi trabajo los sábados?"),
    ("Conversacional 2: Explicación de fecha", "Oye, explícame qué materias veo el 22 de agosto y con qué profesores"),
    ("Conversacional 3: Duda de reglamento", "Si me enfermo y no voy a un examen, ¿cuántos días tengo para presentar la excusa médica y qué pasa con mi nota?"),
    ("Conversacional 4: Pregunta sobre electivas", "Quisiera saber qué electivas me recomiendas para complementar regencia de farmacia"),
    ("Conversacional 5: Pregunta combinada", "Dime si tengo clase mañana y quién es el profesor"),
]

async def verify_clean_division():
    print("================ 1. VERIFICANDO BOTONES OFICIALES FRONTEND (DEBEN SER ZERO-AI) ================")
    user_dict = {"user_id": 2, "username": "2226666"}
    
    frontend_zero_ai = 0
    for idx, (title, prompt) in enumerate(ALL_FRONTEND_PROMPTS, 1):
        resp = await chat_service.process_user_message(prompt, user_dict=user_dict)
        tools = resp.herramientas_usadas or []
        tokens = resp.tokens_usados or 0
        if "zero_ai_directa" in tools or tokens == 0:
            frontend_zero_ai += 1
            print(f"[{idx:02d}] {title} -> ✅ ZERO-AI ($0.00 / 0 Tok)")
        else:
            print(f"[{idx:02d}] {title} -> ❌ FALLÓ (Fue a Gemini AI)")

    print("\n================ 2. VERIFICANDO PREGUNTAS CONVERSACIONALES (DEBEN IR A GEMINI AI) ================")
    conv_gemini_ai = 0
    for idx, (title, prompt) in enumerate(CONVERSATIONAL_CASES, 1):
        resp = await chat_service.process_user_message(prompt, user_dict=user_dict)
        tools = resp.herramientas_usadas or []
        tokens = resp.tokens_usados or 0
        if tokens > 0 and "zero_ai_directa" not in tools:
            conv_gemini_ai += 1
            print(f"[{idx:02d}] {title} -> 🤖 GEMINI AI ({tokens} Tokens, tools={tools})")
        else:
            print(f"[{idx:02d}] {title} -> ❌ INTERCEPTADO POR ERROR EN ZERO-AI")

    print("\n================ RESUMEN FINAL ================")
    print(f"Botones Oficiales en Zero-AI: {frontend_zero_ai}/{len(ALL_FRONTEND_PROMPTS)} ({frontend_zero_ai/len(ALL_FRONTEND_PROMPTS)*100:.1f}%)")
    print(f"Preguntas Libres en Gemini AI: {conv_gemini_ai}/{len(CONVERSATIONAL_CASES)} ({conv_gemini_ai/len(CONVERSATIONAL_CASES)*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(verify_clean_division())
