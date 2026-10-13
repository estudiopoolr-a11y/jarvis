"""Wrapper de inferencia NVIDIA NIM (resistente a errores)."""
import logging

from modules.nvidia.client import pensar_respuesta_nvidia

logger = logging.getLogger("jarvis.nvidia.think")


def pensar_respuesta(prompt: str) -> str:
    """
    Llama a NVIDIA NIM de forma segura.
    Captura excepciones y retorna mensajes amigables al usuario.
    """
    try:
        import asyncio

        return asyncio.run(pensar_respuesta_nvidia(prompt))
    except ValueError as exc:
        # Sin claves configuradas
        logger.error("NVIDIA sin configuración: %s", exc)
        return (
            "⚠️ NVIDIA NIM no está configurado. "
            "Agrega NVIDIA_API_KEYS a tu archivo .env para habilitar el motor de respaldo."
        )
    except Exception as exc:
        logger.error("Error en NVIDIA NIM: %s", exc)
        return "⏳ Error temporal al consultar NVIDIA NIM. Intenta de nuevo."
