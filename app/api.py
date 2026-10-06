"""FastAPI application instance con ciclo de vida asíncrono para Bot de Discord y Telegram Webhook."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel

# Configurar logging centralizado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("JARVIS")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de FastAPI.

    En entorno serverless (Vercel) NO se puede mantener un proceso de Discord
    persistente, por lo que el arranque del bot es opcional y está blindado: si
    el paquete ``bot`` no existe, el lifespan arranca igual para no tumbar la
    función con FUNCTION_INVOCATION_FAILED.
    """
    logger.info("🚀 Iniciando JARVIS Web Service...")

    discord_task = None
    bot = None
    try:
        from bot import TOKEN, bot, register_handlers

        if TOKEN:
            register_handlers()
            logger.info("🤖 TOKEN detectado. Creando tarea de Discord en el event loop...")
            discord_task = asyncio.create_task(bot.start(TOKEN))
        else:
            logger.warning("⚠️ DISCORD_TOKEN no configurado. El bot de Discord no se iniciará.")
    except Exception as exc:
        # El bot de Discord es opcional en serverless; su ausencia no debe romper el arranque.
        logger.warning("ℹ️ Bot de Discord no disponible (%s). Continuando sin él.", exc)

    yield

    logger.info("🛑 Apagando JARVIS Web Service...")
    if discord_task and not discord_task.done() and bot is not None:
        logger.info("🛑 Cerrando sesión del bot de Discord...")
        try:
            await bot.close()
        except Exception:
            pass
        discord_task.cancel()
        try:
            await discord_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="JARVIS Control Center", lifespan=lifespan)
USUARIO_PRINCIPAL = "1536228767180136498"


@app.get("/")
@app.head("/")
@app.get("/health")
@app.head("/health")
def health_check():
    """Endpoint de comprobación de estado para Keep-Alive y UptimeRobot."""
    try:
        from bot import bot
        bot_online = bot.is_ready() if (bot and hasattr(bot, "is_ready")) else False
    except Exception:
        bot_online = False

    return {
        "status": "ok",
        "bot": "online" if bot_online else "connecting",
        "timestamp": datetime.now().isoformat()
    }


class ComandoPayload(BaseModel):
    texto: str
    usuario_id: str = USUARIO_PRINCIPAL
