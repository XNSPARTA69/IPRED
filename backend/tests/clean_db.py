import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import init_db, get_db, close_db

async def clear():
    await init_db()
    db = await get_db()
    m = await db.execute("DELETE FROM mensajes")
    c = await db.execute("DELETE FROM conversaciones")
    print(f"Limpieza completada: {c} conversaciones y {m} mensajes eliminados.")
    await close_db()

if __name__ == "__main__":
    asyncio.run(clear())
