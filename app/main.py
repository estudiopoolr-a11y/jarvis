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
app.include_router(
    telegram_router, prefix="/api/telegram"
)  # Registrar las rutas bajo el prefijo /api/telegram #

@app.get(
    "/api/telegram/health"
)  # Endpoint de verificación de estado y secretos de producción #
def health_check():  # Función de control de salud del sistema #
  import os  # Importar os para la lectura de variables de entorno #

  return {
      "status": "ok",  # Estado general operativo del servidor #
      "telegram_bot_token_present": bool(
          os.getenv("TELEGRAM_BOT_TOKEN")
      ),  # Validar presencia del token de Telegram #
      "gemini_api_key_present": bool(
          os.getenv("GEMINI_API_KEY")
      ),  # Validar presencia de la API Key de Gemini #
  }  # Cierre del diccionario de estado #