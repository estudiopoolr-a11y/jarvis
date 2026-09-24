"""FastAPI application instance con ciclo de vida asíncrono para Bot de Discord."""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel

# Configurar logging centralizado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("JARVIS")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de FastAPI y arranca el Bot de Discord en paralelo."""
    logger.info("🚀 Iniciando JARVIS Web Service...")
    from bot import TOKEN, bot, register_handlers

    discord_task = None
    if TOKEN:
        register_handlers()
        logger.info("🤖 TOKEN detectado. Creando tarea de Discord en el event loop...")
        discord_task = asyncio.create_task(bot.start(TOKEN))
    else:
        logger.warning("⚠️ DISCORD_TOKEN no configurado. El bot de Discord no se iniciará.")

    yield

    logger.info("🛑 Apagando JARVIS Web Service...")
    if discord_task and not discord_task.done():
        logger.info("🛑 Cerrando sesión del bot de Discord...")
        await bot.close()
        discord_task.cancel()
        try:
            await discord_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="JARVIS Control Center", lifespan=lifespan)
USUARIO_PRINCIPAL = "1536228767180136498"


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
