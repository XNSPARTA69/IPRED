"""
IPRED Chatbot - Router de autenticación.
Incluye rate limiting para protección contra ataques de fuerza bruta.
"""

from fastapi import APIRouter, Request, HTTPException, status
from app.models.user import (
    RegisterRequest, LoginRequest, RefreshRequest,
    TokenResponse, UserResponse,
)
from app.services import auth_service
from app.security.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, req: RegisterRequest):
    """Registrar un nuevo usuario."""
    try:
        user_id = await auth_service.register_user(
            username=req.username,
            password=req.password,
            email=req.email,
            nombre=req.nombre_completo,
        )
        return UserResponse(
            id=user_id,
            username=req.username,
            email=req.email,
            nombre_completo=req.nombre_completo,
        )
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nombre de usuario ya está registrado",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar usuario",
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("15/minute")
async def login(request: Request, req: LoginRequest):
    """Iniciar sesión y obtener tokens con rate limiting."""
    user = await auth_service.authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    access_token, expires_in = auth_service.create_access_token(
        user_id=user["id"],
        username=user["username"],
    )
    refresh_token = auth_service.create_refresh_token()
    await auth_service.save_refresh_token(user["id"], refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, req: RefreshRequest):
    """Renovar el access token usando el refresh token con rotación."""
    user_id = await auth_service.verify_refresh_token(req.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
        )

    # Revocar el refresh token usado (rotación segura)
    await auth_service.revoke_refresh_token(req.refresh_token)

    # Obtener datos del usuario
    from app.db.database import get_db
    db = await get_db()
    cursor = await db.execute("SELECT username FROM usuarios WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    # Generar nuevos tokens
    access_token, expires_in = auth_service.create_access_token(user_id, row["username"])
    new_refresh = auth_service.create_refresh_token()
    await auth_service.save_refresh_token(user_id, new_refresh)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=expires_in,
    )
