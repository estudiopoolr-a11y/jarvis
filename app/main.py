import logging  # Importar módulo para registro de logs del sistema #
from fastapi import FastAPI  # Importar el framework principal FastAPI #
from app.routes.telegram import (
    router as telegram_router,
)  # Importar el enrutador exclusivo de Telegram #

app = FastAPI(
    title="JARVIS Backend", version="2.0.0"
)  # Instanciar la aplicación FastAPI principal #
logger = logging.getLogger("jarvis.main")  # Crear logger principal del sistema #

# Montar el router de Telegram UNA SOLA VEZ para evitar duplicidad de respuestas #
app.include_router(telegram_router, prefix="/api/telegram")  # Registrar el router de Telegram con prefijo /api/telegram

# Health check moved to app/routes/telegram.py as /api/telegram/health
# to avoid route duplication.