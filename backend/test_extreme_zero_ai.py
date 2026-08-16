import asyncio
from app.services.chat_service import chat_service

async def run_extreme_testing():
    test_cases = [
        ("1. Fecha Relativa Hoy", "¿Tengo clase hoy?"),
        ("2. Fecha Relativa Mañana", "¿Qué clases tengo mañana?"),
        ("3. Fecha Relativa Próximo Sábado", "¿A qué hora tengo clases el próximo sábado?"),
        ("4. Fecha Relativa Fin de Semana", "¿Qué clases veo este fin de semana?"),
        ("5. Materia por Nombre (Farmacognosia)", "¿Cuándo tengo clases de farmacognosia?"),
        ("6. Materia por Nombre (Salud Pública)", "¿A qué hora es salud publica?"),
        ("7. Docente por Nombre de Materia", "¿Quién es el profesor de farmacovigilancia?"),
        ("8. Ficha de Perfil", "¿Quién soy y en qué sede estoy?"),
        ("9. Escala de Notas", "¿Con cuánto se aprueba una materia?"),
        ("10. Matrícula Asignaturas", "¿Cómo matriculo mis materias?"),
        ("11. Cancelación Asignaturas", "¿Cómo cancelo una materia?"),
        ("12. Requisitos de Grado", "¿Cuáles son los requisitos de grado?"),
        ("13. Descuento Electoral", "¿Cómo obtengo el descuento por votar?"),
        ("14. Out-of-domain (Receta)", "¿Cómo hacer arroz con pollo?"),
    ]

    user_dict = {"user_id": 2, "username": "2226666"}
    
    print("================ INICIANDO TESTING EXTREMO ZERO-AI ================\n")
    zero_ai_count = 0
    ai_count = 0
    
    for category, query in test_cases:
        resp = await chat_service.process_user_message(query, user_dict=user_dict)
        tools = resp.herramientas_usadas or []
        tokens = resp.tokens_usados or 0
        
        is_zero_ai = "zero_ai_directa" in tools or tokens == 0
        if is_zero_ai:
            zero_ai_count += 1
            status = "✅ ZERO-AI ($0.00 COP / 0 tokens)"
        else:
            ai_count += 1
            status = f"🤖 GEMINI AI ({tokens} tokens)"
            
        print(f"[{category}]")
        print(f"💬 Query: \"{query}\"")
        print(f"⚡ Modo: {status}")
        first_line = resp.respuesta.strip().split("\n")[0][:100]
        print(f"📋 Respuesta: {first_line}...")
        print("-" * 70)

    print(f"\n================ RESUMEN DE EFICIENCIA ================")
    print(f"TOTAL PRUEBAS: {len(test_cases)}")
    print(f"ZERO-AI (0 Tokens): {zero_ai_count} ({round(zero_ai_count/len(test_cases)*100, 1)}%)")
    print(f"GEMINI AI: {ai_count} ({round(ai_count/len(test_cases)*100, 1)}%)")

if __name__ == "__main__":
    asyncio.run(run_extreme_testing())
