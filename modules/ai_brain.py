import os
import json
import yfinance as yf
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel
from typing import Literal, Optional
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import firestore
from modules.database import (
    guardar_tarea, registrar_transaccion, establecer_presupuesto,
    marcar_tarea_completada, inicializar_firebase, limpiar_y_cargar_datos_dinamicos,
    obtener_contexto_financiero,
    obtener_tareas_pendientes, obtener_balance_financiero, obtener_resumen_presupuestos
)

load_dotenv()

# ---------- API Key Rotation Setup ----------
# Support multiple API keys via GEMINI_API_KEYS (comma-separated) or fallback to single GEMINI_API_KEY
_api_keys_str = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
if not _api_keys_str:
    raise ValueError("No Gemini API key found. Set GEMINI_API_KEY or GEMINI_API_KEYS environment variable.")
_API_KEYS = [k.strip() for k in _api_keys_str.split(',') if k.strip()]
if not _API_KEYS:
    raise ValueError("API key list is empty after parsing.")
_key_index = 0  # index of the current key in use

def _get_current_client() -> genai.Client:
    """Return a genai.Client configured with the current API key."""
    return genai.Client(api_key=_API_KEYS[_key_index])

def _rotate_key() -> None:
    """Rotate to the next API key (round-robin)."""
    global _key_index
    _key_index = (_key_index + 1) % len(_API_KEYS)

def _gemini_call_with_fallback(callable):
    """
    Execute a callable that takes a genai.Client and makes a Gemini API request.
    On APIError 429, rotate API key and retry (up to number of keys times).
    Propagates other APIError immediately.
    Returns the callable's result.
    """
    retries = len(_API_KEYS)
    for _ in range(retries):
        try:
            return callable(_get_current_client())
        except APIError as e:
            if e.code == 429:
                # Rotate key and try again
                _rotate_key()
                continue
            # For non-429 errors, re-raise immediately
            raise
    # If we exhausted all keys due to 429
    raise Exception("All Gemini API keys exhausted due to 429 errors (quota or rate limit).")

# -------------------------------------------

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

SYSTEM_INSTRUCTION = """
Eres JARVIS, un asistente personal de inteligencia artificial de nivel ejecutivo, frío, analítico, eficiente, directo y sin filtros.
Ayudas al usuario a gestionar sus finanzas personales, presupuestos, tareas y análisis de inversiones con rigor absoluto.
"""

class ItemIntencion(BaseModel):
    tipo: Literal["tarea", "gasto", "ingreso", "presupuesto", "completar_tarea", "configuracion_masiva", "ninguno"]
    tarea: Optional[str] = None
    prioridad: Optional[str] = "Media"
    fecha_limite: Optional[str] = "Pronto"
    monto: Optional[float] = 0.0
    categoria: Optional[str] = "General"
    descripcion: Optional[str] = None
    limite: Optional[float] = 0.0
    presupuestos_dict: Optional[dict] = None
    transacciones_list: Optional[list] = None

PALABRAS_CLAVE_INTENCION = [
    "gasto", "gasté", "compré", "pagué", "compra", "ingreso", "gané", "recibí",
    "pago", "tarea", "pendiente", "recordar", "presupuesto", "límite", "completé",
    "terminé", "hecho", "debo", "cuota", "finanzas", "gastos", "historial", "desglose",
    "borra", "limpia", "reinicia", "configura", "cargar"
]

