import logging  # Importar módulo para registro de logs del sistema #
from fastapi import FastAPI  # Importar el framework principal FastAPI #
from app.routes.telegram import (
    router as telegram_router,
)  # Importar el enrutador exclusivo de Telegram #
from app.routes.widgets import router as widgets_router
from app.routes.dashboard_stats import router as dashboard_stats_router
from app.routes.dashboard import router as dashboard_router

app = FastAPI(
    title="JARVIS Backend", version="2.0.0"
)  # Instanciar la aplicación FastAPI principal #
logger = logging.getLogger("jarvis.main")  # Crear logger principal del sistema #

# Montar el router de Telegram UNA SOLA VEZ para evitar duplicidad de respuestas #
app.include_router(telegram_router, prefix="/api/telegram")  # Registrar el router de Telegram con prefijo /api/telegram
app.include_router(widgets_router)  # Registrar endpoints de datos compartidos del widget y dashboard #
app.include_router(dashboard_stats_router)  # Registrar resumen financiero para el dashboard web #
app.include_router(dashboard_router)  # Registrar las vistas web del dashboard #

# Health check moved to app/routes/telegram.py as /api/telegram/health
# to avoid route duplication.