import os  # Cargar módulo OS para acceder a variables del entorno #
import logging  # Cargar módulo logging para trazas estructuradas #
import inspect  # Cargar módulo inspect para validación de funciones asíncronas #
import httpx  # Cargar cliente HTTP asíncrono optimizado para serverless #
from fastapi import APIRouter, Request  # Cargar clases principales de FastAPI #
from app.core.templates.telegram_templates import plantilla_comando_balance  # Cargar plantilla atómica de inicio #
from modules.ai import analizar_intencion_mensaje  # Importar analizador NLP/Regex asíncrono #
from modules.intent_handler import ejecutar_intencion_nlp  # Importar enrutador de intenciones asíncrono #

router = APIRouter(prefix="/api/telegram")  # Instanciar enrutador de FastAPI con prefijo #
logger = logging.getLogger("jarvis.telegram")  # Crear logger exclusivo para Telegram #


async def resolver_llamada_segura(func, *args, **kwargs):  # Helper universal para ejecutar funciones sync o async sin errores de await #
    """Ejecuta una función de forma segura, inspeccionando si es corrutina o síncrona."""
    if inspect.iscoroutinefunction(func):  # Evaluar si la función fue declarada con async def #
        res = await func(*args, **kwargs)  # Invocación asíncrona segura con await #
    else:  # Si la función es síncrona estándar #
        res = func(*args, **kwargs)  # Invocación síncrona directa #

    if inspect.isawaitable(res):  # Evaluar si el valor devuelto es un objeto corrutina o awaitable #
        res = await res  # Resolver corrutina de manera defensiva #

    return res  # Retornar el valor final procesado #


async def despachar_respuesta_telegram(chat_id: int, texto: str) -> bool:  # Función asíncrona de envío directo #
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Obtener token del bot desde el entorno #
    if not token:  # Validar presencia del token #
        print("💥 [VERCEL CRITICAL] TELEGRAM_BOT_TOKEN NO EXISTE EN VARIABLES DE ENTORNO DE VERCEL", flush=True)  # Log explícito visible en Vercel #
        logger.error("❌ TELEGRAM_BOT_TOKEN ausente")  # Registrar en logger del sistema #
        return False  # Retornar Falso por falta de token #

    # Guarda defensiva: Evitar enviar texto vacío que causa error 400 en Telegram API #
    if not texto or str(texto).strip() == "":  # Validar si el texto está vacío #
        texto = "🤖 JARVIS procesó tu consulta, pero no se generó un texto de respuesta válido."  # Mensaje de respaldo #

    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"  # Construir URL oficial de Telegram API #

    # Intento 1: Formato Markdown enriquecido #
    payload_markdown = {"chat_id": chat_id, "text": str(texto), "parse_mode": "Markdown"}  # Construir payload Markdown #

    async with httpx.AsyncClient(timeout=8.0) as client:  # Instanciar cliente HTTP asíncrono con tiempo límite #
        try:  # Iniciar bloque defensivo para el Intento 1 #
            res = await client.post(endpoint, json=payload_markdown)  # Enviar petición asíncrona POST #
            print(f"📡 [VERCEL OUTBOUND] Intento 1 Markdown Status: {res.status_code}", flush=True)  # Log con flush=True #
            if res.status_code == 200:  # Si Telegram aceptó el formato Markdown #
                return True  # Confirmar entrega exitosa #
        except Exception as e:  # Capturar excepción de red en el primer intento #
            print(f"⚠️ [VERCEL OUTBOUND] Excepción en Intento 1: {e}", flush=True)  # Registrar error explícito en Vercel #

        # Intento 2: Fallback defensivo en Texto Plano #
        payload_plano = {"chat_id": chat_id, "text": str(texto)}  # Construir payload simple sin parse_mode #
        try:  # Iniciar bloque defensivo para el Intento 2 #
            res_plano = await client.post(endpoint, json=payload_plano)  # Enviar petición asíncrona en texto plano #
            print(f"📡 [VERCEL OUTBOUND] Intento 2 Texto Plano Status: {res_plano.status_code}", flush=True)  # Log con flush=True #
            return res_plano.status_code == 200  # Retornar Verdadero si la entrega en texto plano fue exitosa #
        except Exception as e:  # Capturar excepción en el segundo intento #
            print(f"💥 [VERCEL OUTBOUND] Excepción en Intento 2: {e}", flush=True)  # Registrar error crítico en Vercel #
            return False  # Retornar Falso en caso de fallo total #


