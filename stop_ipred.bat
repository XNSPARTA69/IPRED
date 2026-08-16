@echo off
title IPRED Chatbot - Detener Sistema
cd /d "%~dp0"

echo ========================================================
echo    DETENIENDO SERVICIOS DE IPRED CHATBOT UIS
echo ========================================================
echo.

docker compose down

echo.
echo [✓] Todos los servicios han sido detenidos correctamente.
echo.
timeout /t 3
