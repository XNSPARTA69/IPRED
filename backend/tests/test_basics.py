"""
IPRED Chatbot - Tests unitarios e integración básicos.
Ejecutar con: pytest tests/
"""

import pytest
from datetime import datetime, timedelta
import jwt
from unittest.mock import AsyncMock, patch

# ============================================================
# TEST AUTENTICACIÓN
# ============================================================

def test_hash_password():
    """Verifica que el hashing de contraseñas funciona correctamente."""
    from app.services.auth_service import hash_password, verify_password
    
    password = "TestPassword123"
    password_hash = hash_password(password)
    
    # El hash debe ser diferente del password
    assert password_hash != password
    
    # La verificación debe ser exitosa
    assert verify_password(password, password_hash) is True
    
    # Una contraseña incorrecta debe fallar
    assert verify_password("WrongPassword123", password_hash) is False


def test_jwt_token_creation():
    """Verifica que se crean tokens JWT válidos."""
    from app.services.auth_service import create_access_token, decode_access_token
    from app.config import settings
    
    user_id = 42
    username = "estudiante"
    
    token, expires_in = create_access_token(user_id, username)
    
    # El token debe ser un string
    assert isinstance(token, str)
    assert len(token) > 0
    
    # El tiempo de expiración debe ser positivo (en segundos)
    assert expires_in == settings.jwt_access_token_expire_minutes * 60
    
    # La decodificación debe recuperar el payload
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["username"] == username
    assert payload["type"] == "access"


