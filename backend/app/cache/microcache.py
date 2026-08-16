"""
IPRED Chatbot - Microcaché con deduplicación de solicitudes en vuelo.
Implementa caché en memoria con TTL y coalescencia de requests idénticos.
"""

import asyncio
import time
from typing import Any
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """Entrada individual del caché."""
    value: Any
    created_at: float
    ttl: float
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) > self.ttl


class MicroCache:
    """
    Microcaché en memoria con TTL y deduplicación de solicitudes en vuelo.

    Características:
    - TTL configurable por entrada
    - Deduplicación: solicitudes idénticas en vuelo comparten un solo Future
    - Limpieza automática de entradas expiradas
    - Thread-safe para asyncio
    - Límite de concurrencia configurable
    """

    def __init__(self, default_ttl: float = 5.0, max_entries: int = 500):
        self._cache: dict[str, CacheEntry] = {}
        self._in_flight: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._stats = {"hits": 0, "misses": 0, "deduped": 0, "evictions": 0}

    async def get(self, key: str) -> Any | None:
        """Obtiene un valor del caché si existe y no ha expirado."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired:
                entry.hits += 1
                self._stats["hits"] += 1
                return entry.value
            if entry and entry.is_expired:
                del self._cache[key]
            self._stats["misses"] += 1
            return None

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Guarda un valor en el caché con TTL."""
        async with self._lock:
            # Evictar si estamos al límite
            if len(self._cache) >= self._max_entries:
                self._evict_oldest()

            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.monotonic(),
                ttl=ttl or self._default_ttl,
            )

    async def get_or_fetch(
        self,
        key: str,
        fetch_fn,
        ttl: float | None = None,
    ) -> Any:
        """
        Obtiene del caché o ejecuta fetch_fn. Deduplica solicitudes en vuelo.

        Si otra coroutine ya está fetching la misma key, espera su resultado
        en vez de hacer una segunda solicitud.
        """
        # 1. Intentar caché
        cached = await self.get(key)
        if cached is not None:
            return cached

        # 2. Verificar si hay un fetch en vuelo
        async with self._lock:
            if key in self._in_flight:
                self._stats["deduped"] += 1
                future = self._in_flight[key]
            else:
                future = asyncio.get_event_loop().create_future()
                self._in_flight[key] = future
                future = None  # Marcamos que nosotros somos los responsables

        if future is not None:
            # Esperar el resultado del fetch en curso
            return await self._in_flight[key]

        # 3. Somos los responsables: ejecutar fetch
        try:
            result = await fetch_fn()
            await self.set(key, result, ttl)

            async with self._lock:
                if key in self._in_flight:
                    self._in_flight[key].set_result(result)
                    del self._in_flight[key]

            return result

        except Exception as e:
            async with self._lock:
                if key in self._in_flight:
                    self._in_flight[key].set_exception(e)
                    del self._in_flight[key]
            raise

    def _evict_oldest(self) -> None:
        """Elimina las entradas más antiguas o expiradas."""
        # Primero eliminar expiradas
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for k in expired_keys:
            del self._cache[k]
            self._stats["evictions"] += 1

        # Si aún hay demasiadas, eliminar las menos usadas
        if len(self._cache) >= self._max_entries:
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: (self._cache[k].hits, self._cache[k].created_at),
            )
            to_remove = len(self._cache) - self._max_entries + 10
            for k in sorted_keys[:to_remove]:
                del self._cache[k]
                self._stats["evictions"] += 1

    async def clear(self) -> None:
        """Limpia todo el caché."""
        async with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> dict:
        return {**self._stats, "entries": len(self._cache)}


# Instancias globales de caché
cronograma_cache = MicroCache(default_ttl=5.0, max_entries=100)
info_fija_cache = MicroCache(default_ttl=3600.0, max_entries=200)
web_cache = MicroCache(default_ttl=300.0, max_entries=50)
respuesta_cache = MicroCache(default_ttl=60.0, max_entries=300)
