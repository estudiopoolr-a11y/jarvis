import os
import logging
import requests
from fastapi import APIRouter, Request
from app.core.organisms.finance_organism import OrganismoFinanzas
from app.core.templates.telegram_templates import plantilla_comando_balance
from modules.ai import analizar_intencion_mensaje
from modules.intent_handler import ejecutar_intencion_nlp

router = APIRouter(prefix="/api/telegram", tags=["telegram"])
logger = logging.getLogger("jarvis.telegram")


def despachar_respuesta_telegram(chat_id: int, texto: str) -> bool:
    """Envía la respuesta atómica a Telegram API. Devuelve True si fue 200 OK."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN no configurado en entorno")
        return False

    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}

    try:
        res = requests.post(endpoint, json=payload, timeout=8)
        logger.info(f"📡 Respuesta de Telegram API ({res.status_code}): {res.text}")
        return res.status_code == 200
    except Exception as e:
        logger.error(f"❌ Excepción en despachar_respuesta_telegram: {e}")
        return False


@router.get("/set-webhook")
async def set_webhook():
    """Registra el Webhook en la API de Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return {"error": "TELEGRAM_BOT_TOKEN no configurado"}

    base_url = os.getenv("VERCEL_URL", "https://jarvis-two-pi-13.vercel.app")
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    
    webhook_url = f"{base_url}/api/telegram/webhook"
    endpoint = f"https://api.telegram.org/bot{token}/setWebhook"
    payload = {"url": webhook_url}
    
    try:
        resp = requests.post(endpoint, json=payload, timeout=10)
        return resp.json()
    except Exception as e:
        logger.error(f"❌ Error al registrar webhook: {e}")
        return {"error": str(e)}


@router.post("/webhook")
async def atender_telegram_webhook(request: Request):
    """Recibe y procesa los eventos desde Telegram usando arquitectura atómica."""
    try:
        cuerpo = await request.json()
        logger.info(f"📥 Payload recibido en Webhook: {cuerpo}")

        # Extracción ultradefensiva con .get() multinivel para evitar KeyError
        mensaje = cuerpo.get("message") or cuerpo.get("edited_message") or {}
        chat = mensaje.get("chat", {})
        chat_id = chat.get("id")
        mensaje_texto = (mensaje.get("text") or "").strip()

        if chat_id and mensaje_texto:
            if mensaje_texto == "/start":
                respuesta = plantilla_comando_balance()
            else:
                intent_data = await analizar_intencion_mensaje(mensaje_texto)
                respuesta = await ejecutar_intencion_nlp(intent_data)

            despachar_respuesta_telegram(chat_id, respuesta)

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"💥 Error crítico procesando Webhook: {e}")
        return {"status": "error_handled"}