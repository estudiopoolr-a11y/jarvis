import os
import re
import json
import time
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
    obtener_contexto_financiero
)

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# gemini-2.0-flash tiene los límites de cuota gratuitos más altos y soporta texto, imagen y audio.
# Para eliminar límites por completo, activa la facturación en tu proyecto de Google AI Studio.
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Configuración de seguridad reutilizable (evita bloqueos de contenido).
SAFETY_SETTINGS = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]


def _analizar_error_cuota(e: APIError):
    """Extrae de un error 429 el tiempo de espera sugerido y si es un límite diario.

    Devuelve (es_limite_diario: bool, segundos_espera: int | None).
    """
    segundos = None
    es_diario = False

    # 1) Intentar leer los 'details' estructurados que devuelve Google.
    detalles = getattr(e, "details", None)
    try:
        error_obj = detalles.get("error", detalles) if isinstance(detalles, dict) else {}
        lista = error_obj.get("details", []) if isinstance(error_obj, dict) else []
        for d in lista:
            if not isinstance(d, dict):
                continue
            tipo = d.get("@type", "")
            if "RetryInfo" in tipo and d.get("retryDelay"):
                rd = str(d["retryDelay"]).replace("s", "").strip()
                try:
                    segundos = int(float(rd))
                except ValueError:
                    pass
            if "QuotaFailure" in tipo:
                for v in d.get("violations", []):
                    identificador = (v.get("quotaId", "") + v.get("quotaMetric", "")).lower()
                    if "perday" in identificador or "per_day" in identificador:
                        es_diario = True
    except Exception:
        pass

    # 2) Respaldo: buscar pistas en el texto del error.
    texto = str(getattr(e, "message", "") or e)
    if segundos is None:
        m = re.search(r"retryDelay['\"]?:?\s*['\"]?(\d+)\s*s", texto)
        if m:
            segundos = int(m.group(1))
    if not es_diario and ("perday" in texto.lower().replace(" ", "") or "per day" in texto.lower()):
        es_diario = True

    return es_diario, segundos


def _mensaje_429(e: APIError) -> str:
    """Genera un mensaje claro para el usuario según el tipo de límite alcanzado."""
    es_diario, segundos = _analizar_error_cuota(e)
    if es_diario:
        return (
            "⚠️ **Cuota diaria gratuita de Gemini agotada.** No se soluciona esperando unos segundos: "
            "el límite diario del plan gratuito solo se reinicia a medianoche (hora del Pacífico, UTC-8). "
            "Para operar sin límites, activa la facturación de tu proyecto en Google AI Studio."
        )
    espera = segundos or 60
    return f"⚠️ Límite de peticiones por minuto de Gemini alcanzado (Error 429). Reintenta en {espera} segundos."


def _generar_con_reintento(**kwargs):
    """Llama a Gemini reintentando ante 429 por minuto; no reintenta si es límite diario."""
    intentos = 3
    for intento in range(intentos):
        try:
            return client.models.generate_content(**kwargs)
        except APIError as e:
            if getattr(e, "code", None) != 429:
                raise
            es_diario, segundos = _analizar_error_cuota(e)
            # Un límite diario no se recupera esperando segundos: fallar de inmediato.
            if es_diario or intento == intentos - 1:
                raise
            espera = min(segundos or (5 * (intento + 1)), 30)
            print(f"⚠️ Cuota de Gemini excedida (429). Reintentando en {espera}s... ({intento + 1}/{intentos})")
            time.sleep(espera)


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

def procesar_intencion_natural(prompt_usuario: str, usuario_id: str):
    texto_lc = prompt_usuario.lower()
    if not any(kw in texto_lc for kw in PALABRAS_CLAVE_INTENCION):
        return None

    prompt_extractor = (
        f"Analiza este mensaje del usuario: '{prompt_usuario}'. "
        "Si el usuario está pidiendo reiniciar, limpiar, borrar los datos viejos o cargar categorías, presupuestos y transacciones en bloque, "
        "clasifícalo como 'configuracion_masiva' y extrae un diccionario de presupuestos {'Categoria': limite} y una lista de transacciones [{'tipo': 'gasto'/'ingreso', 'monto': 0.0, 'categoria': '', 'descripcion': ''}]. "
        "Si no es masivo, identifica si es tarea, gasto, ingreso, presupuesto o completar_tarea."
    )
    
    try:
        response = _generar_con_reintento(
            model=MODEL_NAME,
            contents=prompt_extractor,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ItemIntencion,
            )
        )
        data = json.loads(response.text)
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
            return _mensaje_429(e)
        print(f"Error de API en intención natural: {e}")
    except Exception as e:
        print(f"Error procesando intención natural: {e}")
        
    return None