def _parse_configuracion_masiva(texto: str) -> tuple[dict, list] | None:
    """
    Parser directo para el formato de configuración masiva.
    Formato esperado:
      Presupuestos: Women: 300000, Deudas: 200000...
      Transacciones: Salario +806199.03, Gasto Women 332540...
    Retorna (presupuestos_dict, transacciones_list) o None si no coincide.
    """
    import re

    presupuestos = {}
    transacciones = []

    # Buscar sección de presupuestos
    match_pres = re.search(r'presupuestos?[:\s]+(.+?)(?=transacciones?[:\s]|$)', texto, re.IGNORECASE | re.DOTALL)
    if match_pres:
        pres_text = match_pres.group(1)
        for cat_match in re.finditer(r'(\w+)\s*:\s*([\d,.]+)', pres_text):
            cat = cat_match.group(1).strip()
            try:
                monto = float(cat_match.group(2).replace(',', ''))
                if monto > 0:
                    presupuestos[cat] = monto
            except ValueError:
                pass

    # Buscar sección de transacciones
    match_trans = re.search(r'transacciones?[:\s]+(.+?)(?=$)', texto, re.IGNORECASE | re.DOTALL)
    if match_trans:
        trans_text = match_trans.group(1)
        # Patrones: "Palabra +/-Monto" o "Tipo Palabra Monto"
        for t_match in re.finditer(r'([\w\s]+?)\s*([+-])?\s*\$?\s*([\d,.]+)', trans_text):
            desc = t_match.group(1).strip()
            try:
                monto = float(t_match.group(3).replace(',', ''))
                if monto > 0:
                    # Determinar tipo: si empieza con "gasto" es gasto, sino es ingreso
                    desc_lower = desc.lower()
                    if desc_lower.startswith('gasto'):
                        tipo = 'gasto'
                        # Extraer categoria despues de "gasto"
                        cat = desc[5:].strip() if len(desc) > 5 else 'General'
                    else:
                        tipo = 'ingreso'
                        cat = 'General'
                    transacciones.append({
                        'tipo': tipo,
                        'monto': monto,
                        'categoria': cat.title() if cat else 'General',
                        'descripcion': desc
                    })
            except ValueError:
                pass

    if presupuestos or transacciones:
        return presupuestos, transacciones
    return None


