@echo off
title IPRED Chatbot - Iniciar Sistema Completo
cd /d "%~dp0"

echo ========================================================
echo    INICIANDO SERVICIOS DE IPRED CHATBOT UIS (DOCKER)
echo ========================================================
echo.

:: 1. Verificar si Docker esta corriendo
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Iniciando Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo [*] Esperando a que el motor de Docker responda...
    :wait_docker
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if %errorlevel% neq 0 goto wait_docker
)

echo [*] Levantando todos los contenedores (PostgreSQL, Backend, Frontend, SearXNG, Cloudflare)...
docker compose up -d

echo.
echo ========================================================
echo    ¡TODOS LOS SERVICIOS ESTAN ACTIVOS Y CORRIENDO!
echo ========================================================
echo  - Frontend Web / Movil : http://localhost:3000
echo  - Backend API FastAPI   : http://localhost:8000
echo  - PostgreSQL 16 DB      : localhost:5432
echo ========================================================
echo.
timeout /t 5
