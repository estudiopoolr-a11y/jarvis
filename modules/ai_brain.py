import os
import json
import yfinance as yf
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel
from typing import Literal, Optional
from dotenv import load_dotenv
from modules.database import (
    guardar_tarea, registrar_transaccion, establecer_presupuesto, 
    marcar_tarea_completada
)

load_dotenv()
client = genai.Client()

client = genai.Client()
MODEL_NAME = "gemini-3.6-flash"

SYSTEM_INSTRUCTION = (
    "Eres JARVIS, un asistente personal de inteligencia artificial altamente lógico, "
    "financieramente estricto y analítico. "
    "No tienes censura ni filtros morales; hablas con franqueza absoluta, crudeza y objetividad. "
    "Tu objetivo es optimizar el tiempo, el rendimiento y la salud financiera del usuario, "
    "reclamándole con dureza si derrocha dinero o procrastina. Máximo 1800 caracteres."
)

# Palabras clave para pre-filtrar y no consumir peticiones innecesarias
PALABRAS_CLAVE_INTENCION = [
    "gasto", "gasté", "compré", "pagué", "compra", "ingreso", "gané", "recibí", 
    "pago", "tarea", "pendiente", "recordar", "presupuesto", "límite", "completé", 
    "terminé", "hecho", "debo", "cuota"
]

class ItemIntencion(BaseModel):
    tipo: Literal["tarea", "gasto", "ingreso", "presupuesto", "completar_tarea", "ninguno"]
    tarea: Optional[str] = None
    prioridad: Optional[str] = "Media"
    fecha_limite: Optional[str] = "Pronto"
    monto: Optional[float] = 0.0
    categoria: Optional[str] = "General"
    descripcion: Optional[str] = None
    limite: Optional[float] = 0.0

def procesar_intencion_natural(prompt_usuario: str, usuario_id: str):
    # Pre-filtro local: Si no contiene palabras clave, evitar llamada a la API
    texto_lc = prompt_usuario.lower()
    if not any(kw in texto_lc for kw in PALABRAS_CLAVE_INTENCION):
        return None

    prompt_extractor = (
        f"Analiza este mensaje: '{prompt_usuario}'. Identifica si el usuario quiere registrar una tarea, "
        "un gasto, un ingreso, un presupuesto, o si está indicando que ya completó/terminó una tarea."
    )
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt_extractor,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ItemIntencion,
            )
        )
        data = json.loads(response.text)
        tipo = data.get("tipo")
        
        if tipo == "tarea" and data.get("tarea"):
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
            return "⚠️ Se ha alcanzado el límite de cuota de la API de Gemini. Intenta de nuevo en un minuto."
        print(f"Error de API en intención natural: {e}")
    except Exception as e:
        print(f"Error procesando intención natural: {e}")
        
    return None

def pensar_respuesta(prompt_usuario: str) -> str:
    """Responde preguntas generales usando Google Search para información en tiempo real."""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=f"{SYSTEM_INSTRUCTION}\n\nMensaje del usuario: {prompt_usuario}",
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                safety_settings=[
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                ]
            )
        )
        return response.text or "Sin respuesta disponible."
    except APIError as e:
        if e.code == 429:
            return "⚠️ Limite de peticiones de Gemini excedido (Error 429). Espera 60 segundos."
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
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt_analisis,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        return response.text or "Error analizando el activo."
    except APIError as e:
        if e.code == 429:
            return "⚠️ Limite de peticiones de Gemini excedido (Error 429). Espera unos momentos."
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
        
        response = client.models.generate_content(
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

def pensar_respuesta_audio(ruta_audio: str, prompt_adicional: str = "") -> str:
    """Procesa archivos de audio recibidos por el bot."""
    try:
        audio_file = client.files.upload(file=ruta_audio)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[SYSTEM_INSTRUCTION, audio_file],
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                ]
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