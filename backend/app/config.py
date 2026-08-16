"""
IPRED Chatbot - Configuración central.
Carga todas las variables de entorno y define los settings de la aplicación.
"""

from pathlib import Path
import logging
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""

    # --- JWT ---
    jwt_secret: str = Field(default="dev-secret-change-in-production-32chars!")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60 * 24 * 30)  # 30 días de sesión activa
    jwt_refresh_token_expire_days: int = Field(default=90)  # 90 días para refresco seguro

    # --- Base de datos ---
    database_url: str = Field(default="sqlite:///./data/ipred_chatbot.db")

    # --- Google Gemini AI ---
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-3.5-flash-lite")

    # --- IPRED Endpoint ---
    ipred_base_url: str = Field(default="https://ipredtic.uis.edu.co/plataformaticv2/")
    ipred_timeout_seconds: int = Field(default=10)
    ipred_max_retries: int = Field(default=2)

    # --- SearXNG ---
    searxng_base_url: str = Field(default="http://searxng:8080")
    searxng_timeout_seconds: int = Field(default=5)
    searxng_max_results: int = Field(default=3)

    # --- Rate Limiting ---
    rate_limit_per_minute: int = Field(default=30)

    # --- App ---
    app_name: str = Field(default="IPRED Chatbot UIS")
    app_version: str = Field(default="1.0.0")
    app_debug: bool = Field(default=True)
    allowed_origins: str = Field(
        default="http://localhost:*,http://127.0.0.1:*,http://localhost:3000,http://localhost:8081,http://localhost:7777,http://localhost:8080,http://127.0.0.1:7777,http://127.0.0.1:8080,http://127.0.0.1:3000"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def db_path(self) -> Path:
        """Extrae la ruta del archivo SQLite."""
        path_str = self.database_url.replace("sqlite:///", "")
        return Path(path_str)


settings = Settings()

# Zona Horaria Oficial Colombia (America/Bogota - UTC-5 sin cambio de horario)
from datetime import datetime, timezone, timedelta
TIMEZONE_COLOMBIA = timezone(timedelta(hours=-5), name="America/Bogota")

def get_colombia_now() -> datetime:
    """Retorna la fecha y hora actual exacta en la zona horaria de Colombia (UTC-5)."""
    return datetime.now(TIMEZONE_COLOMBIA)

# Validación de seguridad en startup
if not settings.app_debug and settings.jwt_secret.startswith("dev-secret"):
    logger.critical("ADVERTENCIA DE SEGURIDAD: Se está ejecutando en modo producción con el JWT_SECRET por defecto.")

