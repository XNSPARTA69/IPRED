"""
IPRED Chatbot - Servicio del cronograma IPRED.
Consulta el endpoint AJAX, parsea, normaliza y filtra los datos.
"""

import asyncio
import logging
from datetime import datetime

import httpx
from pydantic import ValidationError

from app.config import settings
from app.models.cronograma import (
    ActividadIPRED,
    ActividadNormalizada,
    AsignaturaBloque,
    CronogramaQuery,
)
from app.cache.microcache import cronograma_cache

logger = logging.getLogger(__name__)

# Semáforo para limitar concurrencia al endpoint IPRED
_ipred_semaphore = asyncio.Semaphore(3)

# Tipos de actividad conocidos
TIPO_ACTIVIDAD_NOMBRES = {
    1: "Clase Magistral",
    2: "TI (Trabajo Individual)",
    3: "TT (Trabajo Tutorial)",
    4: "Examen",
    5: "Laboratorio",
    6: "Taller",
}


def _build_cache_key(query: CronogramaQuery) -> str:
    """Construye la clave del microcaché."""
    parts = [
        f"crono:{query.semestre}:{query.programa}:{query.sede}",
        f":{query.jornada}:{query.fecha_inicial}:{query.fecha_final}",
    ]
    return "".join(parts)


async def _fetch_from_ipred(query: CronogramaQuery) -> list[dict]:
    """
    Realiza la solicitud HTTP real al endpoint IPRED.
    Retorna la lista de bloques JSON sin procesar.
    """
    url = f"{settings.ipred_base_url}?ajax=CronogramaPublico&action=buscarCronograma"

    form_data = {
        "semestre": query.semestre,
        "programa": query.programa,
        "sede": query.sede,
        "fechaInicial": query.fecha_inicial,
        "fechaFinal": query.fecha_final,
        "jornada": query.jornada,
    }

    last_error = None
    for attempt in range(1, settings.ipred_max_retries + 2):  # 1 intento + N reintentos
        try:
            async with _ipred_semaphore:
                async with httpx.AsyncClient(timeout=settings.ipred_timeout_seconds) as client:
                    response = await client.post(
                        url,
                        data=form_data,
                        headers={
                            "User-Agent": "IPRED-Chatbot-UIS/1.0",
                            "Accept": "application/json",
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        logger.info(
                            "IPRED endpoint OK (attempt %d): %d bloques recibidos",
                            attempt,
                            len(data) if isinstance(data, list) else 0,
                        )
                        return data if isinstance(data, list) else []

                    elif 400 <= response.status_code < 500:
                        logger.warning(
                            "IPRED endpoint client error %d (no retry): %s",
                            response.status_code,
                            response.text[:200],
                        )
                        return []  # Error de parámetros, no reintentar

                    else:
                        last_error = f"HTTP {response.status_code}"
                        logger.warning(
                            "IPRED endpoint error %d (attempt %d/%d)",
                            response.status_code,
                            attempt,
                            settings.ipred_max_retries + 1,
                        )

        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            last_error = str(e)
            logger.warning(
                "IPRED endpoint error (attempt %d/%d): %s",
                attempt,
                settings.ipred_max_retries + 1,
                e,
            )

        # Backoff antes del reintento
        if attempt <= settings.ipred_max_retries:
            await asyncio.sleep(attempt * 1.5)

    logger.error("IPRED endpoint failed after %d attempts: %s", settings.ipred_max_retries + 1, last_error)
    return []


def _parse_and_normalize(raw_data: list[dict]) -> list[ActividadNormalizada]:
    """
    Parsea la respuesta del endpoint IPRED y la normaliza.
    Pipeline: JSON → Pydantic → Aplanar → Normalizar.
    """
    actividades: list[ActividadNormalizada] = []

    for item in raw_data:
        try:
            bloque = AsignaturaBloque(**item)
            for act in bloque.actividades:
                normalizada = ActividadNormalizada.from_ipred(bloque, act)
                actividades.append(normalizada)
        except (ValidationError, KeyError, TypeError) as e:
            logger.warning("Error parseando bloque IPRED: %s — %s", e, str(item)[:100])
            continue

    return actividades


def _filter_actividades(
    actividades: list[ActividadNormalizada],
    grupo: str | None = None,
    asignatura: str | None = None,
    fecha: str | None = None,
) -> list[ActividadNormalizada]:
    """Filtra las actividades normalizadas según los criterios del usuario."""
    result = actividades

    if grupo:
        result = [a for a in result if a.grupo.upper() == grupo.upper()]

    if asignatura:
        asig_lower = asignatura.lower()
        result = [a for a in result if asig_lower in a.asignatura.lower()]

    if fecha:
        result = [a for a in result if a.inicio.startswith(fecha)]

    return result


async def consultar_cronograma(
    query: CronogramaQuery,
    grupo_filtro: str | None = None,
    asignatura_filtro: str | None = None,
    fecha_filtro: str | None = None,
) -> list[dict]:
    """
    Consulta el cronograma IPRED con microcaché y deduplicación.
    Devuelve actividades normalizadas y filtradas como dicts.
    """
    cache_key = _build_cache_key(query)

    async def _do_fetch():
        raw = await _fetch_from_ipred(query)
        return _parse_and_normalize(raw)

    # Obtener del caché o consultar (con deduplicación)
    actividades: list[ActividadNormalizada] = await cronograma_cache.get_or_fetch(
        key=cache_key,
        fetch_fn=_do_fetch,
        ttl=5.0,  # 5 segundos microcaché
    )

    # Filtrar en backend ANTES de enviar al modelo
    filtered = _filter_actividades(
        actividades,
        grupo=grupo_filtro,
        asignatura=asignatura_filtro,
        fecha=fecha_filtro,
    )

    # Devolver como dicts compactos (solo campos relevantes para la IA)
    return [
        {
            "asignatura": a.asignatura,
            "grupo": a.grupo,
            "profesor": a.profesor,
            "inicio": a.inicio,
            "fin": a.fin,
            "tipo": a.tipo_actividad,
            "aula": a.aula,
        }
        for a in filtered
    ]


async def consultar_sedes_programas(semestre: str | None = None) -> dict:
    """Consulta sedes y programas disponibles desde el endpoint IPRED."""
    url = f"{settings.ipred_base_url}?ajax=CronogramaPublico&action=consultarSedesProgramas"

    try:
        async with httpx.AsyncClient(timeout=settings.ipred_timeout_seconds) as client:
            form_data = {}
            if semestre:
                form_data["semestre"] = semestre
            response = await client.post(url, data=form_data)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning("Error consultando sedes/programas IPRED: %s", e)

    return {}
