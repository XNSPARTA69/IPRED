# ==============================================================================
# IPRED Chatbot UIS - Backend Dockerfile (FastAPI / Python 3.12 Slim)
# Optimizado para producción, multi-stage y usuario no privilegiado
# ==============================================================================

FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Imagen final de producción
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH \
    TZ=America/Bogota

# Instalar libpq para conexiones PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copiar paquetes instalados desde builder
COPY --from=builder /root/.local /root/.local

# Copiar código fuente
COPY . /app

# Crear directorio de datos para persistencia
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
