"""
IPRED Chatbot - Adaptador Asíncrono de Base de Datos para PostgreSQL y SQLite.
Permite ejecutar queries de forma transparente en ambos motores sin cambiar el código de negocio.
"""

import re
import logging
from typing import Any, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class PostgresCursorWrapper:
    """Cursor compatible con la interfaz de aiosqlite para resultados de asyncpg."""

    def __init__(self, records: List[Any], lastrowid: Optional[int] = None, rowcount: int = 0):
        self._records = records
        self._index = 0
        self.lastrowid = lastrowid
        self.rowcount = rowcount

    async def fetchall(self) -> List[Any]:
        return self._records

    async def fetchone(self) -> Optional[Any]:
        if self._index < len(self._records):
            rec = self._records[self._index]
            self._index += 1
            return rec
        return None


from datetime import datetime, date, time

def _normalize_param(p: Any) -> Any:
    if isinstance(p, str):
        # 1. Detectar cadenas de hora '06:00' o '18:30:00'
        if len(p) in (5, 8) and ":" in p and "-" not in p and " " not in p:
            try:
                return time.fromisoformat(p)
            except (ValueError, TypeError):
                pass
        # 2. Detectar cadenas ISO datetime o date '2026-08-15'
        if len(p) >= 10 and ("T" in p or "-" in p):
            try:
                if "T" in p or (" " in p and ":" in p):
                    return datetime.fromisoformat(p.replace(" ", "T"))
                elif len(p) == 10 and p.count("-") == 2:
                    return date.fromisoformat(p)
            except (ValueError, TypeError):
                pass
    return p

class PostgresConnectionWrapper:
    """Wrapper de conexión/pool asyncpg compatible con aiosqlite."""

    def __init__(self, pool):
        self._pool = pool

    def _convert_query(self, query: str) -> str:
        """Convierte marcadores de posición SQLite '?' a PostgreSQL '$1, $2...'."""
        # Convertir datetime('now') a NOW()
        q = re.sub(r"datetime\('now'\)", "NOW()", query, flags=re.IGNORECASE)
        # Convertir PRAGMA a SELECT vacío o compatible
        if q.strip().upper().startswith("PRAGMA"):
            return "SELECT 1"

        parts = q.split("?")
        if len(parts) == 1:
            return q
        result = []
        for i, part in enumerate(parts[:-1]):
            result.append(part)
            result.append(f"${i + 1}")
        result.append(parts[-1])
        return "".join(result)

    async def execute(self, query: str, params: Union[Tuple, List] = ()) -> PostgresCursorWrapper:
        converted_query = self._convert_query(query)
        # Manejo especial para INSERT con lastrowid
        is_insert = converted_query.strip().upper().startswith("INSERT")
        needs_returning = is_insert and "RETURNING" not in converted_query.upper()

        if needs_returning and not converted_query.strip().endswith(";"):
            converted_query = f"{converted_query} RETURNING id"

        clean_params = [_normalize_param(p) for p in params] if params else []

        async with self._pool.acquire() as conn:
            try:
                if clean_params:
                    records = await conn.fetch(converted_query, *clean_params)
                else:
                    records = await conn.fetch(converted_query)

                lastrowid = None
                if is_insert and records:
                    try:
                        lastrowid = records[0]["id"]
                    except (KeyError, IndexError, TypeError):
                        pass

                return PostgresCursorWrapper(records, lastrowid=lastrowid, rowcount=len(records))
            except Exception as e:
                # Si falló por RETURNING id en tabla sin columna id, reintentar query original
                if needs_returning:
                    clean_query = self._convert_query(query)
                    if clean_params:
                        records = await conn.fetch(clean_query, *clean_params)
                    else:
                        records = await conn.fetch(clean_query)
                    return PostgresCursorWrapper(records, rowcount=len(records))
                logger.error("Error ejecutando query PostgreSQL [%s]: %s", converted_query, e)
                raise

    async def executemany(self, query: str, seq_of_params: List[Union[Tuple, List]]) -> None:
        """Ejecuta una consulta por lotes masivos con executemany nativo en asyncpg."""
        converted_query = self._convert_query(query)
        
        # Convertir sintaxis SQLite 'INSERT OR REPLACE' a PostgreSQL 'ON CONFLICT DO UPDATE'
        if "INSERT OR REPLACE INTO" in converted_query.upper():
            converted_query = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", converted_query, flags=re.IGNORECASE)
            if "asignaturas" in converted_query.lower() and "ON CONFLICT" not in converted_query.upper():
                converted_query += " ON CONFLICT (codigo_asignatura, grupo, codigo_sede, id_semestre) DO UPDATE SET nombre_completo = EXCLUDED.nombre_completo, correo_institucional = EXCLUDED.correo_institucional"
            elif "horarios" in converted_query.lower() and "ON CONFLICT" not in converted_query.upper():
                converted_query += " ON CONFLICT (codigo_asignatura, grupo, fecha_tutoria, hora_inicio, hora_fin) DO UPDATE SET tipo_tutoria = EXCLUDED.tipo_tutoria"
            elif "ON CONFLICT" not in converted_query.upper():
                converted_query += " ON CONFLICT DO NOTHING"

        clean_seq = [[_normalize_param(p) for p in params] for params in seq_of_params] if seq_of_params else []

        async with self._pool.acquire() as conn:
            await conn.executemany(converted_query, clean_seq)

    async def executescript(self, script: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(script)

    async def commit(self) -> None:
        """En asyncpg en modo autocommit/pool no se requiere commit manual."""
        pass

    async def close(self) -> None:
        await self._pool.close()

