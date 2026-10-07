import os
import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# La URL de Vercel (la actual o la custom domain de Jarvis)
BASE_URL = os.getenv("VERCEL_URL", "")
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
    """Recibe y procesa los eventos desde Telegram. Blindaje: siempre retorna HTTP 200 OK."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("[Telegram Webhook] ATENCION: TELEGRAM_BOT_TOKEN no esta configurado.")
        return Response(status_code=200, content="TOKEN_NOT_CONFIGURED")

    try:
        update = await request.json()
        print(f"[Telegram Webhook] Evento recibido: {update}")

        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]
            user_id = str(update["message"].get("from", {}).get("id", chat_id))

            # Manejo de comandos determinísticos rápidos antes de pasar a la IA
            if text.startswith("/start") or text.startswith("/ayuda"):
                respuesta = (
                    "🤖 *¡Hola! Soy JARVIS, tu asistente financiero inteligente.*\n\n"
                    "Aquí tienes los comandos disponibles:\n"
                    "🔹 `/balance` o `/resumen` - Consulta tu saldo actual y resumen financiero.\n"
                    "🔹 `/gasto <monto> <categoría>` - Registra un gasto rápidamente (ej: `/gasto 50 comida`).\n"
                    "🔹 `/ayuda` - Muestra este menú.\n\n"
                    "También puedes escribirme cualquier duda en lenguaje natural y usaré mi motor de IA para ayudarte."
                )
            elif text.startswith("/balance") or text.startswith("/resumen"):
                try:
                    from modules.db import obtener_balance_financiero
                    resumen = obtener_balance_financiero(user_id)
                    respuesta = f"🏦 *Resumen Financiero*\n\n{resumen}"
                except Exception as e:
                    respuesta = f"❌ Error al obtener el balance: {str(e)}"
            elif text.startswith("/gasto"):
                try:
                    from modules.ai import procesar_intencion_natural
                    # Enviamos el texto tal cual para que el NLP procese la intención de registro
                    respuesta = procesar_intencion_natural(text, user_id)
                except Exception as e:
                    respuesta = f"❌ Error al registrar el gasto: {str(e)}"
            else:
                # Enrutamos al motor de IA para texto libre
                respuesta = None
                try:
                    # Importacion perezosa: un fallo de IA no debe tumbar el arranque serverless.
                    from modules.ai import procesar_intencion_natural, pensar_respuesta

                    respuesta = procesar_intencion_natural(text, user_id)
                    if not respuesta:
                        respuesta = pensar_respuesta(text)
                except Exception as ai_err:
                    print(f"[Telegram Webhook AI Error] Fallo al procesar IA: {ai_err}")
                    respuesta = (
                        "Hola, recibi tu mensaje pero mis servicios de IA estan en mantenimiento. "
                        "Intenta nuevamente en un momento."
                    )

            if respuesta:
                await enviar_mensaje(chat_id, respuesta)

        return Response(status_code=200, content="OK")
    except Exception as e:
        print(f"[Telegram Webhook Critical Error] {e}")
        # Retornar 200 OK siempre para evitar bloqueos por parte de Telegram
        return Response(status_code=200, content="OK")

async def enviar_mensaje(chat_id: int, text: str):
    """Envia un mensaje de texto plano a Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"  # Soporte basico de Markdown
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"[Telegram Error] No se pudo responder: {e}")
