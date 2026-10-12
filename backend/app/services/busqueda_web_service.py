"""
IPRED Chatbot - Servicio de búsqueda web local.
Integración con SearXNG para búsqueda de información universitaria.
"""

import logging
import httpx
from urllib.parse import urlparse
import trafilatura

from app.config import settings
from app.cache.microcache import info_fija_cache

logger = logging.getLogger(__name__)

# Dominios permitidos de confianza (whitelist SSRF)
DOMINIOS_PERMITIDOS = {
    "uis.edu.co",
    "ipredtic.uis.edu.co",
    "www.uis.edu.co",
    "portal.uis.edu.co",
    "academico.uis.edu.co",
    "biblioteca.uis.edu.co",
}

DOMINIOS_PRIORITARIOS = {
    "uis.edu.co": 5,  # Mayor relevancia
    "ipredtic.uis.edu.co": 10,
}


def _validar_url_segura(url: str, dominios_permitidos: set) -> bool:
    """Valida que una URL no sea un ataque SSRF."""
    try:
        parsed = urlparse(url)
        dominio = parsed.netloc.lower()
        
        # Rechazar localhost/IPs privadas
        if dominio in ("localhost", "127.0.0.1", "0.0.0.0"):
            return False
        if dominio.startswith("192.168.") or dominio.startswith("10.") or dominio.startswith("172."):
            return False
        
        # Verificar whitelist
        for dominio_permitido in dominios_permitidos:
            if dominio.endswith(dominio_permitido) or dominio == dominio_permitido:
                return True
        
        return False
    except Exception:
        return False


async def buscar_web_local(
    consulta: str,
    dominio_prioritario: str | None = None,
    max_resultados: int = 5,
) -> list[dict]:
    """
    Busca información en SearXNG configurado localmente.
    Solo devuelve resultados de dominios permitidos.

    Retorna: [{titulo, url, snippet}, ...]
    """
    cache_key = f"web:{consulta.lower()}:{dominio_prioritario or ''}"
    cached = await info_fija_cache.get(cache_key)
    if cached:
        logger.info("Caché HIT para búsqueda web: %s", consulta)
        return cached

    try:
        async with httpx.AsyncClient(timeout=settings.searxng_timeout_seconds) as client:
            response = await client.get(
                f"{settings.searxng_base_url}/search",
                params={
                    "q": consulta,
                    "format": "json",
                    "language": "es",
                    "safesearch": 1,  # Búsqueda segura
                },
                headers={"User-Agent": "IPRED-Chatbot/1.0"},
            )

            if response.status_code != 200:
                logger.warning("SearXNG error %d para búsqueda: %s", response.status_code, consulta)
                return []

            data = response.json()
            resultados_brutos = data.get("results", [])

    except httpx.TimeoutException:
        logger.warning("SearXNG timeout para búsqueda: %s", consulta)
        return []
    except Exception as e:
        logger.warning("Error consultando SearXNG: %s", e)
        return []

    # Filtrar por dominios permitidos y aplicar prioridad
    resultados_filtrados = []
    for item in resultados_brutos:
        url = item.get("url", "")
        if not url:
            continue

        # Validar seguridad de URL
        if not _validar_url_segura(url, DOMINIOS_PERMITIDOS):
            logger.debug("URL bloqueada por SSRF: %s", url)
            continue

        # Calcular score de relevancia por dominio
        score = 0
        for dominio_prioridad, prioridad in DOMINIOS_PRIORITARIOS.items():
            if dominio_prioridad in url:
                score = prioridad
                break

        resultados_filtrados.append({
            "titulo": item.get("title", "Sin título"),
            "url": url,
            "snippet": item.get("content", "")[:120].strip(),
            "_score": score,
        })

    # Ordenar por relevancia
    resultados_filtrados.sort(key=lambda x: -x["_score"])
    limite = min(max_resultados, settings.searxng_max_results)
    resultados_finales = [
        {"titulo": r["titulo"], "url": r["url"], "snippet": r["snippet"]}
        for r in resultados_filtrados[:limite]
    ]

    # Guardar en caché (360 segundos = 6 minutos)
    await info_fija_cache.set(cache_key, resultados_finales, ttl=360)

    logger.info("Búsqueda web: '%s' → %d resultados", consulta, len(resultados_finales))
    return resultados_finales


async def leer_pagina_web(url: str, max_bytes: int = 500000) -> str:
    """
    Lee y extrae el contenido de texto de una página web.
    Solo permite dominios whitelisted.
    Máximo 500 KB para evitar DoS.

    Retorna: texto limpio extraído
    """
    # Validar URL
    if not _validar_url_segura(url, DOMINIOS_PERMITIDOS):
        logger.warning("Intento de acceso a URL no permitida: %s", url)
        return ""

    if url.lower().endswith(".pdf"):
        return f"El enlace oficial de la UIS ({url}) es un archivo PDF de consulta reglamentaria."

    cache_key = f"web_content:{url}"
    cached = await info_fija_cache.get(cache_key)
    if cached:
        logger.info("Caché HIT para lectura de página: %s", url)
        return cached

    try:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(timeout=15, follow_redirects=httpx.USE_CLIENT_DEFAULT, limits=limits, verify=False) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "IPRED-Chatbot/1.0"},
            )

            if response.status_code != 200:
                logger.warning("Página HTTP %d: %s", response.status_code, url)
                return ""

            # Limitar tamaño
            content = response.content
            if len(content) > max_bytes:
                logger.warning("Página demasiado grande (%d bytes): %s", len(content), url)
                content = content[:max_bytes]

            # Extraer texto con trafilatura
            text = trafilatura.extract(
                content,
                include_comments=False,
                include_tables=True,
                favor_precision=True,
            )

            if not text:
                logger.warning("No se pudo extraer contenido de: %s", url)
                return ""

            # Limitar líneas
            lineas = text.split("\n")
            texto_final = "\n".join(lineas[:50])  # Máximo 50 líneas

            # Caché (3600 segundos = 1 hora)
            await info_fija_cache.set(cache_key, texto_final, ttl=3600)

            logger.info("Página extraída: %s (%d caracteres)", url, len(texto_final))
            return texto_final

    except httpx.TimeoutException:
        logger.warning("Timeout al leer página: %s", url)
        return ""
    except Exception as e:
        logger.warning("Error leyendo página %s: %s", url, e)
        return ""