def procesar_intencion_natural(prompt_usuario: str, usuario_id: str):
    texto_lc = prompt_usuario.lower().strip()

    # Deterministic shortcuts to avoid unnecessary Gemini calls
    # Clear or reload data
    if any(k in texto_lc for k in ["borra", "limpia", "reinicia"]) and any(k in texto_lc for k in ["datos", "base", "historial"]):
        result = limpiar_y_cargar_datos_dinamicos(usuario_id, {}, [])
        return f"🤖 **[SISTEMA REINICIADO POR JARVIS]**\n{result}\n\n*He limpiado la basura anterior.*"

    # Parser directo para configuración masiva (evita llamada a Gemini)
    if "configura" in texto_lc or ("presupuestos" in texto_lc and "transacciones" in texto_lc):
        parsed = _parse_configuracion_masiva(prompt_usuario)
        if parsed:
            presupuestos, transacciones = parsed
            result = limpiar_y_cargar_datos_dinamicos(usuario_id, presupuestos, transacciones)
            return f"🤖 **[CONFIGURACIÓN MASIVA CARGADA]**\n{result}"

    if "cargar" in texto_lc and ("config" in texto_lc or "presupuestos" in texto_lc or "transacciones" in texto_lc):
        result = limpiar_y_cargar_datos_dinamicos(usuario_id, {}, [])
        return f"🤖 **[SISTEMA LIMPIADO]**\n{result}\n\n*Para cargar nueva configuración, proporciona los presupuestos y transacciones en formato estructurado.*"
    # List pending tasks
    if "tarea" in texto_lc and any(k in texto_lc for k in ["listar", "mostrar", "ver", "pendientes"]):
        tareas = obtener_tareas_pendientes(usuario_id)
        if not tareas:
            return "📋 No tienes tareas pendientes."
        lista = "\n".join([f"• [{t['prioridad']}] {t['tarea']} (Vence: {t['fecha_limite']})" for t in tareas])
        return f"📋 **Tareas pendientes:**\n{lista}"
    # Check balance/finances
    if any(k in texto_lc for k in ["balance", "finanzas", "ingresos", "gastos"]) and any(k in texto_lc for k in ["cual", "cúal", "cuanto", "cuánto", "ver", "mostrar", "consultar", "cuesta", "cuánto"]):
        balance, ingresos, gastos, _ = obtener_balance_financiero(usuario_id)
        presupuestos = obtener_resumen_presupuestos(usuario_id)
        msg = f"💰 **Balance financiero:**\n- Ingresos: +${ingresos:,.0f}\n- Gastos: -${gastos:,.0f}\n- Neto: ${balance:,.0f}\n"
        if presupuestos:
            msg += "- Presupuestos: " + ", ".join([f"{k}: ${v:,.0f}" for k, v in presupuestos.items()])
        else:
            msg += "- No hay presupuestos establecidos."
        return msg

    # If no intention keywords, return None to let pensar_respuesta handle general queries
    if not any(kw in texto_lc for kw in PALABRAS_CLAVE_INTENCION):
        return None

    prompt_extractor = (
        f"Analiza este mensaje del usuario: '{prompt_usuario}'. "
        "Si el usuario está pidiendo reiniciar, limpiar, borrar los datos viejos o cargar categorías, presupuestos y transacciones en bloque, "
        "clasifícalo como 'configuracion_masiva' y extrae un diccionario de presupuestos {'Categoria': limite} y una lista de transacciones [{'tipo': 'gasto'/'ingreso', 'monto': 0.0, 'categoria': '', 'descripcion': ''}]. "
        "Si no es masivo, identifica si es tarea, gasto, ingreso, presupuesto o completar_tarea."
    )

    try:
        data = _gemini_call_with_fallback(
            lambda c: json.loads(
                c.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt_extractor,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ItemIntencion,
                    )
                ).text
            )
        )
        tipo = data.get("tipo")

        if tipo == "configuracion_masiva":
            p_dict = data.get("presupuestos_dict") or {}
            t_list = data.get("transacciones_list") or []
            resultado = limpiar_y_cargar_datos_dinamicos(usuario_id, p_dict, t_list)
            return f"🤖 **[SISTEMA RECONFIGURADO POR JARVIS]**\n{resultado}\n\n*He limpiado la basura anterior y aplicado sus nuevos parámetros con rigor absoluto.*"

        elif tipo == "tarea" and data.get("tarea"):
            guardar_tarea(usuario_id, data.get("tarea"), data.get("prioridad", "Media"), data.get("fecha_limite", "Pronto"))
            return f"📌 Tarea registrada con prioridad **{data.get('prioridad', 'Media')}**: *{data.get('tarea')}* (Vence: {data.get('fecha_limite')})."

        elif tipo == "completar_tarea":
            texto_busqueda = data.get("tarea") or prompt_usuario
            completada = marcar_tarea_completada(usuario_id, texto_busqueda)
            if completada:
                return f"✅ Tarea marcada como completada: *'{completada}'*. Avanza con el siguiente pendiente."
            return "⚠️ No encontré ninguna tarea pendiente que coincida."

        elif tipo == "gasto" and data.get("monto", 0) > 0:
            monto = float(data.get("monto", 0))
            cat = data.get("categoria", "General").strip().title()
            desc = data.get("descripcion", "Compra")
            alerta = registrar_transaccion(usuario_id, "gasto", monto, cat, desc)
            return f"💸 Gasto registrado: **-${monto:,.0f}** en *{cat}* ({desc}).{alerta or ''}"

        elif tipo == "ingreso" and data.get("monto", 0) > 0:
            monto = float(data.get("monto", 0))
            cat = data.get("categoria", "Ingreso").strip().title()
            desc = data.get("descripcion", "Pago recibido")
            registrar_transaccion(usuario_id, "ingreso", monto, cat, desc)
            return f"💰 ¡Ingreso registrado!: **+${monto:,.0f}** en *{cat}* ({desc}). A capitalizar."

        elif tipo == "presupuesto" and data.get("limite", 0) > 0:
            cat = data.get("categoria", "General").strip().title()
            limite = float(data.get("limite", 0))
            establecer_presupuesto(usuario_id, cat, limite)
            return f"🎯 Presupuesto fijado: Máximo **${limite:,.0f}** para la categoría *{cat}*."

    except APIError as e:
        if e.code == 429:
            retry_delay_seconds = None
            try:
                # Try to extract retry delay from error details
                if hasattr(e, 'details') and e.details:
                    import json
                    if isinstance(e.details, str):
                        try:
                            details = json.loads(e.details)
                        except:
                            details = {}
                    elif isinstance(e.details, dict):
                        details = e.details
                    else:
                        details = {}

                    if isinstance(details, dict) and 'retryDelay' in details:
                        delay_str = details['retryDelay']
                        if isinstance(delay_str, str) and delay_str.endswith('s'):
                            try:
                                retry_delay_seconds = int(delay_str[:-1])
                            except ValueError:
                                pass

                # Fallback: check error message for retry delay patterns
                if retry_delay_seconds is None and hasattr(e, 'message'):
                    msg = str(e.message)
                    import re
                    # Look for patterns like "retry after 60 seconds" or "60s"
                    match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                    if match:
                        retry_delay_seconds = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)s', msg)
                        if match:
                            retry_delay_seconds = int(match.group(1))

                # Determine appropriate response based on delay
                if retry_delay_seconds is not None and retry_delay_seconds <= 300:  # 5 minutes or less
                    return f"⚠️ Límite de tasa alcanzado. Por favor, espera {retry_delay_seconds} segundos antes de intentarlo nuevamente."
                else:
                    return "⚠️ Se ha agotado la cuota diaria gratuita de la API de Gemini. La cuota se reinicia a medianoche (hora del Pacífico). Por favor, intenta nuevamente mañana."
            except Exception as parse_error:
                # If parsing fails, fall back to safe message
                print(f"Error parsing 429 details in intención natural: {parse_error}")
                return "⚠️ Se ha alcanzado el límite de la API de Gemini. Verifica tu consumo y vuelve a intentar en unos minutos."
        print(f"Error de API en intención natural: {e}")
    except Exception as e:
        print(f"Error procesando intención natural: {e}")

    return None

