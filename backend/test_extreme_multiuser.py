import asyncio
import time
from app.db.database import get_db
from app.services.chat_service import chat_service
from test_all_frontend_prompts import ALL_FRONTEND_PROMPTS

TEST_STUDENTS = [
    {"user_id": 2, "username": "2226666", "label": "Santiago Obregón (Farmacia)"},
    {"user_id": 8, "username": "2237184", "label": "Estudiante 2237184"},
    {"user_id": 9, "username": "2237391", "label": "Estudiante 2237391"},
    {"user_id": 10, "username": "2246020", "label": "Estudiante 2246020"},
    {"user_id": 14, "username": "2246209", "label": "Estudiante 2246209"},
]

ADDITIONAL_ZERO_AI_QUERIES = [
    ("Saludo 1", "Hola"),
    ("Saludo 2", "Buenos días"),
    ("Saludo 3", "Buenas tardes"),
    ("Despedida 1", "Muchas gracias"),
    ("Despedida 2", "Hasta luego"),
    ("Materia Código 1", "27338"),
    ("Materia Código 2", "27336"),
    ("Out of Context 1", "¿Cómo hacer arroz con pollo?"),
    ("Out of Context 2", "¿Quién ganó el partido de fútbol?"),
    ("Out of Context 3", "¿Cuál es el precio del bitcoin hoy?"),
    ("Perfil Corto", "quién soy"),
    ("Perfil Largo", "ver mi perfil"),
]

async def run_extreme_stress_test():
    print("=" * 80)
    print("🚀 INICIANDO TESTING EXTREMO MULTIUSUARIO DE ZERO-AI ($0.00 COP / 0 TOKENS)")
    print("=" * 80)

    total_requests = 0
    zero_ai_success = 0
    gemini_fallbacks = 0
    errors = 0
    latencies = []

    start_time_all = time.time()

    # 1. Ejecutar las 33 opciones del frontend por cada estudiante
    for est in TEST_STUDENTS:
        print(f"\n👤 [PROBANDO USUARIO: {est['label']} (Código: {est['username']})]")
        user_dict = {"user_id": est["user_id"], "username": est["username"]}

        for title, prompt in ALL_FRONTEND_PROMPTS:
            t0 = time.time()
            try:
                resp = await chat_service.process_user_message(prompt, user_dict=user_dict)
                elapsed = (time.time() - t0) * 1000
                latencies.append(elapsed)
                total_requests += 1

                tools = resp.herramientas_usadas or []
                tokens = resp.tokens_usados or 0

                if "zero_ai_directa" in tools or tokens == 0:
                    zero_ai_success += 1
                else:
                    gemini_fallbacks += 1
                    print(f"  ❌ Fuga a Gemini AI en '{title}': {tokens} tokens")
            except Exception as e:
                errors += 1
                print(f"  💥 ERROR en '{title}': {e}")

        # Ejecutar preguntas adicionales de Zero-AI
        for title, prompt in ADDITIONAL_ZERO_AI_QUERIES:
            t0 = time.time()
            try:
                resp = await chat_service.process_user_message(prompt, user_dict=user_dict)
                elapsed = (time.time() - t0) * 1000
                latencies.append(elapsed)
                total_requests += 1

                tools = resp.herramientas_usadas or []
                tokens = resp.tokens_usados or 0

                if "zero_ai_directa" in tools or tokens == 0:
                    zero_ai_success += 1
                else:
                    gemini_fallbacks += 1
                    print(f"  ❌ Fuga a Gemini AI en '{title}': {tokens} tokens")
            except Exception as e:
                errors += 1
                print(f"  💥 ERROR en '{title}': {e}")

        print(f"  -> {len(ALL_FRONTEND_PROMPTS) + len(ADDITIONAL_ZERO_AI_QUERIES)} pruebas ejecutadas exitosamente.")

    # 2. Prueba de concurrencia masiva simultánea (10 requests en paralelo)
    print("\n⚡ [PROBANDO CONCURRENCIA MASIVA SIMULTÁNEA: 10 HILOS EN PARALELO]")
    concurrency_prompts = [
        "¿Cuáles son las materias que tengo matriculadas este semestre?",
        "¿Cuándo son mis próximas tutorías y horarios de clase?",
        "¿Quiénes son los profesores de mis asignaturas y sus correos?",
        "¿Cuál es mi calendario académico, próximas tutorías y fechas clave?",
        "¿Cómo es el proceso oficial para cancelar una materia o el semestre?",
        "¿Cuáles son los requisitos oficiales y fechas de grado en el IPRED?",
        "¿Cómo ingresar al aula virtual Moodle AVA y la plataforma IPRED TIC?",
        "¿Cuáles son las sedes del IPRED, teléfonos y canales de atención?",
        "¿Cómo descargar mi volante de liquidación de matrícula y qué métodos de pago hay?",
        "Hola, buenos días",
    ]

    async def single_concurrent_req(p):
        t0 = time.time()
        user_dict = {"user_id": 2, "username": "2226666"}
        res = await chat_service.process_user_message(p, user_dict=user_dict)
        el = (time.time() - t0) * 1000
        return res, el

    conc_results = await asyncio.gather(*(single_concurrent_req(p) for p in concurrency_prompts))
    for res, el in conc_results:
        latencies.append(el)
        total_requests += 1
        tools = res.herramientas_usadas or []
        tokens = res.tokens_usados or 0
        if "zero_ai_directa" in tools or tokens == 0:
            zero_ai_success += 1
        else:
            gemini_fallbacks += 1

    total_time = time.time() - start_time_all
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    print("\n" + "=" * 80)
    print("📊 RESULTADOS DEL TESTING EXTREMO ZERO-AI")
    print("=" * 80)
    print(f"Total Requests Ejecutados: {total_requests}")
    print(f"✅ Respuestas en Modo Zero-AI: {zero_ai_success} ({(zero_ai_success/total_requests)*100:.2f}%)")
    print(f"🤖 Fugas a Gemini AI (Tokens Gastados): {gemini_fallbacks}")
    print(f"💥 Errores o Excepciones: {errors}")
    print(f"⏱️ Tiempo Total de la Batería: {total_time:.2f} segundos")
    print(f"⚡ Latencia Promedio por Request: {avg_latency:.2f} ms")
    print(f"🚀 Throughput Estimado: {total_requests / total_time:.1f} requests/segundo")
    print("=" * 80)

    # 3. Limpieza completa de todas las conversaciones en la base de datos
    print("\n🧹 [INICIANDO PURGA DE TODAS LAS CONVERSACIONES EN BASE DE DATOS]")
    db = await get_db()
    try:
        cur_m = await db.execute("DELETE FROM mensajes;")
        cur_c = await db.execute("DELETE FROM conversaciones;")
        await db.commit()
        print("✅ TODAS LAS CONVERSACIONES Y MENSAJES FUERON BORRADOS COMPLETAMENTE.")
    except Exception as e:
        print(f"❌ Error durante la purga de conversaciones: {e}")

if __name__ == "__main__":
    asyncio.run(run_extreme_stress_test())
