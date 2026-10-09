import os
import httpx
from fastapi import APIRouter, Request, Response

# Importar organismo atómico de finanzas para consumo desde la capa de rutas
from app.core.organisms.finance_organism import OrganismoFinanzas
# Importar plantillas estructurales de Telegram desde capa Templates
from app.core.templates.telegram_templates import plantilla_comando_balance, plantilla_respuesta_nlp
# Importar funciones de análisis de intenciones e intent handler
from modules.ai import analizar_intencion_mensaje
from modules.intent_handler import ejecutar_intencion_nlp

router = APIRouter(prefix="/api/telegram", tags=["telegram"])  # Definir router con prefijo y tag para FastAPI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")  # Obtener token de Telegram desde variables de entorno
# La URL de Vercel (la actual o la custom domain de Jarvis)
BASE_URL = os.getenv("VERCEL_URL", "")
if BASE_URL and not BASE_URL.startswith("http"):
    BASE_URL = f"https://{BASE_URL}"
# Fallback si no hay env VERCEL_URL configurada
if not BASE_URL:
    BASE_URL = "https://jarvis.vercel.app"

async def procesar_texto_libre_telegram(chat_id: str, texto_mensaje: str) -> str:
    """Procesa texto libre usando análisis de intenciones y ejecuta la respuesta."""
    try:
        intent_data = analizar_intencion_mensaje(texto_mensaje)
        intent_data["texto"] = texto_mensaje
        respuesta = await ejecutar_intencion_nlp(intent_data)
        await enviar_mensaje(chat_id, respuesta)
        return respuesta
    except Exception as e:
        print(f"[Telegram Procesar Error] {e}")
        fallback_msg = "Recibí tu mensaje. Usa /balance o /ayuda para ver los comandos disponibles."
        await enviar_mensaje(chat_id, fallback_msg)
        return fallback_msg

@router.get("/set-webhook")
async def set_webhook():
    """Registra el Webhook en la API de Telegram."""
    if not TELEGRAM_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN no configurado"}

    webhook_url = f"{BASE_URL}/api/telegram/webhook"  # Construir URL completa del webhook #
    telegram_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}"

    async with httpx.AsyncClient() as client:
        response = await client.get(telegram_api)
        return response.json()

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Recibe y procesa los eventos desde Telegram usando arquitectura atómica. Blindaje: siempre retorna HTTP 200 OK."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")  # Obtener token para validación interna #
    if not token:
        print("[Telegram Webhook] ATENCION: TELEGRAM_BOT_TOKEN no esta configurado.")
        return Response(status_code=200, content="TOKEN_NOT_CONFIGURED")

    try:
        update = await request.json()  # Parsear payload JSON del evento de Telegram #
        print(f"[Telegram Webhook] Evento recibido: {update}")

        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]  # Extraer texto del mensaje #
            chat_id = update["message"]["chat"]["id"]  # Extraer chat_id para respuesta #
            user_id = str(update["message"].get("from", {}).get("id", chat_id))  # Extraer user_id como string #

            # Manejo de comandos determinísticos rápidos antes de pasar a la IA #
            if text.startswith("/start") or text.startswith("/ayuda"):
                respuesta = plantilla_comando_balance()  # Consumir plantilla de Templates layer #
            elif text.startswith("/balance") or text.startswith("/resumen"):
                try:
                    # Consumir Organismo Atómico de Finanzas para obtener resumen estructurado #
                    organismo = OrganismoFinanzas()  # Instanciar organismo de finanzas atómico #
                    respuesta_formateada = await organismo.obtener_resumen_organismo(user_id)  # Generar respuesta estructurada #
                    respuesta = f"🏦 *Resumen Financiero*\n\n{respuesta_formateada}"  # Envelop con etiqueta #
                except Exception as e:
                    respuesta = f"❌ Error al obtener el balance: {str(e)}"  # Plantilla genérica de error #
            elif text.startswith("/gasto"):
                try:
                    from modules.ai import procesar_intencion_natural
                    # Enviamos el texto tal cual para que el NLP procese la intención de registro
                    respuesta = procesar_intencion_natural(text, user_id)
                except Exception as e:
                    respuesta = f"❌ Error al registrar el gasto: {str(e)}"
            else:
                # NUEVO FLUJO: Análisis de intención con Regex/Gemini NLP
                try:
                    await procesar_texto_libre_telegram(chat_id, text)
                except Exception as nlp_err:
                    # Fallback al comportamiento anterior si falla el NLP
                    print(f"[Telegram Webhook NLP Error] {nlp_err}")
                    respuesta = "Recibí tu mensaje. Usa /balance o /ayuda para ver los comandos disponibles."
                    await enviar_mensaje(chat_id, respuesta)

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
