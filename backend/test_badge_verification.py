import asyncio
from app.db.database import get_db
from app.services.chat_service import chat_service

async def run_badge_verification():
    print("=" * 70)
    print("🧪 VERIFICACIÓN DE CLASIFICACIÓN DE BADGES (ZERO-AI / IA / WEB)")
    print("=" * 70)

    user_dict = {"user_id": 2, "username": "2226666"}

    # Caso 1: Pregunta IA Local (Base de Conocimiento Fijo UIS)
    q1 = "¿Cuáles son las opciones de modalidad de grado en el IPRED según el reglamento?"
    print(f"\n[TEST 1 - IA LOCAL]: \"{q1}\"")
    r1 = await chat_service.process_user_message(q1, user_dict=user_dict)
    tools1 = r1.herramientas_usadas or []
    es_ia1 = r1.tokens_usados > 0
    es_web1 = bool(r1.es_web)
    print(f"-> Tokens: {r1.tokens_usados} | Tools: {tools1}")
    print(f"-> Badges generados: {'[✨ IA]' if es_ia1 else '[⚡ ZERO IA]'} {'[🌐 WEB]' if es_web1 else ''}")

    # Caso 2: Pregunta IA Externa (Requiere Búsqueda Web UIS en SearXNG)
    q2 = "¿Quién es el actual rector de la Universidad Industrial de Santander UIS y qué noticias recientes hay en la web?"
    print(f"\n[TEST 2 - IA + BÚSQUEDA WEB]: \"{q2}\"")
    r2 = await chat_service.process_user_message(q2, user_dict=user_dict)
    tools2 = r2.herramientas_usadas or []
    es_ia2 = r2.tokens_usados > 0
    es_web2 = bool(r2.es_web)
    print(f"-> Tokens: {r2.tokens_usados} | Tools: {tools2}")
    print(f"-> Badges generados: {'[✨ IA]' if es_ia2 else '[⚡ ZERO IA]'} {'[🌐 WEB]' if es_web2 else ''}")

    print("\n" + "=" * 70)
    print("✅ RESULTADOS DE LA PRUEBA:")
    print(f"Test 1 (IA Local): {'CORRECTO (Solo IA)' if (es_ia1 and not es_web1) else 'FALLÓ'}")
    print(f"Test 2 (IA Web):   {'CORRECTO (IA + WEB)' if (es_ia2 and es_web2) else 'FALLÓ'}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_badge_verification())
