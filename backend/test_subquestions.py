import asyncio
from app.services.chat_service import chat_service

async def test_subcategories_and_buttons():
    tests = [
        ("Subpregunta Modal: Cancelacion", "¿Cómo es el proceso oficial para cancelar una materia o el semestre?"),
        ("Subpregunta Modal: Requisitos Grado", "¿Cuáles son los requisitos oficiales y fechas de grado en el IPRED?"),
        ("Subpregunta Modal: Certificados", "¿Cómo solicito un certificado de notas o constancia de estudio?"),
        ("Subpregunta Modal: Paz y Salvo", "¿Cómo tramitar el paz y salvo institucional UIS?"),
        ("Subpregunta Modal: Moodle", "¿Cómo ingresar al aula virtual Moodle AVA y la plataforma IPRED TIC?"),
        ("Subpregunta Modal: Recuperar Clave", "¿Cómo recuperar mi contraseña del sistema de estudiantes o el correo institucional UIS?"),
        ("Subpregunta Modal: Calificaciones", "¿Dónde y cómo consulto mis calificaciones parciales y finales?"),
        ("Subpregunta Modal: Gratuidad", "¿Cuáles son los requisitos y cómo funciona la Política de Gratuidad en la matrícula?"),
        ("Subpregunta Modal: Descuento 10%", "¿Cómo aplicar el descuento del 10% en la matrícula con el certificado electoral?"),
        ("Subpregunta Modal: Sedes", "¿Cuáles son las sedes del IPRED, teléfonos y canales de atención?"),
        ("Subpregunta Modal: Carreras", "¿Cuáles son las carreras y programas académicos de pregrado que ofrece el IPRED?"),
    ]

    user_dict = {"user_id": 2, "username": "2226666"}
    for title, q in tests:
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
    asyncio.run(test_subcategories_and_buttons())
