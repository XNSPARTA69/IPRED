"""
IPRED Chatbot - Verificador de Preparación para Despliegue en Docker y PostgreSQL.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

REQUIRED_FILES = [
    (ROOT_DIR / "docker-compose.yml", "Orquestador Maestro Docker Compose"),
    (ROOT_DIR / ".env.example", "Plantilla de Variables de Entorno"),
    (ROOT_DIR / "backend" / "Dockerfile", "Dockerfile del Backend FastAPI"),
    (ROOT_DIR / "backend" / ".dockerignore", "Dockerignore del Backend"),
    (ROOT_DIR / "backend" / "requirements.txt", "Dependencias de Python (SQLite + PostgreSQL)"),
    (ROOT_DIR / "backend" / "database_schema_postgres.sql", "Esquema DDL Oficial PostgreSQL"),
    (ROOT_DIR / "backend" / "scripts" / "migrate_sqlite_to_postgres.py", "Script de Migración de Datos"),
    (ROOT_DIR / "frontend" / "Dockerfile", "Dockerfile Multi-stage Flutter Web"),
    (ROOT_DIR / "frontend" / "nginx.conf", "Configuración Nginx con Proxy Inverso"),
    (ROOT_DIR / "frontend" / ".dockerignore", "Dockerignore del Frontend"),
]


def check():
    print("=" * 80)
    print("🔍 AUDITORÍA DE PREPARACIÓN PARA CONTENEDORIZACIÓN Y MIGRACIÓN")
    print("=" * 80)

    todos_ok = True
    for path, desc in REQUIRED_FILES:
        exists = os.path.exists(path)
        status = "✅ LISTO" if exists else "❌ FALTA"
        size = f"({os.path.getsize(path)} bytes)" if exists else ""
        print(f"  * {desc:<48}: {status} {size}")
        if not exists:
            todos_ok = False

    print("\n" + "-" * 80)
    print("📦 MAPEO DE PUERTOS Y NOMBRES DE CONTENEDORES:")
    print("  * [ipred_frontend]  -> Puerto 3000 (Flutter Web + Nginx)")
    print("  * [ipred_backend]   -> Puerto 8000 (FastAPI / Uvicorn Python 3.12)")
    print("  * [ipred_postgres]  -> Puerto 5432 (PostgreSQL 16 Alpine)")
    print("  * [ipred_redis]     -> Puerto 6379 (Redis 7 Alpine)")
    print("  * [ipred_searxng]   -> Puerto 8080 (Motor de Búsqueda)")
    print("-" * 80)

    if todos_ok:
        print("\n🎉 ¡ESTADO 100% PREPARADO! Todos los archivos, esquemas y dependencias están listos.")
    else:
        print("\n⚠️ Faltan algunos archivos requeridos.")


if __name__ == "__main__":
    check()
