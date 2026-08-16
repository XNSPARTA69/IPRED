"""
IPRED Chatbot - Gestión de base de datos SQLite con aiosqlite.
Modo de inicialización no destructivo e idempotente.
"""

import aiosqlite
import json
import logging
import re
from pathlib import Path
from typing import Any, Union
from app.config import settings

logger = logging.getLogger(__name__)

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
POSTGRES_SCHEMA_PATH = BASE_DIR / "database_schema_postgres.sql"
JSON_DATA_PATH = BASE_DIR / "base_conocimiento_ipred_completa-v2 (1).json"
SQL_DATA_PATH = BASE_DIR / "database.sql"

_db_connection: Any = None
_is_postgres: bool = False


async def get_db() -> Any:
    """Obtiene la conexión activa a la base de datos con auto-inicialización segura."""
    global _db_connection
    if _db_connection is None:
        await init_db()
    return _db_connection


async def _cargar_datos_json_si_vacio() -> None:
    """Carga los datos del JSON solo si la tabla info_fija está vacía."""
    db = _db_connection
    cursor = await db.execute("SELECT COUNT(*) FROM info_fija")
    row = await cursor.fetchone()
    count = row[0] if isinstance(row, (tuple, list)) else (row["count"] if "count" in row else row[0])
    if count > 0:
        logger.info("Base de conocimiento ya poblada (%d chunks). Omitiendo carga JSON.", count)
        return

    if not JSON_DATA_PATH.exists():
        logger.warning("Archivo JSON no encontrado: %s", JSON_DATA_PATH)
        return

    try:
        with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        from app.services.info_fija_service import build_normalized_key

        for chunk in chunks:
            categoria = chunk.get("categoria", "General")
            titulo = chunk.get("id_chunk", "Sin título")
            contenido = chunk.get("contexto_para_ia", "")
            tags = " ".join(chunk.get("preguntas_entrenamiento", []))

            cursor = await db.execute(
                """INSERT INTO info_fija (categoria, subcategoria, titulo, contenido, tags)
                   VALUES (?, ?, ?, ?, ?)""",
                (categoria, "", titulo, contenido, tags),
            )
            id_info = cursor.lastrowid

            for pregunta in chunk.get("preguntas_entrenamiento", []):
                pregunta_norm = build_normalized_key(pregunta)
                await db.execute(
                    """INSERT INTO respuestas_directas (pregunta, pregunta_norm, respuesta, id_info, categoria, origen)
                       VALUES (?, ?, ?, ?, ?, 'json')""",
                    (pregunta, pregunta_norm, contenido, id_info, categoria),
                )

        await db.commit()
        logger.info("Cargados %d chunks del JSON exitosamente.", len(chunks))
    except Exception as e:
        logger.error("Error parseando JSON: %s", e)


async def init_db() -> None:
    """Inicializa la base de datos (PostgreSQL o SQLite según DATABASE_URL)."""
    global _db_connection, _is_postgres

    db_url = settings.database_url.strip()

    if db_url.startswith("postgresql") or db_url.startswith("postgres"):
        # Modo PostgreSQL
        import asyncpg
        from app.db.postgres_adapter import PostgresConnectionWrapper

        # Normalizar URL para asyncpg (remover sufijo +asyncpg si existiera)
        clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        logger.info("Iniciando conexión a PostgreSQL: %s", clean_url.split("@")[-1])

        pool = await asyncpg.create_pool(
            dsn=clean_url,
            min_size=5,
            max_size=50,
            statement_cache_size=100,
            command_timeout=30.0,
        )
        _db_connection = PostgresConnectionWrapper(pool)
        _is_postgres = True

        # Verificar si la base de datos ya está poblada (no reescribir nada si ya tiene datos)
        cursor_check = await _db_connection.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'estudiantes'"
        )
        row_check = await cursor_check.fetchone()
        table_exists = row_check[0] > 0 if row_check else False

        if not table_exists and POSTGRES_SCHEMA_PATH.exists():
            schema_sql = POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8")
            await _db_connection.executescript(schema_sql)
            logger.info("Base de datos PostgreSQL inicializada con esquema oficial.")
        else:
            logger.info("Base de datos PostgreSQL ya contiene datos activos. Omitiendo reescritura de esquema.")

        return

    # Modo SQLite (por defecto)
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _db_connection = await aiosqlite.connect(str(db_path))
    _db_connection.row_factory = aiosqlite.Row
    _is_postgres = False

    # Habilitar WAL, foreign keys y pragmas de optimización extrema
    await _db_connection.execute("PRAGMA journal_mode = WAL")
    await _db_connection.execute("PRAGMA foreign_keys = ON")
    await _db_connection.execute("PRAGMA synchronous = NORMAL")
    await _db_connection.execute("PRAGMA cache_size = -20000")  # 20MB de caché
    await _db_connection.execute("PRAGMA temp_store = MEMORY")

    # Ejecutar esquema idempotente
    if SCHEMA_PATH.exists():
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        await _db_connection.executescript(schema_sql)
        await _db_connection.commit()

    # Carga idempotente de datos si está vacía
    await _cargar_datos_json_si_vacio()

    logger.info("Base de datos SQLite inicializada y lista.")


async def close_db() -> None:
    """Cierra la conexión a la base de datos."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None

