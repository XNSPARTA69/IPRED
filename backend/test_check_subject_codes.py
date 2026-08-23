import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.database import init_db, close_db, get_db

async def check():
    await init_db()
    db = await get_db()
    
    # 1. Total filas de estudiantes
    c_total = await (await db.execute("SELECT COUNT(*) FROM estudiantes;")).fetchone()
    # 2. Total con codigo_asignatura nulo o vacío
    c_empty = await (await db.execute("SELECT COUNT(*) FROM estudiantes WHERE codigo_asignatura IS NULL OR TRIM(codigo_asignatura) = '' OR TRIM(codigo_asignatura) = '-';")).fetchone()
    
    print(f"Total registros en tabla estudiantes: {c_total[0]}")
    print(f"Total con código de asignatura vacío o nulo: {c_empty[0]}")
    
    # 3. Muestra de 10 estudiantes
    cursor = await db.execute("SELECT DISTINCT codigo_est, primer_nombre, primer_apellido, codigo_asignatura, nombre_asignatura, grupo FROM estudiantes LIMIT 10;")
    rows = await cursor.fetchall()
    print("\n=== MUESTRA DE 10 REGISTROS DE ESTUDIANTES ===")
    for r in rows:
        d = dict(r)
        print(f"Estudiante: {d['codigo_est']} ({d['primer_nombre'].strip()}) | Cod Asig: {d['codigo_asignatura'].strip()} | Materia: {d['nombre_asignatura'].strip()} ({d['grupo'].strip()})")
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(check())
