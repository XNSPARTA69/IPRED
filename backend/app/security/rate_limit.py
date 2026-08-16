"""
IPRED Chatbot - Middleware de Rate Limiting.
"""

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings

def get_real_client_ip(request: Request) -> str:
    """Extrae la IP real del cliente detrás de Cloudflare y proxies Nginx."""
    # 1. Cloudflare header
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    # 2. X-Forwarded-For (primer IP de la cadena)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # 3. X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    # 4. Fallback estándar
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

limiter = Limiter(
    key_func=get_real_client_ip,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"]
)

def setup_rate_limiting(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
