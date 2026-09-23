"""Generative fallback (read-only). Never mutates Firestore."""
import hashlib
import time

from google.genai import types
from google.genai.errors import APIError

from modules.db import obtener_contexto_financiero
from modules.gemini.client import MODEL_NAME, SYSTEM_INSTRUCTION, _gemini_call_with_fallback
from modules.gemini.errors import _manejar_error_api, _manejar_error_generico

_busquedas_cache = {}
_CACHE_WEB_TTL = 3600

def _gemini_call_with_cache(prompt: str, usar_web: bool = True, max_tokens: int = 1500):
    """Llama a Gemini con cache de búsquedas web para evitar repetir la misma query."""
    cache_key = hashlib.md5(f"{prompt}|{usar_web}".encode()).hexdigest()
    ahora = time.time()

    # Verificar cache
    if cache_key in _busquedas_cache:
        timestamp, resultado = _busquedas_cache[cache_key]
        if ahora - timestamp < _CACHE_WEB_TTL:
            return resultado

    # Hacer llamada real
    tools = [{"google_search": {}}] if usar_web else None
    resultado = _gemini_call_with_fallback(
        lambda c: c.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=tools,
                max_output_tokens=max_tokens
            )
        ).text
    )

    if resultado:
        _busquedas_cache[cache_key] = (ahora, resultado)

    return resultado


def _necesita_busqueda_web(texto: str) -> bool:
    """Determina si la pregunta requiere búsqueda web en tiempo real."""
    texto_lower = texto.lower()
    palabras_web = [
        "noticia", "actual", "hoy", "ayer", "esta semana", "último", "ultimo",
        "precio", "vale", "cuesta", "tasa", "cdt", "inflación", "inflacion",
        "dolar", "dólar", "trm", "bolsa", "mercado", "invertir", "inversion",
        "noticias", "2026", "2025", "reciente"
    ]
    return any(p in texto_lower for p in palabras_web)


def pensar_respuesta(prompt_usuario: str, usuario_id: str = "default") -> str:
    """Responde preguntas generales inyectando el contexto de Firebase y Google Search."""
    try:
        contexto_db = obtener_contexto_financiero(usuario_id)
        from modules.memory.rag import obtener_contexto_historico
        contexto_historico = obtener_contexto_historico(prompt_usuario)
        prompt_completo = f"{SYSTEM_INSTRUCTION}{contexto_db}\n{contexto_historico}\n\nMensaje del usuario: {prompt_usuario}"

        # OPTIMIZADO: Solo usar google_search si es necesario
        usar_web = _necesita_busqueda_web(prompt_usuario)
        tools = [{"google_search": {}}] if usar_web else None

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_completo,
                config=types.GenerateContentConfig(
                    tools=tools,
                    max_output_tokens=1500,
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
        return _manejar_error_api(e, contexto="pensar_respuesta")
    except Exception as e:
        return _manejar_error_generico(e, contexto="pensar_respuesta")

def pensar_respuesta_imagen(ruta_imagen: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa una imagen (factura, recibo, captura) extrayendo transacciones automáticamente."""
    imagen_file = None
    try:
        imagen_file = _gemini_call_with_fallback(lambda c: c.files.upload(file=ruta_imagen))
        # OPTIMIZADO: Prompt más corto + max_output_tokens
        prompt = (
            f"{SYSTEM_INSTRUCTION}\n"
            "Si es recibo/factura: extrae monto, establecimiento, categoría. "
            f"Comentario: {prompt_adicional}"
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, imagen_file],
                config=types.GenerateContentConfig(
                    max_output_tokens=1000,
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

        return response_text or "Imagen procesada sin texto resultante."
    except APIError as e:
        return _manejar_error_api(e, contexto="imagen")
    except Exception as e:
        return _manejar_error_generico(e, contexto="imagen")
    finally:
        if imagen_file is not None:
            try:
                imagen_file.delete()
            except Exception:
                pass

def pensar_respuesta_audio(ruta_audio: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa archivos de audio recibidos inyectando estrictamente el contexto de la base de datos.

    OPTIMIZADO: Una sola llamada API (sube audio + genera respuesta con contexto).
    """
    audio_file = None
    try:
        # Subir audio una sola vez
        audio_file = _gemini_call_with_fallback(lambda c: c.files.upload(file=ruta_audio))
        contexto_db = obtener_contexto_financiero(usuario_id)

        # Construir prompt: system + contexto + instrucción
        prompt_base = "Responde de forma concisa. Solo usa los datos proporcionados."
        if prompt_adicional:
            prompt_completo = f"{SYSTEM_INSTRUCTION}\n{contexto_db}\n{prompt_base}\n\nContexto adicional: {prompt_adicional}"
        else:
            prompt_completo = f"{SYSTEM_INSTRUCTION}\n{contexto_db}\n{prompt_base}"

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt_completo, audio_file],
                config=types.GenerateContentConfig(
                    max_output_tokens=1000,
                    temperature=0.3,
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )
        return response_text.strip() if response_text else "No pude procesar el audio. Intenta de nuevo."
    except APIError as e:
        return _manejar_error_api(e, contexto="audio")
    except Exception as e:
        return _manejar_error_generico(e, contexto="audio")
    finally:
        # SIEMPRE limpiar el archivo subido para evitar "Upload has already been terminated"
        if audio_file is not None:
            try:
                audio_file.delete()
            except Exception:
                pass