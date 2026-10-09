"""FastAPI application instance con ciclo de vida asíncrono para Bot de Discord y Telegram Webhook."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
import httpx
from fastapi import FastAPI, Request
from fastapi import APIRouter  # Cargar clase APIRouter para agregación de rutas #
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
        logger.warning("Bot de Discord no disponible (%s). Continuando sin él.", exc)

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

# Instanciar router principal unificado con comentarios atómicos #
api_router = APIRouter()  # Crear router central para consolidar todos los endpoints #

# Importación diferida/lazy de los endpoints activos en la arquitectura simplificada #
from app.routes.telegram import router as telegram_router  # Cargar router de Telegram #
from app.routes.widgets import router as widgets_router  # Cargar router de Widgets iOS #
from app.routes.prestamos import router as prestamos_router  # Cargar router de Préstamos #
from app.routes.kebo.accounts import router as kebo_accounts_router  # Cargar router de Cuentas Kebo #
from app.routes.kebo.budgets import router as kebo_budgets_router  # Cargar router de Presupuestos Kebo #
from app.routes.kebo.transactions import router as kebo_transactions_router  # Cargar router de Transacciones Kebo #

# Registro con prefijo y etiquetas de cada submodulo activo en el router principal #
api_router.include_router(telegram_router)  # Registrar Webhook de Telegram #
api_router.include_router(widgets_router)  # Registrar Endpoint de Widgets #
api_router.include_router(prestamos_router, prefix="/v1/prestamos", tags=["Préstamos"])  # Registrar Módulo de Préstamos #
api_router.include_router(kebo_accounts_router, prefix="/kebo/accounts", tags=["Kebo Cuentas"])  # Registrar Cuentas #
api_router.include_router(kebo_budgets_router, prefix="/kebo/presupuestos", tags=["Kebo Presupuestos"])  # Registrar Presupuestos #
api_router.include_router(kebo_transactions_router, prefix="/kebo/transacciones", tags=["Kebo Transacciones"])  # Registrar Transacciones #

app.include_router(api_router)  # Registrar router principal en la aplicación FastAPI #


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
