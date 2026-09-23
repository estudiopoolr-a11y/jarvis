"""User-facing Gemini error messages."""
import re
from google.genai.errors import APIError

def _manejar_error_api(e: APIError, contexto: str = "general") -> str:
    """Maneja errores de API de Gemini de forma centralizada."""

    if e.code == 429:
        retry_seconds = None
        msg = str(e.message) if hasattr(e, 'message') else str(e)

        # Extraer retry delay
        match = _re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, _re.IGNORECASE)
        if match:
            retry_seconds = int(match.group(1))
        else:
            match = _re.search(r'(\d+)s', msg)
            if match:
                retry_seconds = int(match.group(1))

        if retry_seconds and retry_seconds <= 300:
            return f"⏳ Límite de velocidad (RPM). Espera {retry_seconds}s o vuelve en 1-2 minutos."
        return "⚠️ Cuota diaria de Gemini agotada. Se reinicia a medianoche (hora Colombia)."

    # Otros errores de API
    msg = str(e.message) if hasattr(e, 'message') else str(e)

    # Casos especiales con mensajes amigables
    if "high demand" in msg.lower():
        return "⏳ Gemini tiene alta demanda en este momento. Espera 1-2 minutos e intenta de nuevo."
    if "upload" in msg.lower() and "terminated" in msg.lower():
        return "⏳ Error con el archivo. Intenta enviar el audio/imagen de nuevo."
    if "quota" in msg.lower() or "limit" in msg.lower():
        return "⚠️ Cuota de Gemini agotada. Se reinicia a medianoche (hora Colombia)."

    # Mensaje genérico para otros errores
    print(f"Error de API en {contexto}: {msg}")
    return "⏳ Error temporal. Espera 1-2 minutos e intenta de nuevo."


def _manejar_error_generico(e: Exception, contexto: str = "general") -> str:
    """Maneja errores genéricos de forma centralizada."""
    msg = str(e)
    print(f"Error en {contexto}: {msg}")

    if "upload" in msg.lower() and "terminated" in msg.lower():
        return "⏳ Error con el archivo. Intenta enviar el audio/imagen de nuevo."
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return "⏳ Tiempo de espera agotado. Intenta de nuevo."
    if "connection" in msg.lower() or "network" in msg.lower():
        return "⏳ Error de conexión. Verifica tu internet e intenta de nuevo."

    return "⏳ Error temporal. Espera 1-2 minutos e intenta de nuevo."