def pensar_respuesta(prompt_usuario: str, usuario_id: str = "default") -> str:
    """Responde preguntas generales inyectando el contexto de Firebase y Google Search."""
    try:
        contexto_db = obtener_contexto_financiero(usuario_id)
        prompt_completo = f"{SYSTEM_INSTRUCTION}{contexto_db}\n\nMensaje del usuario: {prompt_usuario}"

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_completo,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )
        return response_text or "Sin respuesta disponible."
    except APIError as e:
        if e.code == 429:
            retry_delay_seconds = None
            try:
                # Try to extract retry delay from error details
                if hasattr(e, 'details') and e.details:
                    import json
                    if isinstance(e.details, str):
                        try:
                            details = json.loads(e.details)
                        except:
                            details = {}
                    elif isinstance(e.details, dict):
                        details = e.details
                    else:
                        details = {}

                    if isinstance(details, dict) and 'retryDelay' in details:
                        delay_str = details['retryDelay']
                        if isinstance(delay_str, str) and delay_str.endswith('s'):
                            try:
                                retry_delay_seconds = int(delay_str[:-1])
                            except ValueError:
                                pass

                # Fallback: check error message for retry delay patterns
                if retry_delay_seconds is None and hasattr(e, 'message'):
                    msg = str(e.message)
                    import re
                    # Look for patterns like "retry after 60 seconds" or "60s"
                    match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                    if match:
                        retry_delay_seconds = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)s', msg)
                        if match:
                            retry_delay_seconds = int(match.group(1))

                # Determine appropriate response based on delay
                if retry_delay_seconds is not None and retry_delay_seconds <= 300:  # 5 minutes or less
                    return f"⚠️ Límite de tasa alcanzado. Por favor, espera {retry_delay_seconds} segundos antes de intentarlo nuevamente."
                else:
                    return "⚠️ Se ha agotado la cuota diaria gratuita de la API de Gemini. La cuota se reinicia a medianoche (hora del Pacífico). Por favor, intenta nuevamente mañana."
            except Exception as parse_error:
                # If parsing fails, fall back to safe message
                print(f"Error parsing 429 details in pensar_respuesta: {parse_error}")
                return "⚠️ Se ha alcanzado el límite de la API de Gemini. Verifica tu consumo y vuelve a intentar en unos minutos."
        return f"Error en la API de Gemini: {e.message}"
    except Exception as e:
        return f"Error en sistemas: {e}"

