"""
Utilidad institucional para purgar conversaciones y mensajes de prueba de la base de datos.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.database import init_db, get_db, close_db

async def clear_all_conversations():
    await init_db()
    db = await get_db()
    await db.execute("DELETE FROM mensajes")
    await db.execute("DELETE FROM conversaciones")
    c = (await (await db.execute("SELECT COUNT(*) FROM conversaciones")).fetchone())[0]
    m = (await (await db.execute("SELECT COUNT(*) FROM mensajes")).fetchone())[0]
    print(f"DB LIMPIA: {c} conversaciones, {m} mensajes.")
    await close_db()

if __name__ == "__main__":
    asyncio.run(clear_all_conversations())