@router.post("/webhook")  # Declarar el endpoint POST del webhook #
async def atender_telegram_webhook(request: Request):  # Controlador asíncrono del webhook #
    chat_id = None  # Inicializar ID de chat para captura defensiva #
    try:  # Iniciar bloque defensivo principal #
        cuerpo = await request.json()  # Parsear el cuerpo de la petición JSON #
        print(f"📥 [VERCEL INBOUND] Webhook recibido: {cuerpo}", flush=True)  # Log forzado del payload #

        mensaje = cuerpo.get("message") or cuerpo.get("edited_message") or {}  # Extraer objeto de mensaje con .get() multinivel #
        chat = mensaje.get("chat", {})  # Extraer objeto chat #
        chat_id = chat.get("id")  # Extraer ID único del chat #
        mensaje_texto = mensaje.get("text", "").strip()  # Extraer y limpiar texto del mensaje #

        if chat_id and mensaje_texto:  # Validar presencia de ID de chat y texto #
            print(f"🔍 [VERCEL PROCESSING] Chat ID: {chat_id} - Texto: '{mensaje_texto}'", flush=True)  # Log de procesamiento #

            # Ejecución segura con wrapper universal (evita TypeError: object dict can't be used in 'await') #
            intent_data = await resolver_llamada_segura(analizar_intencion_mensaje, mensaje_texto)  # Analizar intención de forma segura //
            respuesta = await resolver_llamada_segura(ejecutar_intencion_nlp, intent_data)  # Ejecutar intención de forma segura //

            # Garantizar que la respuesta sea siempre una cadena de texto //
            if isinstance(respuesta, dict):  # Si la respuesta devuelta es un diccionario #
                respuesta = respuesta.get("text") or respuesta.get("message") or str(respuesta)  # Extraer el texto interno //
            elif not isinstance(respuesta, str):  # Si la respuesta no es cadena de texto //
                respuesta = str(respuesta)  # Convertir a cadena string //

            await despachar_respuesta_telegram(chat_id, respuesta)  # Despachar respuesta de forma asíncrona #
        else:  # Si el payload no contenía un mensaje de texto válido #
            print("⚠️ [VERCEL PROCESSING] Payload sin chat_id o texto válido", flush=True)  # Notificar payload no procesable #

        return {"status": "ok"}  # Confirmar siempre 200 OK a Telegram para validar recepción #
    except Exception as e:  # Capturar cualquier fallo inesperado #
        error_msg = f"💥 [VERCEL ERROR] Fallo crítico en webhook: {e}"  # Formatear traza de error #
        print(error_msg, flush=True)  # Imprimir error en Vercel Logs //
        # Notificar el error en Telegram para evitar silencio absoluto del bot //
        if chat_id:  # Si logramos identificar el chat_id antes de la falla //
            await despachar_respuesta_telegram(chat_id, f"⚠️ Ocurrió un error interno en el bot: {str(e)[:120]}")  # Notificar error en Telegram #
        return {"status": "error_handled"}  # Retornar confirmación controlada #


@router.get("/set-webhook")  # Declarar el endpoint GET del helper #
async def set_webhook():  # Controlador asíncrono del webhook #
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Obtener token del bot desde el entorno #
    if not token:  # Validar existencia del token #
        print("💥 [VERCEL CRITICAL] TELEGRAM_BOT_TOKEN NO EXISTE EN VARIABLES DE ENTORNO DE VERCEL", flush=True)  # Log crítico #
        return {"error": "TELEGRAM_BOT_TOKEN no configurado"}  # Retornar error #

    base_url = os.getenv("VERCEL_URL", "https://jarvis-two-pi-13.vercel.app")  # Obtener URL base de Vercel #
    if not base_url.startswith("http"):  # Validar prefijo HTTP #
        base_url = f"https://{base_url}"  # Agregar prefijo HTTPS si es necesario #

    webhook_url = f"{base_url}/api/telegram/webhook"  # Construir URL del webhook #
    endpoint = f"https://api.telegram.org/bot{token}/setWebhook"  # Construir endpoint de Telegram API #
    payload = {"url": webhook_url}  # Construir payload de configuración #

    print(f"📡 [VERCEL OUTBOUND] SetWebhook: {webhook_url}", flush=True)  # Log explícito de configuración #

    async with httpx.AsyncClient(timeout=10.0) as client:  # Instanciar cliente HTTP asíncrono #
        try:  # Iniciar bloque defensivo #
            resp = await client.post(endpoint, json=payload)  # Enviar petición asíncrona POST #
            print(f"📡 [VERCEL OUTBOUND] SetWebhook Status: {resp.status_code}", flush=True)  # Log en Vercel #
            return resp.json()  # Retornar respuesta JSON #
        except Exception:  # Capturar excepción #
            print(f"💥 [VERCEL OUTBOUND] Excepción en SetWebhook", flush=True)  # Registrar error crítico #
            return {"error": str(e)}  # Retornar error como diccionario #


@router.get("/health")  # Declarar el endpoint GET de diagnóstico de salud #
async def verificar_salud_telegram():  # Controlador asíncrono para validar variables de entorno #
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Extraer el token de Telegram del entorno #
    gemini_key = os.getenv("GEMINI_API_KEY")  # Extraer la clave de Gemini del entorno #

    estado_token = bool(token and len(token) > 10)  # Validar si el token existe y tiene longitud mínima #
    estado_gemini = bool(gemini_key and len(gemini_key) > 10)  # Validar si la clave de Gemini existe #

    detalles_bot = None  # Inicializar variable para guardar información del bot #
    if estado_token:  # Si la variable del token está presente en el servidor #
        try:  # Iniciar bloque seguro de verificación HTTP #
            async with httpx.AsyncClient(timeout=5.0) as client:  # Instanciar cliente HTTP asíncrono #
                resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")  # Consultar getMe a Telegram #
                detalles_bot = resp.json() if resp.status_code == 200 else f"Error HTTP {resp.status_code}"  # Guardar respuesta #
        except Exception as e:  # Capturar excepciones de conectividad de red #
            detalles_bot = f"Excepción de red: {str(e)}"  # Guardar mensaje de error #

    return {  # Retornar estructura JSON con el diagnóstico del servidor #
        "status": "ok" if estado_token else "token_missing",  # Estado general del diagnóstico #
        "telegram_bot_token_present": estado_token,  # Confirmación booleana de presencia de token #
        "gemini_api_key_present": estado_gemini,  # Confirmación booleana de presencia de clave Gemini #
        "telegram_api_response": detalles_bot  # Resultado de la consulta getMe con Telegram API #
    }  # Cierre de diccionario de respuesta de salud #