def test_jwt_token_expiration():
    """Verifica que los tokens caducados se rechazan."""
    from app.services.auth_service import decode_access_token
    import jwt as pyjwt
    from app.config import settings
    
    from datetime import timezone
    past_expire = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {
        "sub": "42",
        "username": "estudiante",
        "exp": past_expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    expired_token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    
    # La decodificación debe fallar
    result = decode_access_token(expired_token)
    assert result is None


# ============================================================
# TEST VALIDACIÓN DE URLS (SSRF)
# ============================================================

def test_url_validator_localhost():
    """Verifica que se bloquean accesos a localhost."""
    from app.security.url_validator import validar_url_segura
    
    assert validar_url_segura("http://localhost:8000") is False
    assert validar_url_segura("http://127.0.0.1:8000") is False
    assert validar_url_segura("http://[::1]") is False


def test_url_validator_private_ips():
    """Verifica que se bloquean accesos a IPs privadas."""
    from app.security.url_validator import validar_url_segura
    
    assert validar_url_segura("http://192.168.1.1") is False
    assert validar_url_segura("http://10.0.0.1") is False
    assert validar_url_segura("http://172.16.0.1") is False
    assert validar_url_segura("http://169.254.169.254") is False  # Metadata


def test_url_validator_public():
    """Verifica que se permiten URLs públicas válidas."""
    from app.security.url_validator import validar_url_segura
    
    assert validar_url_segura("https://uis.edu.co") is True
    assert validar_url_segura("https://www.uis.edu.co") is True
    assert validar_url_segura("https://portal.uis.edu.co") is True


def test_url_validator_whitelist():
    """Verifica el filtrado con whitelist."""
    from app.security.url_validator import validar_url_segura
    
    permitidos = {"uis.edu.co", "google.com"}
    
    assert validar_url_segura("https://uis.edu.co", permitidos) is True
    assert validar_url_segura("https://google.com", permitidos) is True
    assert validar_url_segura("https://evil.com", permitidos) is False


# ============================================================
# TEST NORMALIZACIÓN DE CRONOGRAMA
# ============================================================

def test_actividad_normalizada_from_ipred():
    """Verifica la normalización de actividades del endpoint IPRED."""
    from app.models.cronograma import ActividadIPRED, AsignaturaBloque, ActividadNormalizada
    
    # Crear datos similares a los del endpoint IPRED
    bloque = AsignaturaBloque(
        codigo_programa=87,
        codigo_sede=11,
        codigo_asignatura=29389,
        id_semestre=20262,
        grupo="NW7",
        nombre_profesor="Jesus Romero Arrieta",
        nombre_asignatura="PLANEACION ESTRATEGICA EN LOS AGRONEGOCIOS",
        actividades=[
            ActividadIPRED(
                fecha_inicio="2026-08-20 13:30:00",
                fecha_fin="2026-08-20 15:30:00",
                codigo_tipo_actividad=3,
                nombre_tipo_actividad="TT",
                id_actividad=2423203,
            )
        ]
    )
    
    actividad = bloque.actividades[0]
    normalizada = ActividadNormalizada.from_ipred(bloque, actividad)
    
    # Verificar normalización
    assert normalizada.semestre == "20262"
    assert normalizada.programa_codigo == "87"
    assert normalizada.grupo == "NW7"
    assert normalizada.asignatura == "Planeacion Estrategica En Los Agronegocios"
    assert normalizada.profesor == "Jesus Romero Arrieta"
    assert normalizada.tipo_actividad == "TT"
    assert normalizada.inicio == "2026-08-20T13:30:00"
    assert normalizada.fin == "2026-08-20T15:30:00"


# ============================================================
# TEST NORMALIZACIÓN DE BÚSQUEDA
# ============================================================

def test_normalize_text():
    """Verifica la normalización de texto para búsquedas."""
    from app.services.info_fija_service import normalize_text
    
    assert normalize_text("TELÉFONO") == "telefono"
    assert normalize_text("  Barrancabermeja  ") == "barrancabermeja"
    assert normalize_text("¿Cuál es?") == "cual es"
    assert normalize_text("Múltiples  espacios") == "multiples espacios"


def test_extract_keywords():
    """Verifica la extracción de keywords."""
    from app.services.info_fija_service import extract_keywords
    
    keywords = extract_keywords("¿Cuál es el teléfono de Barrancabermeja?")
    
    # Los stopwords deben ser removidos
    assert "cual" not in keywords  # stopword
    assert "es" not in keywords    # stopword
    assert "de" not in keywords    # stopword
    
    # Las palabras clave deben estar presentes
    assert "telefono" in keywords
    assert "barrancabermeja" in keywords


# ============================================================
# TEST MICROCACHÉ
# ============================================================

@pytest.mark.asyncio
async def test_microcache_set_get():
    """Verifica que el microcaché guarda y recupera valores."""
    from app.cache.microcache import MicroCache
    
    cache = MicroCache(default_ttl=5.0)
    
    # Guardar
    await cache.set("test-key", "test-value")
    
    # Recuperar
    result = await cache.get("test-key")
    assert result == "test-value"
    
    # Verificar que existe en el caché
    result2 = await cache.get("test-key")
    assert result2 == "test-value"


@pytest.mark.asyncio
async def test_microcache_get_or_fetch():
    """Verifica la coalescencia de requests en vuelo."""
    from app.cache.microcache import MicroCache
    import asyncio
    
    cache = MicroCache(default_ttl=5.0)
    call_count = 0
    
    async def expensive_fetch():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return f"result-{call_count}"
    
    # Dos llamadas simultáneas con la misma clave
    results = await asyncio.gather(
        cache.get_or_fetch("shared-key", expensive_fetch),
        cache.get_or_fetch("shared-key", expensive_fetch),
    )
    
    # Debe haber solo UNA llamada a fetch (deduplicación)
    assert call_count == 1
    assert results[0] == results[1]


# ============================================================
# TEST MODELOS PYDANTIC
# ============================================================

def test_chat_request_message_variants():
    """Verifica que ChatRequest acepta 'message' y 'mensaje'."""
    from app.models.user import ChatRequest
    
    # Variante con 'message'
    req1 = ChatRequest(message="¿Hola?")
    assert req1.get_message_text() == "¿Hola?"
    
    # Variante con 'mensaje'
    req2 = ChatRequest(mensaje="¿Hola?")
    assert req2.get_message_text() == "¿Hola?"


def test_perfil_update_model():
    """Verifica el modelo de actualización de perfil."""
    from app.models.user import PerfilUpdate
    
    perfil = PerfilUpdate(
        sede_codigo="11",
        programa_codigo="87",
        grupo="NW7",
    )
    
    assert perfil.sede_codigo == "11"
    assert perfil.programa_codigo == "87"
    assert perfil.grupo == "NW7"
    assert perfil.asignaturas_interes is None


# ============================================================
# FIXTURES (para tests más complejos)
# ============================================================

@pytest.fixture
def mock_db():
    """Mock de base de datos para tests."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_http_client():
    """Mock de cliente HTTP para tests."""
    mock = AsyncMock()
    return mock


if __name__ == "__main__":
    # Ejecutar tests: pytest tests/test_basics.py -v
    pytest.main([__file__, "-v"])
