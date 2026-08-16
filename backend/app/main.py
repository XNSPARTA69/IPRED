"""
IPRED Chatbot - Main FastAPI application.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.db.database import init_db, close_db
from app.routers import auth, chat, profile
from app.security.rate_limit import setup_rate_limiting

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


import asyncio
from app.services.uis_sync_service import uis_sync_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI app."""
    # Startup
    logger.info("Starting up IPRED Chatbot...")
    await init_db()
    
    # Iniciar cron de sincronización periódica en segundo plano
    sync_task = asyncio.create_task(uis_sync_service.start_periodic_sync())
    yield
    # Shutdown
    logger.info("Shutting down IPRED Chatbot...")
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    debug=settings.app_debug
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_rate_limiting(app)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(profile.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version}


@app.get("/sync/status")
async def get_sync_status():
    """Consulta el estado del último proceso de sincronización con la UIS."""
    status = await uis_sync_service.get_latest_sync_status()
    status["en_proceso"] = uis_sync_service.is_syncing
    return status


@app.post("/sync/trigger")
async def trigger_manual_sync():
    """Dispara manualmente una sincronización global en segundo plano."""
    if uis_sync_service.is_syncing:
        return {"status": "ALREADY_RUNNING", "mensaje": "Ya existe una sincronización en progreso."}
    
    asyncio.create_task(uis_sync_service.execute_full_sync(is_manual=True))
    return {"status": "STARTED", "mensaje": "Sincronización global con la UIS iniciada en segundo plano."}
