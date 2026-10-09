import os  # Cargar módulo OS para acceder a variables del sistema #
import logging  # Cargar módulo logging para trazas estructuradas #
import httpx  # Cargar cliente HTTP asíncrono optimizado para serverless #
from fastapi import APIRouter, Request  # Cargar clases principales de FastAPI #
from app.core.organisms.finance_organism import OrganismoFinanzas  # Cargar organismo atómico de finanzas #
from app.core.templates.telegram_templates import plantilla_comando_balance  # Cargar plantilla atómica de bienvenida #
from modules.ai import analizar_intencion_mensaje  # Cargar analizador NLP/Regex #
from modules.intent_handler import ejecutar_intencion_nlp  # Cargar enrutador de intenciones #

router = APIRouter()  # Instanciar enrutador de rutas FastAPI #
logger = logging.getLogger("jarvis.telegram")  # Crear logger exclusivo para Telegram #


async def despachar_respuesta_telegram(chat_id: int, texto: str) -> bool:  # Función asíncrona de envío directo #
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Obtener token del bot desde el entorno de Vercel #
    if not token:  # Validar existencia de la variable de entorno #
        print("💥 [VERCEL CRITICAL] TELEGRAM_BOT_TOKEN NO EXISTE EN VARIABLES DE ENTORNO DE VERCEL")  # Log explícito visible en Vercel #
        logger.error("❌ TELEGRAM_BOT_TOKEN ausente")  # Registrar en logger del sistema #
        return False  # Retornar Falso por falta de token #

    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"  # Construir endpoint oficial de Telegram API #

    # Intento 1: Formato Markdown enriquecido #
    payload_markdown = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}  # Construir payload Markdown #

    async with httpx.AsyncClient(timeout=10.0) as client:  # Instanciar cliente HTTP asíncrono con tiempo límite #
        try:  # Iniciar bloque defensivo para el Intento 1 #
            res = await client.post(endpoint, json=payload_markdown)  # Enviar petición asíncrona POST #
            print(f"📡 [VERCEL OUTBOUND] Intento 1 Markdown Status: {res.status_code} - Body: {res.text}")  # Log explícito en Vercel #
            if res.status_code == 200:  # Si Telegram aceptó el formato Markdown #
                return True  # Confirmar entrega exitosa #
        except Exception as e:  # Capturar excepción de red en el primer intento #
            print(f"⚠️ [VERCEL OUTBOUND] Excepción en Intento 1: {e}")  # Registrar error explícito en Vercel #

        # Intento 2: Fallback en Texto Plano si falla el Markdown #
        payload_plano = {"chat_id": chat_id, "text": texto}  # Construir payload simple sin parse_mode #
        try:  # Iniciar bloque defensivo para el Intento 2 #
            res_plano = await client.post(endpoint, json=payload_plano)  # Enviar petición asíncrona en texto plano #
            print(f"📡 [VERCEL OUTBOUND] Intento 2 Texto Plano Status: {res_plano.status_code} - Body: {res_plano.text}")  # Log en Vercel #
            return res_plano.status_code == 200  # Retornar Verdadero si la entrega en texto plano fue exitosa #
        except Exception as e:  # Capturar excepción en el segundo intento #
            print(f"💥 [VERCEL OUTBOUND] Excepción en Intento 2: {e}")  # Registrar error crítico en Vercel #
            return False  # Retornar Falso en caso de fallo total #


@router.post("/webhook")  # Declarar el endpoint POST del webhook #
async def atender_telegram_webhook(request: Request):  # Controlador asíncrono del webhook #
    try:  # Iniciar bloque defensivo principal #
        cuerpo = await request.json()  # Parsear el cuerpo de la petición JSON #
        print(f"📥 [VERCEL INBOUND] Webhook recibido: {cuerpo}")  # Log explícito del payload recibido #

        mensaje = cuerpo.get("message") or cuerpo.get("edited_message") or {}  # Extraer objeto de mensaje con .get() multinivel #
        chat = mensaje.get("chat", {})  # Extraer objeto chat de forma segura #
        chat_id = chat.get("id")  # Extraer ID único del chat #
        mensaje_texto = mensaje.get("text", "").strip()  # Extraer texto del mensaje sanitizado #

        if chat_id and mensaje_texto:  # Validar presencia de ID de chat y texto #
            print(f"🔍 [VERCEL PROCESSING] Chat ID: {chat_id} - Texto: '{mensaje_texto}'")  # Log del mensaje procesado #
            if mensaje_texto == "/start":  # Manejar comando de inicio #
                respuesta = plantilla_comando_balance()  # Generar bienvenida con plantilla atómica #
            else:  # Manejar consultas en texto plano #
                intent_data = await analizar_intencion_mensaje(mensaje_texto)  # Analizar intención por Gemini/Regex #
                respuesta = await ejecutar_intencion_nlp(intent_data)  # Generar respuesta con la capa atómica #

            await despachar_respuesta_telegram(chat_id, respuesta)  # Invocación asíncrona del despacho de respuesta #
        else:  # Si el payload no contenía un mensaje de texto válido #
            print("⚠️ [VERCEL PROCESSING] Payload sin chat_id o texto válido")  # Notificar payload no procesable #

        return {"status": "ok"}  # Confirmar siempre 200 OK a Telegram para validar recepción #
    except Exception as e:  # Capturar fallos no previstos #
        print(f"💥 [VERCEL ERROR] Fallo crítico en webhook: {e}")  # Log del error en consola Vercel #
        return {"status": "error_handled"}  # Retornar confirmación controlada #


@router.get("/set-webhook")  # Declarar el endpoint GET del helper #
async def set_webhook():  # Controlador asíncrono del webhook #
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Obtener token del bot desde el entorno #
    if not token:  # Validar existencia del token #
        print("💥 [VERCEL CRITICAL] TELEGRAM_BOT_TOKEN NO EXISTE EN VARIABLES DE ENTORNO DE VERCEL")  # Log crítico #
        return {"error": "TELEGRAM_BOT_TOKEN no configurado"}  # Retornar error #

    base_url = os.getenv("VERCEL_URL", "https://jarvis-two-pi-13.vercel.app")  # Obtener URL base de Vercel #
    if not base_url.startswith("http"):  # Validar prefijo HTTP #
        base_url = f"https://{base_url}"  # Agregar prefijo HTTPS si es necesario #

    webhook_url = f"{base_url}/api/telegram/webhook"  # Construir URL del webhook #
    endpoint = f"https://api.telegram.org/bot{token}/setWebhook"  # Construir endpoint de Telegram API #
    payload = {"url": webhook_url}  # Construir payload de configuración #

    print(f"📡 [VERCEL OUTBOUND] SetWebhook: {webhook_url}")  # Log explícito de configuración #

    async with httpx.AsyncClient(timeout=10.0) as client:  # Instanciar cliente HTTP asíncrono #
        try:  # Iniciar bloque defensivo #
            resp = await client.post(endpoint, json=payload)  # Enviar petición asíncrona POST #
            print(f"📡 [VERCEL OUTBOUND] SetWebhook Status: {resp.status_code} - Body: {resp.text}")  # Log en Vercel #
            return resp.json()  # Retornar respuesta JSON #
        except Exception as e:  # Capturar excepción #
            print(f"💥 [VERCEL OUTBOUND] Excepción en SetWebhook: {e}")  # Registrar error crítico #
            return {"error": str(e)}  # Retornar error como diccionario #