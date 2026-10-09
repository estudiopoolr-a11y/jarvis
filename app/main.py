import os
import logging
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="JARVIS API", version="1.0.0")
logger = logging.getLogger("jarvis.telegram")


@app.get("/")
@app.get("/debug")
@app.get("/api/debug")
async def debug_root():
    return {
        "status": "online",
        "environment": os.getenv("VERCEL_ENV", "development"),
        "has_telegram_token": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "has_gemini_key": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.post("/api/telegram/webhook")
async def atender_telegram_webhook(request: Request):
    """Recibe y procesa los eventos desde Telegram."""
    # Lazy imports para evitar FUNCTION_INVOCATION_FAILED
    try:
        from app.core.templates.telegram_templates import plantilla_comando_balance
        from modules.ai import analizar_intencion_mensaje
        from modules.intent_handler import ejecutar_intencion_nlp
    except ImportError as e:
        print(f"ÔÜá´©Å [VERCEL] Import error: {e}")
        return JSONResponse(status_code=200, content={"status": "ok", "degraded": True})

    try:
        cuerpo = await request.json()
        print(f"­ƒôÑ [VERCEL INBOUND] Webhook recibido: {cuerpo}")

        mensaje = cuerpo.get("message") or cuerpo.get("edited_message") or {}
        chat = mensaje.get("chat", {})
        chat_id = chat.get("id")
        mensaje_texto = mensaje.get("text", "").strip()

        if chat_id and mensaje_texto:
            print(f"­ƒöì [VERCEL PROCESSING] Chat ID: {chat_id} - Texto: '{mensaje_texto}'")
            if mensaje_texto == "/start":
                respuesta = plantilla_comando_balance()
            else:
                intent_data = await analizar_intencion_mensaje(mensaje_texto)
                respuesta = await ejecutar_intencion_nlp(intent_data)

            # Despachar respuesta
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if token:
                endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {"chat_id": chat_id, "text": respuesta}
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        res = await client.post(endpoint, json=payload)
                        print(f"­ƒôí [VERCEL OUTBOUND] Status: {res.status_code} - Body: {res.text}")
                except Exception as e:
                    print(f"­ƒÆÑ [VERCEL OUTBOUND] Error: {e}")
        else:
            print("ÔÜá´©Å [VERCEL PROCESSING] Payload sin chat_id o texto v├ílido")

        return {"status": "ok"}
    except Exception as e:
        print(f"­ƒÆÑ [VERCEL ERROR] Fallo cr├¡tico en webhook: {e}")
        return {"status": "error_handled"}


@app.get("/api/telegram/health")
async def verificar_salud_telegram():
    """Endpoint de diagn├│stico de variables de entorno."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_key = os.getenv("GEMINI_API_KEY")

    estado_token = bool(token and len(token) > 10)
    estado_gemini = bool(gemini_key and len(gemini_key) > 10)

    detalles_bot = None
    if estado_token:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                detalles_bot = resp.json() if resp.status_code == 200 else f"Error HTTP {resp.status_code}"
        except Exception as e:
            detalles_bot = f"Excepci├│n de red: {str(e)}"

    return {
        "status": "ok" if estado_token else "token_missing",
        "telegram_bot_token_present": estado_token,
        "gemini_api_key_present": estado_gemini,
        "telegram_api_response": detalles_bot
    }


@app.get("/api/telegram/set-webhook")
async def set_webhook():
    """Helper para registrar el webhook en Telegram API."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("­ƒÆÑ [VERCEL CRITICAL] TELEGRAM_BOT_TOKEN NO CONFIGURADO")
        return {"error": "TELEGRAM_BOT_TOKEN no configurado"}

    base_url = os.getenv("VERCEL_URL", "https://jarvis-two-pi-13.vercel.app")
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"

    webhook_url = f"{base_url}/api/telegram/webhook"
    endpoint = f"https://api.telegram.org/bot{token}/setWebhook"

    print(f"­ƒôí [VERCEL OUTBOUND] SetWebhook: {webhook_url}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(endpoint, json={"url": webhook_url})
            print(f"­ƒôí [VERCEL OUTBOUND] SetWebhook Status: {resp.status_code}")
            return resp.json()
    except Exception as e:
        print(f"­ƒÆÑ [VERCEL OUTBOUND] Error SetWebhook: {e}")
        return {"error": str(e)}


handler = app
