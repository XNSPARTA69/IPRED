import asyncio
from app.services.busqueda_web_service import buscar_web_local

async def test_searxng():
    res = await buscar_web_local("rector de la UIS Universidad Industrial de Santander")
    print(f"Resultados SearXNG ({len(res)}):")
    for r in res:
        print(f"- {r.get('titulo')}: {r.get('url')}")

if __name__ == "__main__":
    asyncio.run(test_searxng())
