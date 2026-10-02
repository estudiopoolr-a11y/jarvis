import os
import httpx
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from modules.ai import procesar_intencion_natural, pensar_respuesta

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# La URL de Vercel (la actual o la custom domain de Jarvis)
BASE_URL = os.getenv("VERCEL_URL") 
if BASE_URL and not BASE_URL.startswith("http"):
    BASE_URL = f"https://{BASE_URL}"
# Fallback si no hay env VERCEL_URL configurada:
if not BASE_URL:
    BASE_URL = "https://jarvis.vercel.app"

@router.get("/set-webhook")
async def set_webhook():
    """Registra el Webhook en la API de Telegram."""
    if not TELEGRAM_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN no configurado"}
        
    webhook_url = f"{BASE_URL}/api/telegram/webhook"
    telegram_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(telegram_api)
        return response.json()

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Recibe y procesa los eventos desde Telegram."""
    try:
        update = await request.json()
        print(f"[Telegram Webhook] Evento recibido: {update}")
        
        # Procesamiento ultra-básico (se puede mejorar/conectar con python-telegram-bot más adelante)
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]
            user_id = str(update["message"]["from"]["id"])
            
            # TODO: Conectar con la lógica central de Jarvis (Hermes Agent / AI module)
            respuesta = procesar_intencion_natural(text, user_id)
            if not respuesta:
                respuesta = pensar_respuesta(text)
                
            if respuesta:
                await enviar_mensaje(chat_id, respuesta)
                
        return Response(status_code=200) # Telegram exige un 200 OK rápido
    except Exception as e:
        print(f"[Telegram Webhook] Error interno: {e}")
        return Response(status_code=200) # Siempre responder 200 para que TX ignore fallos temporales

async def enviar_mensaje(chat_id: int, text: str):
    """Envía un mensaje de texto plano a Telegram."""
    if not TELEGRAM_TOKEN:
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown" # Soporte básico de Markdown
    }
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"[Telegram Error] No se pudo responder: {e}")
