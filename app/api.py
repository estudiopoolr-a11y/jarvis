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
    """
    Endpoint webhook para recibir mensajes de Telegram.

    Flujo de procesamiento (AGENTS.md §1 — Preservar parsers determinísticos):
      1. Parsers determinísticos de modules/ai.py (90 % de los mensajes, $0, <10 ms).
      2. Si ningún parser coincide → HermesAgent ReAct (Gemini / Nvidia NIM).

    Siempre responde 200 OK para evitar reintentos duplicados de Telegram.
    """
    # Respuesta vacía inmediata — nunca dejamos que Telegram reintente
    try:
        update = await request.json()
    except Exception as parse_exc:
        logger.warning("Webhook: payload JSON inválido: %s", parse_exc)
        return {"status": "ok"}

    try:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return {"status": "ok"}

        texto = message.get("text", "").strip()
        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if not texto or not chat_id:
            return {"status": "ok"}

        usuario_id = str(chat_id)

        # ----------------------------------------------------------------
        # Paso 1: Parsers determinísticos (rápidos, sin costo de tokens)
        # ----------------------------------------------------------------
        from modules.ai import procesar_intencion_natural

        respuesta: str | None = procesar_intencion_natural(
            texto, usuario_id, es_audio=False
        )

        # ----------------------------------------------------------------
        # Paso 2: Fallback agéntico — HermesAgent ReAct
        # ----------------------------------------------------------------
        if not respuesta:
            try:
                from src.agent.hermes_engine import get_hermes_agent

                agent = get_hermes_agent()
                respuesta = await agent.process_message(texto, usuario_id)
            except Exception as agent_exc:
                logger.error(
                    "HermesAgent falló, usando fallback Gemini directo: %s",
                    agent_exc,
                    exc_info=True,
                )
                # Último recurso: Gemini sin herramientas
                try:
                    from modules.ai import pensar_respuesta
                    respuesta = pensar_respuesta(texto)
                except Exception as gemini_exc:
                    logger.error("Fallback Gemini también falló: %s", gemini_exc)
                    respuesta = (
                        "⚠️ No pude procesar tu solicitud en este momento. "
                        "Por favor, inténtalo de nuevo en unos segundos."
                    )

        if not respuesta:
            respuesta = "No entendí tu solicitud. ¿Puedes reformularla?"

        # ----------------------------------------------------------------
        # Paso 3: Enviar respuesta a Telegram
        # ----------------------------------------------------------------
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_token:
            logger.error("TELEGRAM_BOT_TOKEN no configurado en variables de entorno.")
            return {"status": "ok"}

        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        # Telegram limita mensajes a 4096 caracteres
        texto_respuesta = respuesta[:4096] if len(respuesta) > 4096 else respuesta
        payload = {
            "chat_id": chat_id,
            "text": texto_respuesta,
            "parse_mode": "Markdown",
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, timeout=15.0)
                if resp.status_code != 200:
                    logger.error(
                        "Telegram API error %s: %s", resp.status_code, resp.text
                    )
                    # Reintentar sin parse_mode en caso de error de formato Markdown
                    payload_plain = {"chat_id": chat_id, "text": texto_respuesta}
                    await client.post(url, json=payload_plain, timeout=10.0)
            except Exception as send_exc:
                logger.error("Error enviando mensaje a Telegram: %s", send_exc)

        return {"status": "ok"}

    except Exception as e:
        logger.error("Error procesando webhook de Telegram: %s", e, exc_info=True)
        # Siempre 200 OK para evitar reintentos de Telegram
        return {"status": "ok"}
