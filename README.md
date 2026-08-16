# 🎓 IPRED Chatbot UIS — Asistente Académico Inteligente

<div align="center">

![Flutter](https://img.shields.io/badge/Flutter-3.24-02569B?style=for-the-badge&logo=flutter&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_Alpine-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose_Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Cloudflare](https://img.shields.io/badge/Cloudflare-Tunnels_QUIC-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Google_Gemini-Flash_Lite-8E75B2?style=for-the-badge&logo=google&logoColor=white)

<p align="center">
  <strong>Sistema Oficial de Asistencia Académica y Horarios para el Instituto de Proyección Regional y Educación a Distancia (IPRED) — Universidad Industrial de Santander (UIS)</strong>
</p>

[🚀 Inicio Rápido](#-inicio-rápido-con-docker) •
[🏛️ Arquitectura](#-arquitectura-del-sistema) •
[⚡ Motor Zero-AI](#-motor-zero-ai-y-rendimiento) •
[📱 App Móvil & Web](#-app-móvil-y-web) •
[🛠️ Desarrollo Local](#-desarrollo-local) •
[🔐 Seguridad](#-seguridad-y-privacidad)

</div>

---

## 🌟 Características Principales

* ⚡ **Motor Determinista Zero-AI ($0.00 COP / 0 Tokens):** Resuelve consultas de horarios de clase, materias matriculadas, docentes con correos institucionales, calendario académico, trámites y reglamentos en **menos de 30 milisegundos** sin consumir tokens de IA.
* 🤖 **IA Híbrida Inteligente (Google Gemini Flash-Lite):** Para preguntas abiertas complejas o no estructuradas, recurre a Gemini mediante un prompt enriquecido con el contexto oficial UIS y búsqueda web privada (*SearXNG*).
* 📅 **Gestión de Horarios y Cronogramas:** Soporte integral para más de **18,000 sesiones de clase** y **684 estudiantes** distribuidos en todas las sedes regionales del IPRED (*Bucaramanga, Barrancabermeja, El Carmen de Chucurí, Puerto Wilches, Barbosa, Málaga, Socorro, San Alberto*).
* 📱 **Frontend Flutter Ultra-Fluido (60/120 FPS):** Interfaz moderna mobile-first con renderizado optimizado por `RepaintBoundary`, memoización de Markdown, tablas nativas inteligentes y soporte de tema claro/oscuro.
* 🌐 **Despliegue Global Inmediato con Cloudflare:** Conexión segura HTTPS con protocolo QUIC/HTTP/3 y auto-arranque continuo.
* 🔒 **Seguridad Criptográfica:** Contraseñas hasheadas con **Argon2id**, autenticación **JWT**, control de accesos por roles y protección contra inyecciones SQL.

---

## 🚀 Inicio Rápido con Docker

El proyecto está 100% contenerizado. Para levantarlo en cualquier máquina (Windows, Linux, macOS) con un solo comando:

### 1. Clonar el Repositorio
```bash
git clone https://github.com/XNSPARTA69/IPRED.git
cd IPRED
```

### 2. Configurar Variables de Entorno
Copia el archivo de ejemplo:
```bash
# En Windows PowerShell / CMD:
copy .env.example .env

# En Linux / macOS:
cp .env.example .env
```

*(Opcional: Si deseas habilitar la IA de respaldo para preguntas no académicas, coloca tu `GEMINI_API_KEY` en `.env`).*

### 3. Levantar Todo el Ecosistema
```bash
docker compose up -d
```

¡Listo! En segundos tendrás disponibles los siguientes servicios:

| Servicio | URL Local | Descripción |
| :--- | :--- | :--- |
| 📱 **Frontend Web / Móvil** | [http://localhost:3000](http://localhost:3000) | Aplicación Flutter Web interactiva |
| ⚙️ **Backend API (Swagger Docs)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentación interactiva FastAPI |
| 🐘 **PostgreSQL 16** | `localhost:5432` | Base de datos (BD: `ipred_chatbot`, User: `ipred_user`) |
| 🔍 **SearXNG** | [http://localhost:8080](http://localhost:8080) | Motor de búsqueda web privado |
| 🔒 **Túnel Cloudflare** | `Ver logs con: docker logs ipred_cloudflare_tunnel` | Acceso público HTTPS global |

---

## 🏛️ Arquitectura del Sistema

```
                        ┌─────────────────────────────────────────┐
                        │   Dispositivos Móviles (Android / iOS)  │
                        │        y Navegadores Web                │
                        └────────────────────┬────────────────────┘
                                             │  (HTTPS / WSS)
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │     Cloudflare Tunnel + Nginx Proxy     │
                        └────────────────────┬────────────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
        ┌───────────────────────────┐                 ┌───────────────────────────┐
        │   Frontend Flutter Web    │                 │    Backend FastAPI App    │
        │   (Clean Architecture)    │                 │       (Python 3.12)       │
        └───────────────────────────┘                 └─────────────┬─────────────┘
                                                                    │
                     ┌──────────────────────────────────────────────┼──────────────────────────────┐
                     ▼                                              ▼                              ▼
      ┌─────────────────────────────┐                ┌─────────────────────────────┐ ┌─────────────────────────────┐
      │     Motor Zero-AI           │                │    Google Gemini AI         │ │    Motor de Búsqueda        │
      │  (Consultas Deterministas)  │                │  (Preguntas No Académicas)  │ │      SearXNG Privado        │
      └──────────────┬──────────────┘                └─────────────────────────────┘ └─────────────────────────────┘
                     │
                     ▼
      ┌─────────────────────────────┐
      │   PostgreSQL 16 Alpine      │
      │  (GIN Trigrams + Full-Text) │
      └─────────────────────────────┘
```

---

## ⚡ Motor Zero-AI y Rendimiento

El sistema prioriza la precisión académica y el costo cero mediante algoritmos de coincidencia determinista y vistas materializadas en PostgreSQL:

| Tipo de Consulta | Tokens Consumidos | Tiempo de Respuesta | Precisión de Datos |
| :--- | :---: | :---: | :---: |
| **Horario y Próxima Clase** | **0 Tokens ($0.00)** | **~18 ms** | **100% Oficial UIS** |
| **Materias Matriculadas** | **0 Tokens ($0.00)** | **~15 ms** | **100% Oficial UIS** |
| **Docente y Correo Institucional** | **0 Tokens ($0.00)** | **~14 ms** | **100% Oficial UIS** |
| **Calendario Académico y Fechas** | **0 Tokens ($0.00)** | **~16 ms** | **100% Oficial UIS** |
| **Trámites, Grados y Reglamentos** | **0 Tokens ($0.00)** | **~15 ms** | **100% Oficial UIS** |
| **Sedes Regionales y Contactos** | **0 Tokens ($0.00)** | **~12 ms** | **100% Oficial UIS** |
| *Pregunta Abierta General (IA Fallback)* | *~400 Tokens* | *~1.2 s* | *Enriquecida con RAG UIS* |

---

## 📱 App Móvil y Web

### 🤖 Android (APK Nativo)
El proyecto cuenta con integración nativa con Android Keystore para almacenamiento seguro de credenciales.
* Para compilar el APK de producción localmente:
  ```bash
  cd frontend
  flutter build apk --release --dart-define=API_BASE_URL=https://tu-dominio-o-ip:8000
  ```
* O utiliza el archivo de flujo automatizado en GitHub Actions [`.github/workflows/build_mobile.yml`](.github/workflows/build_mobile.yml).

### 🍎 iOS (iPhone / iPad)
* **Modo App Nativa Inmediata (PWA Standalone):** Abre la URL en Safari ➔ Toca *Compartir* ➔ *Agregar al inicio*. La app abrirá a pantalla completa con icono nativo y sin barras de navegación.
* **Compilación Nativa IPA:** El flujo de CI/CD de GitHub Actions compila automáticamente el ejecutable de iOS sobre entornos oficiales macOS.

---

## 🛠️ Desarrollo Local

Si prefieres ejecutar el frontend o backend sin Docker:

### Backend (Python 3.12)
```bash
cd backend
python -m venv venv
# Activar entorno (Windows: .\venv\Scripts\activate | Linux: source venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (Flutter)
```bash
cd frontend
flutter pub get
flutter run -d chrome # O conectar dispositivo Android/iOS
```

---

## 🔐 Seguridad y Privacidad

1. **Autenticación Fuerte:** Hashes de contraseñas procesados con **Argon2id** (estándar OWASP resistente a GPU/ASIC).
2. **Aislamiento en Contenedores:** Ningún servicio tiene acceso directo al sistema operativo anfitrión.
3. **Validación Estricta:** Todas las entradas y parámetros son validados contra esquemas estrictos de **Pydantic v2**.
4. **Cero Fugas de Datos:** Toda la información estudiantil reside en bases de datos locales cifradas.

---

## 📄 Licencia y Créditos

Desarrollado para el **Instituto de Proyección Regional y Educación a Distancia (IPRED)** de la **Universidad Industrial de Santander (UIS)**.

Distribuido bajo la Licencia MIT. Consulta el archivo `LICENSE` para más información.
