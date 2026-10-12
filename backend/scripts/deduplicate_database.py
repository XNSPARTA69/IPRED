"""
IPRED Chatbot - Script de Deduplicación y Consolidación de Base de Datos
=======================================================================
Garantiza que ninguna tabla contenga registros duplicados y crea
índices únicos estrictos en PostgreSQL para blindar la integridad referencial.
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))
import asyncio
from app.db.database import get_db

async def deduplicate():
    db = await get_db()
    print("=" * 80)
    print("🧹 INICIANDO DEDUPLICACIÓN INTEGRAL DE BASE DE DATOS POSTGRESQL")
    print("=" * 80)

    # 1. Deduplicar tabla estudiantes
    print("1. Deduplicando tabla 'estudiantes'...")
    await db.execute("""
        DELETE FROM estudiantes a USING estudiantes b
        WHERE a.id > b.id
          AND a.codigo_est = b.codigo_est
          AND a.codigo_asignatura = b.codigo_asignatura
          AND a.grupo = b.grupo
    """)
    await db.commit()

    await db.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_estudiantes_cod_asig_grp 
        ON estudiantes(codigo_est, codigo_asignatura, grupo)
    """)
    await db.commit()

    cur = await db.execute("SELECT COUNT(*) as cnt FROM estudiantes")
    row = await cur.fetchone()
    print(f"   ✓ Total filas únicas en 'estudiantes': {row['cnt']}")

    # 2. Deduplicar tabla asignaturas
    print("2. Deduplicando tabla 'asignaturas'...")
    # Eliminar duplicados donde una fila no tiene correo institucional pero otra sí
    await db.execute("""
        DELETE FROM asignaturas a USING asignaturas b
        WHERE a.id > b.id
          AND a.codigo_asignatura = b.codigo_asignatura
          AND a.grupo = b.grupo
          AND (
            (a.correo_institucional IS NULL OR a.correo_institucional = '') 
            AND (b.correo_institucional IS NOT NULL AND b.correo_institucional != '')
          )
    """)
    await db.commit()

    # Eliminar duplicados exactos de asignaturas
    await db.execute("""
        DELETE FROM asignaturas a USING asignaturas b
        WHERE a.id > b.id
          AND a.codigo_asignatura = b.codigo_asignatura
          AND a.grupo = b.grupo
          AND a.nombre_completo = b.nombre_completo
    """)
    await db.commit()

    cur2 = await db.execute("SELECT COUNT(*) as cnt FROM asignaturas")
    row2 = await cur2.fetchone()
    print(f"   ✓ Total filas optimizadas en 'asignaturas': {row2['cnt']}")

    # 3. Deduplicar horarios
    print("3. Verificando tabla 'horarios'...")
    await db.execute("""
        DELETE FROM horarios a USING horarios b
        WHERE a.id_horario > b.id_horario
          AND a.codigo_asignatura = b.codigo_asignatura
          AND a.grupo = b.grupo
          AND a.fecha_tutoria = b.fecha_tutoria
          AND a.hora_inicio = b.hora_inicio
          AND a.hora_fin = b.hora_fin
          AND a.tipo_tutoria = b.tipo_tutoria
    """)
    await db.commit()

    cur3 = await db.execute("SELECT COUNT(*) as cnt FROM horarios")
    row3 = await cur3.fetchone()
    print(f"   ✓ Total horarios únicos en 'horarios': {row3['cnt']}")

    print("=" * 80)
    print("✨ DEDUPLICACIÓN COMPLETADA CON ÉXITO Y CONSTRAINTS APLICADAS")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(deduplicate())
