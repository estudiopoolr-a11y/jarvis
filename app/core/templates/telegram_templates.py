# Módulo de Templates: Plantillas estructurales de respuesta para Telegram #
from typing import Dict, Any  # Importar tipos para tipado de plantillas #

# Plantilla base para respuestas del bot en Telegram #
PLANTILLA_RESPUESTA_BASE: Dict[str, str] = {  # Diccionario con plantillas markdown predefinidas #
    "inicio": "🤖 *¡Hola! Soy JARVIS, tu asistente financiero inteligente.*\n\nAquí tienes los comandos disponibles:\n🔹 `/balance` o `/resumen` - Consulta tu saldo actual y resumen financiero.\n🔹 `/gasto <monto> <categoría>` - Registra un gasto rápidamente (ej: `/gasto 50 comida`).\n🔹 `/ayuda` - Muestra este menú.\n\nTambién puedes escribirme cualquier duda en lenguaje natural y usaré mi motor de IA para ayudarte.",  # Plantilla para comandos /start y /ayuda #
    "error_interno": "❌ Ocurrió un error interno. Por favor intenta nuevamente más tarde.",  # Plantilla genérica de error #
    "mantenimiento": "Hola, recibi tu mensaje pero mis servicios de IA estan en mantenimiento. Intenta nuevamente en un momento.",  # Plantilla de estado de mantenimiento #
}

def plantilla_comando_balance() -> str:  # Función que retorna plantilla fija para comando balance #
    """Retorna la plantilla base para comandos de balance (cuando no hay datos)."""
    return PLANTILLA_RESPUESTA_BASE["inicio"]  # Retornar plantilla de bienvenida/inicio #

def plantilla_respuesta_nlp(fallback: bool = False) -> str:  # Función que retorna plantilla para respuestas NLP #
    """Retorna plantilla adaptativa según si hubo fallback o no."""
    if fallback:  # Evaluar si se usó fallback por error en NLP #
        return PLANTILLA_RESPUESTA_BASE["mantenimiento"]  # Retornar plantilla de mantenimiento #
    return ""  # Retornar vacío para indicar que no hay plantilla fija #
