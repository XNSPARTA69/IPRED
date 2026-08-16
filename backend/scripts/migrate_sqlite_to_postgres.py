"""
IPRED Chatbot - Script de Migración de SQLite a PostgreSQL.
Lee los 6,826 estudiantes, 1,656 materias y 18,070 horarios de SQLite y los inserta en PostgreSQL.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
import asyncio
import sqlite3
import time
import os

try:
    import psycopg
except ImportError:
    psycopg = None

SQLITE_PATH = "data/ipred_chatbot.db"
PG_DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://ipred_user:ipred_secure_password_2026!@localhost:5432/ipred_chatbot"
)


def migrate():
    print("=" * 80)
    print("🚀 MIGRACIÓN DE BASE DE DATOS: SQLite ➔ PostgreSQL")
    print("=" * 80)

    if not os.path.exists(SQLITE_PATH):
        print(f"[❌] No se encontró el archivo SQLite en {SQLITE_PATH}")
        return

    if psycopg is None:
        print("[!] Nota: Librería 'psycopg' no instalada en este entorno virtual.")
        print("    Para ejecutar la migración, corre: pip install psycopg[binary]")
        return

    try:
        pg_conn = psycopg.connect(PG_DSN, autocommit=True)
        print(f"[✓] Conexión establecida con PostgreSQL exitosamente.")
    except Exception as e:
        print(f"[❌] Error conectando a PostgreSQL ({PG_DSN}): {e}")
        return

    # Aplicar esquema actualizado
    schema_path = os.path.join(os.path.dirname(__file__), "..", "database_schema_postgres.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as sf:
            schema_ddl = sf.read()
        with pg_conn.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS usuarios, perfiles, info_fija, respuestas_directas CASCADE;
            """)
            cur.execute(schema_ddl)
        print("[✓] Esquema DDL PostgreSQL aplicado correctamente.")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    s_cur = sqlite_conn.cursor()

    t0 = time.time()

    # 1. Migrar Estudiantes
    print("\n[*] Migrando tabla 'estudiantes'...")
    s_cur.execute("SELECT codigo_est, primer_apellido, primer_nombre, programa_academico, nombre_programa, codigo_sede, nombre_sede, codigo_asignatura, grupo, nombre_asignatura, pass FROM estudiantes")
    est_rows = [tuple(r) for r in s_cur.fetchall()]
    with pg_conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE estudiantes RESTART IDENTITY CASCADE;")
        cur.executemany(
            """INSERT INTO estudiantes (codigo_est, primer_apellido, primer_nombre,
                                      programa_academico, nombre_programa, codigo_sede,
                                      nombre_sede, codigo_asignatura, grupo,
                                      nombre_asignatura, pass)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            est_rows
        )
    print(f"[✓] {len(est_rows)} estudiantes migrados.")

    # 2. Migrar Asignaturas
    print("\n[*] Migrando tabla 'asignaturas'...")
    s_cur.execute("SELECT codigo_programa, nombre_programa, codigo_sede, codigo_asignatura, nombre_asignatura, id_semestre, grupo, nombre_completo, correo_institucional FROM asignaturas")
    asig_rows = [tuple(r) for r in s_cur.fetchall()]
    with pg_conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE asignaturas RESTART IDENTITY CASCADE;")
        cur.executemany(
            """INSERT INTO asignaturas (codigo_programa, nombre_programa, codigo_sede,
                                       codigo_asignatura, nombre_asignatura, id_semestre,
                                       grupo, nombre_completo, correo_institucional)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            asig_rows
        )
    print(f"[✓] {len(asig_rows)} asignaturas migradas.")

    # 3. Migrar Horarios
    print("\n[*] Migrando tabla 'horarios'...")
    s_cur.execute("SELECT codigo_asignatura, grupo, fecha_tutoria, hora_inicio, hora_fin, tipo_tutoria FROM horarios")
    hor_rows = [tuple(r) for r in s_cur.fetchall()]
    with pg_conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE horarios RESTART IDENTITY CASCADE;")
        cur.executemany(
            """INSERT INTO horarios (codigo_asignatura, grupo, fecha_tutoria,
                                    hora_inicio, hora_fin, tipo_tutoria)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            hor_rows
        )
    print(f"[✓] {len(hor_rows)} horarios migrados.")

    # 4. Migrar Info Fija
    print("\n[*] Migrando tabla 'info_fija'...")
    s_cur.execute("SELECT categoria, titulo, contenido, tags FROM info_fija")
    info_rows = []
    for r in s_cur.fetchall():
        info_rows.append((r["categoria"], r["titulo"], r["contenido"], r["tags"] or "", "", True))
    with pg_conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE info_fija RESTART IDENTITY CASCADE;")
        cur.executemany(
            """INSERT INTO info_fija (categoria, titulo, contenido, palabras_clave, enlaces_utiles, activo)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            info_rows
        )
    print(f"[✓] {len(info_rows)} registros de información fija migrados.")

    # 5. Migrar Respuestas Directas (Capa 0)
    print("\n[*] Migrando tabla 'respuestas_directas'...")
    try:
        s_cur.execute("SELECT pregunta, pregunta_norm, respuesta, categoria FROM respuestas_directas")
        rd_rows = [tuple(r) for r in s_cur.fetchall()]
        with pg_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE respuestas_directas RESTART IDENTITY CASCADE;")
            cur.executemany(
                """INSERT INTO respuestas_directas (pregunta, pregunta_norm, respuesta, categoria)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (pregunta_norm) DO NOTHING""",
                rd_rows
            )
        print(f"[✓] {len(rd_rows)} respuestas directas migradas.")
    except Exception as e:
        print(f"[!] Info: {e}")

    # 6. Migrar Usuarios
    print("\n[*] Migrando tabla 'usuarios'...")
    try:
        s_cur.execute("SELECT username, password_hash, email, nombre_completo, activo FROM usuarios")
        u_rows = [(r["username"], r["password_hash"], r["email"], r["nombre_completo"], "student", r["activo"]) for r in s_cur.fetchall()]
        with pg_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE usuarios RESTART IDENTITY CASCADE;")
            cur.executemany(
                """INSERT INTO usuarios (username, password_hash, email, nombre_completo, rol, activo)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (username) DO NOTHING""",
                u_rows
            )
        print(f"[✓] {len(u_rows)} usuarios migrados.")
    except Exception as e:
        print(f"[!] Info usuarios: {e}")

    # 7. Refrescar Vista Materializada Pre-calculada
    print("\n[*] Pre-calculando vista materializada de estudiantes...")
    try:
        with pg_conn.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW vista_carga_estudiantes;")
        print("[✓] Vista materializada 'vista_carga_estudiantes' pre-calculada y lista.")
    except Exception as e:
        print(f"[!] Error refrescando vista: {e}")

    t_total = time.time() - t0
    print("\n" + "=" * 80)
    print(f"[🎉] ¡MIGRACIÓN COMPLETADA EXITOSAMENTE EN {t_total:.2f} SEGUNDOS!")
    print("=" * 80)

    sqlite_conn.close()
    pg_conn.close()


if __name__ == "__main__":
    migrate()
