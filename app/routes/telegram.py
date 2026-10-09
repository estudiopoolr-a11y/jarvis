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


def despachar_respuesta_telegram(chat_id: int, texto: str):
    """Función para enviar mensaje a Telegram API."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN ausente en la ejecución")
        return
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    try:
        requests.post(endpoint, json=payload, timeout=8)
    except Exception as e:
        logger.error(f"❌ Error al enviar respuesta a Telegram: {e}")


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
        
        if "message" in cuerpo and "text" in cuerpo["message"]:
            chat_id = cuerpo["message"]["chat"]["id"]
            mensaje_texto = cuerpo["message"]["text"]
            user_id = str(cuerpo["message"].get("from", {}).get("id", chat_id))
            
            if mensaje_texto.strip() == "/start":
                respuesta = plantilla_comando_balance()
            else:
                intent_data = await analizar_intencion_mensaje(mensaje_texto)
                respuesta = await ejecutar_intencion_nlp(intent_data)
            
            despachar_respuesta_telegram(chat_id, respuesta)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Fallo crítico en atender_telegram_webhook: {e}")
        return {"status": "error_handled"}