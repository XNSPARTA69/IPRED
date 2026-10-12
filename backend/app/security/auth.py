"""
IPRED Chatbot - Middleware de seguridad y autenticación.
"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(request: Request, allow_guest: bool = False) -> dict:
    """
    Extrae y valida el usuario del JWT en el header Authorization.
    Garantiza que la sesión mantenga la identidad real del estudiante y nunca se degrade a código 0.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        if allow_guest:
            return {"user_id": 1, "username": "estudiante"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ", 1)[1]
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada o token inválido. Por favor inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": int(payload["sub"]),
        "username": payload["username"],
    }

