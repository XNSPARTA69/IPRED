"""
IPRED Chatbot - Modelos Pydantic para usuarios, perfiles y autenticación.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re


# ============================================================
# Requests
# ============================================================

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    email: Optional[str] = Field(default=None, max_length=120)
    nombre_completo: Optional[str] = Field(default=None, max_length=200)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._@-]+$", v):
            raise ValueError("El username solo puede contener letras, números, '.', '_', '@' y '-'")
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe tener al menos una mayúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe tener al menos un número")
        return v


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


# ============================================================
# Responses
# ============================================================

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    nombre_completo: Optional[str] = None


# ============================================================
# Perfil
# ============================================================

class PerfilUpdate(BaseModel):
    programa_codigo: Optional[str] = None
    programa_nombre: Optional[str] = None
    sede_codigo: Optional[str] = None
    sede_nombre: Optional[str] = None
    semestre: Optional[str] = None
    jornada: Optional[str] = None
    grupo: Optional[str] = None
    asignaturas_interes: Optional[List[str]] = None
    idioma_preferido: Optional[str] = None


class PerfilResponse(BaseModel):
    usuario_id: int
    codigo_est: Optional[int] = None
    nombre_completo: Optional[str] = None
    primer_nombre: Optional[str] = None
    primer_apellido: Optional[str] = None
    programa_codigo: Optional[str] = None
    programa_nombre: Optional[str] = None
    sede_codigo: Optional[str] = None
    sede_nombre: Optional[str] = None
    semestre: Optional[str] = None
    jornada: Optional[str] = None
    grupo: Optional[str] = None
    asignaturas_interes: Optional[List[str]] = None
    idioma_preferido: str = "es"


# ============================================================
# Chat
# ============================================================

class ChatRequest(BaseModel):
    message: Optional[str] = Field(default=None, max_length=2000)
    mensaje: Optional[str] = Field(default=None, max_length=2000)
    conversacion_id: Optional[int] = None

    def get_message_text(self) -> str:
        text = self.message or self.mensaje or ""
        return text.strip()


class ChatResponse(BaseModel):
    respuesta: str
    conversacion_id: int
    fuentes: Optional[List[str]] = None
    herramientas_usadas: Optional[List[str]] = None
    tokens_usados: int = 0
    es_ia: bool = False
    es_web: bool = False

