"""bot/events/context_builder.py - Construcción de contexto para Gemini."""
import os

from bot import TEMP_DIR
from bot.services.db import (
    obtener_tareas_pendientes,
    obtener_contexto_financiero,
)


PALABRAS_CLAVE_FINANZAS = [
    "gasto", "gastos", "finanzas", "balance", "movimiento",
    "dinero", "registre", "presupuesto",
]

PALABRAS_CLAVE_TAREAS = [
    "tarea", "tareas", "pendiente", "pendientes", "recordatorio",
]


def construir_prompt_con_contexto(
    prompt_base: str,
    texto_lower: str,
    usuario_id: str,
    adjunto
) -> str:
    """Construye el prompt enriquecido con contexto financiero y de tareas."""
    prompt = prompt_base

    # Agregar contexto financiero si es relevante
    if any(k in texto_lower for k in PALABRAS_CLAVE_FINANZAS) or bool(adjunto):
        prompt += f"\n{obtener_contexto_financiero(usuario_id)}\nUsa SOLO estos datos."

    # Agregar contexto de tareas si es relevante
    if any(k in texto_lower for k in PALABRAS_CLAVE_TAREAS) or bool(adjunto):
        tareas = obtener_tareas_pendientes(usuario_id)
        prompt += f"\nTareas:{len(tareas)}"

    return prompt


def es_archivo_texto(adjunto) -> bool:
    """Determina si el adjunto es un archivo de texto."""
    return (
        adjunto.filename.lower().endswith((".txt", ".csv"))
        or (adjunto.content_type or "").startswith("text/")
    )


def obtener_ruta_temporal(adjunto) -> str:
    """Obtiene la ruta temporal para guardar el adjunto."""
    return os.path.join(TEMP_DIR, adjunto.filename)
