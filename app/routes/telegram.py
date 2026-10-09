import os  # Cargar módulo OS para acceder a variables del sistema #
import logging  # Cargar módulo logging para trazas estructuradas #
import asyncio  # Cargar módulo asyncio para inspección de corrutinas #
import inspect  # Cargar módulo inspect para validación de funciones asíncronas #
import httpx  # Cargar cliente HTTP asíncrono optimizado para serverless #
from fastapi import APIRouter, Request  # Importar clases principales de FastAPI #
from app.core.templates.telegram_templates import plantilla_comando_balance  # Importar plantilla atómica de inicio #
from modules.ai import analizar_intencion_mensaje  # Importar extractor NLP/Regex #
from modules.intent_handler import ejecutar_intencion_nlp  # Importar enrutador de intenciones #

router = APIRouter(prefix="/api/telegram")  # Instanciar enrutador de FastAPI con prefijo #
logger = logging.getLogger("jarvis.telegram")  # Crear logger exclusivo para Telegram #


async def despachar_respuesta_telegram(chat_id: int, texto: str) -> bool:  # Función asíncrona de envío a Telegram API #
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Obtener token de Telegram desde el entorno #
    if not token:  # Validar presencia del token #
        print("💥 [VERCEL CRITICAL] TELEGRAM_BOT_TOKEN no encontrado")  # Log de error en Vercel //
        logger.error("❌ TELEGRAM_BOT_TOKEN ausente")  # Registrar en logger del sistema #
        return False  # Retornar Falso por falta de credencial #

    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"  # Construir URL oficial de Telegram //

    # Intento 1: Envío formateado con Markdown //
    payload_markdown = {"chat_id": chat_id, "text": str(texto), "parse_mode": "Markdown"}  # Construir payload Markdown //

    async with httpx.AsyncClient(timeout=8.0) as client:  # Crear cliente HTTP asíncrono con timeout //
        try:  # Iniciar bloque seguro para Intento 1 //
            res = await client.post(endpoint, json=payload_markdown)  # Enviar petición POST //
            print(f"📡 [VERCEL OUTBOUND] Intento 1 Markdown Status: {res.status_code}")  # Registrar estado en Vercel //
            if res.status_code == 200:  # Si la entrega con Markdown fue exitosa //
                return True  # Confirmar entrega //
        except Exception as e:  # Capturar falla de red //
            print(f"⚠️ [VERCEL OUTBOUND] Excepción en Intento 1: {e}")  # Registrar traza de error //

        # Intento 2: Fallback defensivo en Texto Plano //
        payload_plano = {"chat_id": chat_id, "text": str(texto)}  # Construir payload en texto plano //
        try:  # Iniciar bloque seguro para Intento 2 //
            res_plano = await client.post(endpoint, json=payload_plano)  # Enviar reintento sin parse_mode //
            print(f"📡 [VERCEL OUTBOUND] Intento 2 Texto Plano Status: {res_plano.status_code}")  # Log de estado //
            return res_plano.status_code == 200  # Retornar resultado del reintento //
        except Exception as e:  # Capturar falla final //
            print(f"💥 [VERCEL OUTBOUND] Excepción en Intento 2: {e}")  # Registrar error fatal //
            return False  # Retornar Falso //


@router.post("/webhook")  # Endpoint de webhook de Telegram //
async def atender_telegram_webhook(request: Request):  # Controlador asíncrono del webhook //
    try:  # Iniciar bloque defensivo global //
        cuerpo = await request.json()  # Parsear cuerpo JSON entrante //
        print(f"📥 [VERCEL INBOUND] Webhook recibido: {cuerpo}")  # Log del payload //

        mensaje = cuerpo.get("message") or cuerpo.get("edited_message") or {}  # Extracción defensiva con .get() //
        chat = mensaje.get("chat", {})  # Extraer objeto chat //
        chat_id = chat.get("id")  # Extraer ID de chat //
        mensaje_texto = mensaje.get("text", "").strip()  # Extraer y limpiar texto //

        if chat_id and mensaje_texto:  # Si contemos con chat_id y texto válido //
            print(f"🔍 [VERCEL PROCESSING] Chat ID: {chat_id} - Texto: '{mensaje_texto}'")  # Log de procesamiento //

            if mensaje_texto == "/start":  # Comando inicial //
                respuesta = plantilla_comando_balance()  # Generar bienvenida //
            else:  # Procesamiento de mensajes de texto libre //
                # Ejecución segura de análisis de intención (evita await en objetos síncronos) //
                if inspect.iscoroutinefunction(analizar_intencion_mensaje):  # Verificar si es corrutina //
                    intent_data = await analizar_intencion_mensaje(mensaje_texto)  # Await solo si es asíncrona //
                else:  # Si es función síncrona //
                    intent_data = analizar_intencion_mensaje(mensaje_texto)  # Invocación síncrona directa //

                # Ejecución segura de enrutamiento de intenciones //
                if inspect.iscoroutinefunction(ejecutar_intencion_nlp):  # Verificar si el ejecutor es corrutina //
                    respuesta = await ejecutar_intencion_nlp(intent_data)  # Await solo si es asíncrona //
                else:  # Si el ejecutor es síncrono //
                    respuesta = ejecutar_intencion_nlp(intent_data)  # Invocación síncrona directa //

            # Garantizar que la respuesta sea siempre una cadena de texto //
            if isinstance(respuesta, dict):  # Si la respuesta fue un diccionario //
                respuesta = respuesta.get("text") or respuesta.get("message") or str(respuesta)  # Extraer texto interno //
            elif not isinstance(respuesta, str):  # Si no es texto ni diccionario //
                respuesta = str(respuesta)  # Convertir a cadena string //

            await despachar_respuesta_telegram(chat_id, respuesta)  # Despachar respuesta de forma asíncrona //

        return {"status": "ok"}  # Confirmar siempre 200 OK a Telegram //
    except Exception as e:  # Capturar cualquier fallo inesperado //
        print(f"💥 [VERCEL ERROR] Fallo crítico en webhook: {e}")  # Imprimir traza explícita en Vercel //
        return {"status": "error_handled"}  # Responder con estado controlado //


