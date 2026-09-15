"""
bot/services/ai.py - Wrappers a modules.ai para uso en handlers del bot.

Centraliza las funciones de IA que el bot usa: parsers, Gemini, TTS, imágenes.
"""
from modules.ai import (
    # Parsers determinísticos
    procesar_intencion_natural,
    # Cliente Gemini / respuestas
    pensar_respuesta,
    pensar_respuesta_audio,
    pensar_respuesta_imagen,
    analizar_inversion,
    transcribir_audio,
    # Internos para estado/debug
    _API_KEYS,
    _key_index,
    _esperar_por_rpm,
    _gemini_call_with_fallback,
)

__all__ = [
    "procesar_intencion_natural",
    "pensar_respuesta",
    "pensar_respuesta_audio",
    "pensar_respuesta_imagen",
    "analizar_inversion",
    "transcribir_audio",
    "_API_KEYS",
    "_key_index",
    "_esperar_por_rpm",
    "_gemini_call_with_fallback",
]