def analizar_inversion(ticker: str) -> str:
    """Analiza un activo bursátil combinando datos en vivo de yfinance y búsqueda web."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")

        datos_mercado = ""
        if not hist.empty:
            precio_actual = hist['Close'].iloc[-1]
            precio_anterior = hist['Close'].iloc[-2]
            cambio_pct = ((precio_actual - precio_anterior) / precio_anterior) * 100
            datos_mercado = f"Precio actual: ${precio_actual:,.2f} USD. Variación reciente: {cambio_pct:+.2f}%."
        else:
            datos_mercado = f"No se obtuvieron datos directos de yfinance para `{ticker}`."

        prompt_analisis = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            f"El usuario evalúa el activo o instrumento financiero: {ticker.upper()}.\n"
            f"Datos del mercado: {datos_mercado}\n"
            "Busca en la web el contexto reciente de este activo o empresa y realiza un análisis frío, objetivo y pragmático."
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_analisis,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                )
            ).text
        )
        return response_text or "Error analizando el activo."
    except APIError as e:
        if e.code == 429:
            retry_delay_seconds = None
            try:
                # Try to extract retry delay from error details
                if hasattr(e, 'details') and e.details:
                    import json
                    if isinstance(e.details, str):
                        try:
                            details = json.loads(e.details)
                        except:
                            details = {}
                    elif isinstance(e.details, dict):
                        details = e.details
                    else:
                        details = {}

                    if isinstance(details, dict) and 'retryDelay' in details:
                        delay_str = details['retryDelay']
                        if isinstance(delay_str, str) and delay_str.endswith('s'):
                            try:
                                retry_delay_seconds = int(delay_str[:-1])
                            except ValueError:
                                pass

                # Fallback: check error message for retry delay patterns
                if retry_delay_seconds is None and hasattr(e, 'message'):
                    msg = str(e.message)
                    import re
                    # Look for patterns like "retry after 60 seconds" or "60s"
                    match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                    if match:
                        retry_delay_seconds = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)s', msg)
                        if match:
                            retry_delay_seconds = int(match.group(1))

                # Determine appropriate response based on delay
                if retry_delay_seconds is not None and retry_delay_seconds <= 300:  # 5 minutes or less
                    return f"⚠️ Límite de tasa alcanzado. Por favor, espera {retry_delay_seconds} segundos antes de intentarlo nuevamente."
                else:
                    return "⚠️ Se ha agotado la cuota diaria gratuita de la API de Gemini. La cuota se reinicia a medianoche (hora del Pacífico). Por favor, intenta nuevamente mañana."
            except Exception as parse_error:
                # If parsing fails, fall back to safe message
                print(f"Error parsing 429 details in analizar_inversion: {parse_error}")
                return "⚠️ Se ha alcanzado el límite de la API de Gemini. Verifica tu consumo y vuelve a intentar en unos minutos."
        return f"Error de API: {e.message}"
    except Exception as e:
        return f"Error consultando el mercado para {ticker}: {e}"

def pensar_respuesta_imagen(ruta_imagen: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa una imagen (factura, recibo, captura) extrayendo transacciones automáticamente."""
    try:
        imagen_file = _gemini_call_with_fallback(lambda c: c.files.upload(file=ruta_imagen))
        prompt = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            "El usuario te envía esta imagen. Si se trata de un recibo, factura o comprobante de pago: "
            "1. Extrae el monto total, el establecimiento/comercio y la categoría aproximada. "
            "2. Responde confirmando los datos extraídos y realiza un juicio analítico sobre el gasto.\n\n"
            f"Comentario del usuario: {prompt_adicional}"
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, imagen_file],
                config=types.GenerateContentConfig(
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )

        if response_text:
            procesar_intencion_natural(response_text, usuario_id)

        try:
            imagen_file.delete()  # Assuming the file object has a delete method; if not, fallback
        except Exception:
            pass

        return response_text or "Imagen procesada sin texto resultante."
    except APIError as e:
        if e.code == 429:
            retry_delay_seconds = None
            try:
                # Try to extract retry delay from error details
                if hasattr(e, 'details') and e.details:
                    import json
                    if isinstance(e.details, str):
                        try:
                            details = json.loads(e.details)
                        except:
                            details = {}
                    elif isinstance(e.details, dict):
                        details = e.details
                    else:
                        details = {}

                    if isinstance(details, dict) and 'retryDelay' in details:
                        delay_str = details['retryDelay']
                        if isinstance(delay_str, str) and delay_str.endswith('s'):
                            try:
                                retry_delay_seconds = int(delay_str[:-1])
                            except ValueError:
                                pass

                # Fallback: check error message for retry delay patterns
                if retry_delay_seconds is None and hasattr(e, 'message'):
                    msg = str(e.message)
                    import re
                    # Look for patterns like "retry after 60 seconds" or "60s"
                    match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                    if match:
                        retry_delay_seconds = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)s', msg)
                        if match:
                            retry_delay_seconds = int(match.group(1))

                # Determine appropriate response based on delay
                if retry_delay_seconds is not None and retry_delay_seconds <= 300:  # 5 minutes or less
                    return f"⚠️ Límite de tasa alcanzado. Por favor, espera {retry_delay_seconds} segundos antes de intentarlo nuevamente."
                else:
                    return "⚠️ Se ha agotado la cuota diaria gratuita de la API de Gemini. La cuota se reinicia a medianoche (hora del Pacífico). Por favor, intenta nuevamente mañana."
            except Exception as parse_error:
                # If parsing fails, fall back to safe message
                print(f"Error parsing 429 details in pensar_respuesta_imagen: {parse_error}")
                return "⚠️ Se ha alcanzado el límite de la API de Gemini. Verifica tu consumo y vuelve a intentar en unos minutos."
        return f"Error de API al analizar imagen: {e.message}"
    except Exception as e:
        return f"Error analizando imagen: {e}"