@router.get("/set-webhook")  # Declarar el endpoint GET del helper //
async def set_webhook():  # Controlador asíncrono del webhook //
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Obtener token del bot desde el entorno //
    if not token:  # Validar existencia del token //
        print("💥 [VERCEL CRITICAL] TELEGRAM_BOT_TOKEN NO EXISTE EN VARIABLES DE ENTORNO DE VERCEL")  # Log crítico //
        return {"error": "TELEGRAM_BOT_TOKEN no configurado"}  # Retornar error //

    base_url = os.getenv("VERCEL_URL", "https://jarvis-two-pi-13.vercel.app")  # Obtener URL base de Vercel //
    if not base_url.startswith("http"):  # Validar prefijo HTTP //
        base_url = f"https://{base_url}"  # Agregar prefijo HTTPS si es necesario //

    webhook_url = f"{base_url}/api/telegram/webhook"  # Construir URL del webhook //
    endpoint = f"https://api.telegram.org/bot{token}/setWebhook"  # Construir endpoint de Telegram API //
    payload = {"url": webhook_url}  # Construir payload de configuración //

    print(f"📡 [VERCEL OUTBOUND] SetWebhook: {webhook_url}")  # Log explícito de configuración //

    async with httpx.AsyncClient(timeout=10.0) as client:  # Instanciar cliente HTTP asíncrono //
        try:  # Iniciar bloque defensivo //
            resp = await client.post(endpoint, json=payload)  # Enviar petición asíncrona POST //
            print(f"📡 [VERCEL OUTBOUND] SetWebhook Status: {resp.status_code} - Body: {resp.text}")  # Log en Vercel //
            return resp.json()  # Retornar respuesta JSON //
        except Exception as e:  # Capturar excepción //
            print(f"💥 [VERCEL OUTBOUND] Excepción en SetWebhook: {e}")  # Registrar error crítico //
            return {"error": str(e)}  # Retornar error como diccionario //


@router.get("/health")  # Declarar el endpoint GET de diagnóstico de salud //
async def verificar_salud_telegram():  # Controlador asíncrono para validar variables de entorno //
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Extraer el token de Telegram del entorno //
    gemini_key = os.getenv("GEMINI_API_KEY")  # Extraer la clave de Gemini del entorno //

    estado_token = bool(token and len(token) > 10)  # Validar si el token existe y tiene longitud mínima //
    estado_gemini = bool(gemini_key and len(gemini_key) > 10)  # Validar si la clave de Gemini existe //

    detalles_bot = None  # Inicializar variable para guardar información del bot //
    if estado_token:  # Si la variable del token está presente en el servidor //
        try:  # Iniciar bloque seguro de verificación HTTP //
            async with httpx.AsyncClient(timeout=5.0) as client:  # Instanciar cliente HTTP asíncrono //
                resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")  # Consultar getMe a Telegram //
                detalles_bot = resp.json() if resp.status_code == 200 else f"Error HTTP {resp.status_code}"  # Guardar respuesta //
        except Exception as e:  # Capturar excepciones de conectividad de red //
            detalles_bot = f"Excepción de red: {str(e)}"  # Guardar mensaje de error //

    return {  # Retornar estructura JSON con el diagnóstico del servidor //
        "status": "ok" if estado_token else "token_missing",  # Estado general del diagnóstico //
        "telegram_bot_token_present": estado_token,  # Confirmación booleana de presencia de token //
        "gemini_api_key_present": estado_gemini,  # Confirmación booleana de presencia de clave Gemini //
        "telegram_api_response": detalles_bot  # Resultado de la consulta getMe con Telegram API //
    }  # Cierre de diccionario de respuesta de salud //