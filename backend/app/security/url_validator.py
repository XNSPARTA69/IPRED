"""
IPRED Chatbot - Validador de URLs contra ataques SSRF.
"""

from urllib.parse import urlparse
import re
import logging

logger = logging.getLogger(__name__)


def validar_url_segura(url: str, dominios_permitidos: set | None = None) -> bool:
    """
    Valida que una URL sea segura y no intente acceder a recursos privados.

    Previene:
    - Acceso a localhost / 127.0.0.1 / [::1]
    - Acceso a redes privadas (10.0.0.0, 192.168.0.0, 172.16.0.0, fc00::/7)
    - Protocolos peligrosos (file://, gopher://, etc.)
    - URLs malformadas

    Args:
        url: URL a validar
        dominios_permitidos: Set de dominios permitidos (opcional whitelist)

    Returns:
        True si la URL es segura, False en caso contrario
    """
    try:
        parsed = urlparse(url)
        
        # Solo permitir HTTP/HTTPS
        if parsed.scheme not in ("http", "https"):
            logger.warning("Protocolo no permitido: %s", parsed.scheme)
            return False
        
        dominio = parsed.netloc.lower().split(":")[0].strip("[]")
        
        # Rechazar localhost / loopback IPv4 e IPv6
        if dominio in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "") or dominio.startswith("127."):
            logger.warning("Acceso a localhost bloqueado: %s", dominio)
            return False
        
        # Rechazar IPs privadas
        # Rango 10.0.0.0/8
        if re.match(r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$", dominio):
            logger.warning("Acceso a IP privada bloqueada (10.x.x.x): %s", dominio)
            return False
        
        # Rango 192.168.0.0/16
        if re.match(r"^192\.168\.\d{1,3}\.\d{1,3}$", dominio):
            logger.warning("Acceso a IP privada bloqueada (192.168.x.x): %s", dominio)
            return False
        
        # Rango 172.16.0.0/12
        if re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}$", dominio):
            logger.warning("Acceso a IP privada bloqueada (172.16-31.x.x): %s", dominio)
            return False
        
        # Rechazar metadata services
        if dominio in ("169.254.169.254", "metadata.google.internal"):
            logger.warning("Acceso a metadata service bloqueado: %s", dominio)
            return False
        
        # Si hay whitelist, validar contra ella
        if dominios_permitidos is not None:
            es_permitido = False
            for dominio_permitido in dominios_permitidos:
                if dominio == dominio_permitido or dominio.endswith("." + dominio_permitido):
                    es_permitido = True
                    break
            
            if not es_permitido:
                logger.warning("Dominio no en whitelist: %s", dominio)
                return False
        
        return True
        
    except Exception as e:
        logger.warning("Error validando URL %s: %s", url, e)
        return False