def pensar_respuesta_audio(ruta_audio: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa archivos de audio recibidos inyectando estrictamente el contexto de la base de datos."""
    try:
        audio_file = _gemini_call_with_fallback(lambda c: c.files.upload(file=ruta_audio))
        contexto_db = obtener_contexto_financiero(usuario_id)

        prompt_completo = (
            f"{SYSTEM_INSTRUCTION}{contexto_db}\n\n"
            "Escucha el audio adjunto del usuario. Si pregunta por sus finanzas, gastos, historial o transacciones, "
            "DEBES responderle utilizando ÚNICAMENTE los datos reales de la base de datos proporcionados arriba. "
            "Prohibido inventar montos, fechas o categorías que no estén en esa lista."
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt_completo, audio_file],
                config=types.GenerateContentConfig(
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )
        try:
            audio_file.delete()
        except Exception:
            pass
        return response_text or ""
    except APIError as e:
        if e.code == 429:
            retry_delay_seconds = None
            try:
                # Try to extract retry delay from error details
                if hasattr(e, 'details') and e.details:
                    import json
                    if isinstance(e.details, str):
                        try:
                            details = json.loads(e.details)
                        except:
                            details = {}
                    elif isinstance(e.details, dict):
                        details = e.details
                    else:
                        details = {}

                    if isinstance(details, dict) and 'retryDelay' in details:
                        delay_str = details['retryDelay']
                        if isinstance(delay_str, str) and delay_str.endswith('s'):
                            try:
                                retry_delay_seconds = int(delay_str[:-1])
                            except ValueError:
                                pass

                # Fallback: check error message for retry delay patterns
                if retry_delay_seconds is None and hasattr(e, 'message'):
                    msg = str(e.message)
                    import re
                    # Look for patterns like "retry after 60 seconds" or "60s"
                    match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                    if match:
                        retry_delay_seconds = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)s', msg)
                        if match:
                            retry_delay_seconds = int(match.group(1))

                # Determine appropriate response based on delay
                if retry_delay_seconds is not None and retry_delay_seconds <= 300:  # 5 minutes or less
                    return f"⚠️ Límite de tasa alcanzado. Por favor, espera {retry_delay_seconds} segundos antes de intentarlo nuevamente."
                else:
                    return "⚠️ Se ha agotado la cuota diaria gratuita de la API de Gemini. La cuota se reinicia a medianoche (hora del Pacífico). Por favor, intenta nuevamente mañana."
            except Exception as parse_error:
                # If parsing fails, fall back to safe message
                print(f"Error parsing 429 details in pensar_respuesta_audio: {parse_error}")
                return "⚠️ Se ha alcanzado el límite de la API de Gemini. Verifica tu consumo y vuelve a intentar en unos minutos."
        return f"Error de API al procesar audio: {e.message}"
    except Exception as e:
        return f"Error al procesar audio: {e}"