def pensar_respuesta(prompt_usuario: str, usuario_id: str = "default") -> str:
    """Responde preguntas generales inyectando el contexto de Firebase y Google Search."""
    try:
        contexto_db = obtener_contexto_financiero(usuario_id)
        prompt_completo = f"{SYSTEM_INSTRUCTION}{contexto_db}\n\nMensaje del usuario: {prompt_usuario}"
        
        response = _generar_con_reintento(
            model=MODEL_NAME,
            contents=prompt_completo,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                safety_settings=SAFETY_SETTINGS,
            )
        )
        return response.text or "Sin respuesta disponible."
    except APIError as e:
        if e.code == 429:
            return "⚠️ Límite de peticiones de Gemini excedido (Error 429). Espera 60 segundos."
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
        
        response = _generar_con_reintento(
            model=MODEL_NAME,
            contents=prompt_analisis,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        return response.text or "Error analizando el activo."
    except APIError as e:
        if e.code == 429:
            return "⚠️ Límite de peticiones de Gemini excedido (Error 429)."
        return f"Error de API: {e.message}"
    except Exception as e:
        return f"Error consultando el mercado para {ticker}: {e}"

def pensar_respuesta_imagen(ruta_imagen: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa una imagen (factura, recibo, captura) extrayendo transacciones automáticamente."""
    try:
        imagen_file = client.files.upload(file=ruta_imagen)
        prompt = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            "El usuario te envía esta imagen. Si se trata de un recibo, factura o comprobante de pago: "
            "1. Extrae el monto total, el establecimiento/comercio y la categoría aproximada. "
            "2. Responde confirmando los datos extraídos y realiza un juicio analítico sobre el gasto.\n\n"
            f"Comentario del usuario: {prompt_adicional}"
        )
        
        response = _generar_con_reintento(
            model=MODEL_NAME,
            contents=[prompt, imagen_file],
            config=types.GenerateContentConfig(
                safety_settings=SAFETY_SETTINGS,
            )
        )
        
        if response.text:
            procesar_intencion_natural(response.text, usuario_id)
            
        try: client.files.delete(name=imagen_file.name)
        except: pass
        
        return response.text or "Imagen procesada sin texto resultante."
    except APIError as e:
        if e.code == 429:
            return "⚠️ Límite de peticiones de Gemini excedido (Error 429)."
        return f"Error de API al analizar imagen: {e.message}"
    except Exception as e:
        return f"Error analizando imagen: {e}"

def pensar_respuesta_audio(ruta_audio: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa archivos de audio recibidos inyectando estrictamente el contexto de la base de datos."""
    try:
        audio_file = client.files.upload(file=ruta_audio)
        contexto_db = obtener_contexto_financiero(usuario_id)
        
        prompt_completo = (
            f"{SYSTEM_INSTRUCTION}{contexto_db}\n\n"
            "Escucha el audio adjunto del usuario. Si pregunta por sus finanzas, gastos, historial o transacciones, "
            "DEBES responderle utilizando ÚNICAMENTE los datos reales de la base de datos proporcionados arriba. "
            "Prohibido inventar montos, fechas o categorías que no estén en esa lista."
        )
        
        response = _generar_con_reintento(
            model=MODEL_NAME,
            contents=[prompt_completo, audio_file],
            config=types.GenerateContentConfig(
                safety_settings=SAFETY_SETTINGS,
            )
        )
        try: client.files.delete(name=audio_file.name)
        except: pass
        return response.text or ""
    except APIError as e:
        if e.code == 429:
            return "⚠️ Límite de peticiones de Gemini excedido (Error 429)."
        return f"Error de API al procesar audio: {e.message}"
    except Exception as e:
        return f"Error al procesar audio: {e}"
