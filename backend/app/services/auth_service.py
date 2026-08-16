"""
IPRED Chatbot - Servicio de autenticación.
Argon2id para hashing, JWT para sesiones, refresh tokens rotativos.
"""

import json
import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings
from app.db.database import get_db

logger = logging.getLogger(__name__)

# Argon2id — parámetros aligerados para desarrollo (login ~100ms en vez de ~800ms).
# TODO producción: time_cost=3, memory_cost=65536, parallelism=4
_ph = PasswordHasher(
    time_cost=1,        # iteraciones
    memory_cost=16384,  # 16 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hashea una contraseña con Argon2id."""
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash Argon2id."""
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: int, username: str) -> tuple[str, int]:
    """Crea un JWT de acceso. Devuelve (token, expires_in_seconds)."""
    expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def create_refresh_token() -> str:
    """Genera un refresh token opaco seguro."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Hash SHA-256 del refresh token para almacenar en BD."""
    return hashlib.sha256(token.encode()).hexdigest()


def decode_access_token(token: str) -> dict | None:
    """Decodifica y valida un JWT de acceso."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def register_user(
    username: str, password: str, email: str | None = None, nombre: str | None = None
) -> int:
    """Registra un usuario nuevo. Devuelve el ID del usuario."""
    db = await get_db()
    pw_hash = hash_password(password)

    cursor = await db.execute(
        """INSERT INTO usuarios (username, password_hash, email, nombre_completo)
           VALUES (?, ?, ?, ?)""",
        (username, pw_hash, email, nombre),
    )
    await db.commit()
    user_id = cursor.lastrowid

    # Crear perfil vacío
    await db.execute(
        "INSERT INTO perfiles (usuario_id) VALUES (?)", (user_id,)
    )
    await db.commit()

    return user_id


async def authenticate_user(username: str, password: str) -> dict | None:
    """
    Autentica un usuario.
    Soporta auto-aprovisionamiento instantáneo para todos los estudiantes matriculados en la UIS
    y contraseñas estándar de prueba/acceso (123456, password123, o su mismo código).
    """
    clean_username = username.strip().lower()
    clean_password = password.strip()
    db = await get_db()
    
    # 1. Buscar en la tabla de usuarios
    cursor = await db.execute(
        "SELECT id, username, password_hash, email, nombre_completo FROM usuarios WHERE username = ? AND activo = true",
        (clean_username,),
    )
    row = await cursor.fetchone()
    
    # 2. Si no existe en usuarios, verificar si es un estudiante matriculado en 'estudiantes'
    if not row and clean_username.isdigit():
        codigo_num = int(clean_username)
        cur_est = await db.execute(
            """SELECT primer_nombre, primer_apellido, nombre_programa, nombre_sede 
               FROM estudiantes WHERE codigo_est = ? LIMIT 1""",
            (codigo_num,),
        )
        est_row = await cur_est.fetchone()
        if est_row:
            nombre = f"{est_row['primer_nombre']} {est_row['primer_apellido']}".strip().title()
            email = f"{codigo_num}@correo.uis.edu.co"
            effective_pw = clean_password if len(clean_password) >= 4 else "123456"
            pw_hash = hash_password(effective_pw)
            
            # Auto-registrar usuario
            cur_ins = await db.execute(
                """INSERT INTO usuarios (username, password_hash, email, nombre_completo)
                   VALUES (?, ?, ?, ?)""",
                (clean_username, pw_hash, email, nombre),
            )
            user_id = cur_ins.lastrowid
            
            # Crear perfil asociado con el estudiante
            await db.execute(
                """INSERT INTO perfiles (usuario_id, nombre, apellido, codigo_estudiante, programa_academico, sede)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    est_row["primer_nombre"].strip(),
                    est_row["primer_apellido"].strip(),
                    str(codigo_num),
                    est_row["nombre_programa"].strip(),
                    est_row["nombre_sede"].strip(),
                ),
            )
            await db.commit()
            
            logger.info("Estudiante %d auto-aprovisionado exitosamente en usuarios.", codigo_num)
            return {
                "id": user_id,
                "username": clean_username,
                "email": email,
                "nombre_completo": nombre,
            }
        return None

    if not row:
        return None

    # 3. Validar contraseña normal (probando original y trimmed)
    pw_valid = verify_password(clean_password, row["password_hash"]) or verify_password(password, row["password_hash"])
    
    # Si la contraseña no coincide pero es una de las contraseñas predeterminadas estándar (123456, password123 o código)
    if not pw_valid and (clean_password in ("123456", "password123", clean_username) or password in ("123456", "password123", clean_username)):
        new_hash = hash_password(clean_password)
        await db.execute(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?",
            (new_hash, row["id"]),
        )
        await db.commit()
        pw_valid = True

    if not pw_valid:
        return None

    # Actualizar last_login
    await db.execute(
        "UPDATE usuarios SET last_login = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), row["id"]),
    )
    await db.commit()

    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "nombre_completo": row["nombre_completo"],
    }


async def save_refresh_token(user_id: int, token: str) -> None:
    """Guarda el hash del refresh token en la BD."""
    db = await get_db()
    token_h = hash_token(token)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    await db.execute(
        """INSERT INTO refresh_tokens (usuario_id, token_hash, expires_at)
           VALUES (?, ?, ?)""",
        (user_id, token_h, expires.isoformat()),
    )
    await db.commit()


async def verify_refresh_token(token: str) -> int | None:
    """Verifica un refresh token. Devuelve el user_id o None."""
    db = await get_db()
    token_h = hash_token(token)
    cursor = await db.execute(
        """SELECT usuario_id, expires_at FROM refresh_tokens
           WHERE token_hash = ? AND revoked = 0""",
        (token_h,),
    )
    row = await cursor.fetchone()
    if not row:
        return None

    # Verificar expiración
    expires = datetime.fromisoformat(row["expires_at"])
    if datetime.now(timezone.utc) > expires:
        # Revocar token expirado
        await db.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?",
            (token_h,),
        )
        await db.commit()
        return None

    return row["usuario_id"]


async def revoke_refresh_token(token: str) -> None:
    """Revoca un refresh token."""
    db = await get_db()
    token_h = hash_token(token)
    await db.execute(
        "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?",
        (token_h,),
    )
    await db.commit()
