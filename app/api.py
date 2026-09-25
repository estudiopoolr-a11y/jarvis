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


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Endpoint webhook para recibir mensajes de Telegram y responder con Gemini/NLP."""
    try:
        update = await request.json()
        message = update.get("message") or update.get("edited_message")
        if not message:
            return {"status": "ok"}

        texto = message.get("text")
        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if not texto or not chat_id:
            return {"status": "ok"}

        # Procesar con intención determinística o fallback a Gemini
        from modules.ai import procesar_intencion_natural, pensar_respuesta

        respuesta = procesar_intencion_natural(texto, str(chat_id), es_audio=False)
        if not respuesta:
            respuesta = pensar_respuesta(texto)

        # Enviar respuesta al usuario mediante la API de Telegram
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_token:
            logger.error("TELEGRAM_BOT_TOKEN no configurado en variables de entorno.")
            return {"status": "ok"}

        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": respuesta}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            if resp.status_code != 200:
                logger.error(f"Telegram API error {resp.status_code}: {resp.text}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error procesando webhook de Telegram: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
