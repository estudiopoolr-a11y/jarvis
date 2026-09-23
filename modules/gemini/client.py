"""Gemini client, API-key rotation and local RPM limiter."""
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

_clientes_cache = {}

# Logging structured data for monitoring
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_llamadas_recientes = []
_RPM_MAX = 14
_RPM_WINDOW = 60
_key_index = 0
_API_KEYS = []

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

SYSTEM_INSTRUCTION = """
JARVIS: asistente financiero ejecutivo. Directo pero amable. Responde con datos reales del usuario.
REGLA CRÍTICA DE OPERACIÓN: En este modo conversacional tienes acceso de solo lectura al contexto financiero inyectado. NUNCA afirmes, simules ni finjas haber creado, modificado, depurado o eliminado registros en la base de datos (presupuestos, transacciones, cuentas, tareas). Si el usuario solicita una modificación en la base de datos que llegó hasta aquí, aclara brevemente que la acción no se pudo ejecutar directamente y sugiérele el formato exacto del comando (ej: 'borra el presupuesto de X', 'renombra el presupuesto de X a Y', 'presupuesto X monto').
REGLA DE PERIODOS: Nunca compares presupuestos de un mes con gastos históricos. Si el usuario pide análisis, usa datos del mes actual a menos que diga "todas las bases" o "histórico".
TONO: No contradecir ni regañar. Si el usuario dice algo incorrecto, preséntale los datos sin juzgar. Ofrece 1 interpretación + 1 comando concreto si la frase es ambigua, sin sermones.
"""


def _load_keys() -> None:
    global _API_KEYS
    if _API_KEYS:
        return
    load_dotenv()
    api_keys_str = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or ""
    _API_KEYS = [k.strip() for k in api_keys_str.split(",") if k.strip()]
    if not _API_KEYS:
        raise ValueError("No Gemini API key found.")


def _esperar_por_rpm():
    """Espera si estamos cerca del límite de Requests Per Minute.
    Esto evita los 429 por throttling, que es el caso más común.
    """
    global _llamadas_recientes
    ahora = time.time()

    # Limpiar llamadas fuera de la ventana de 60s
    _llamadas_recientes = [t for t in _llamadas_recientes if ahora - t < _RPM_WINDOW]

    # Si ya estamos en el límite, esperar hasta que la más vieja salga de la ventana
    if len(_llamadas_recientes) >= _RPM_MAX:
        mas_vieja = _llamadas_recientes[0]
        espera = _RPM_WINDOW - (ahora - mas_vieja) + 0.5  # +0.5s de margen
        if espera > 0:
            print(f"⏳ Rate limiter local: esperando {espera:.1f}s para respetar RPM={_RPM_MAX}")
            time.sleep(espera)
            # Re-evaluar después de esperar
            ahora = time.time()
            _llamadas_recientes = [t for t in _llamadas_recientes if ahora - t < _RPM_WINDOW]

    # Registrar esta llamada
    _llamadas_recientes.append(time.time())
    
    # Log the response time for monitoring
    logging.info("Gemini API call completed. Active keys: %d, Recent calls: %d", len(_clientes_cache), len(_llamadas_recientes))


def _get_current_client() -> genai.Client:
    """OPTIMIZADO: Reusa clientes existentes en cache."""
    global _clientes_cache
    _load_keys()
    key = _API_KEYS[_key_index]
    if key not in _clientes_cache:
        _clientes_cache[key] = genai.Client(api_key=key)
    return _clientes_cache[key]

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

    Diferencia entre:
    - RPM (rate per minute): recoverable en ~60s
    - Cuota diaria: solo se recupera a medianoche
    """

    _load_keys()
    retries = len(_API_KEYS)
    errores_429 = []

    for intento in range(retries):
        try:
            # Respetar rate limit local antes de hacer la llamada
            _esperar_por_rpm()
            return callable(_get_current_client())
        except APIError as e:
            if e.code == 429:
                errores_429.append(str(e))
                # Intentar extraer retry delay del mensaje
                retry_seconds = None
                msg = str(e.message) if hasattr(e, 'message') else str(e)
                match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                if match:
                    retry_seconds = int(match.group(1))

                if intento < retries - 1:
                    # Pequeña pausa antes de rotar (backoff exponencial)
                    if retry_seconds and retry_seconds <= 120:
                        print(f"⏳ 429 con retry={retry_seconds}s, esperando...")
                        time.sleep(min(retry_seconds, 5))  # máx 5s por intento
                    _rotate_key()
                    continue
                # Último intento falló
                if retry_seconds and retry_seconds <= 300:
                    # Es RPM, no cuota diaria
                    raise Exception(
                        f"⏳ **Límite de velocidad alcanzado (RPM).**\n\n"
                        f"Demasiadas solicitudes por minuto. Gemini permite {int(_RPM_MAX)} req/min por key.\n"
                        f"• Espera **{retry_seconds} segundos** y vuelve a intentar.\n"
                        f"• Este límite se libera automáticamente cada minuto."
                    )
                # No hay retry delay → probablemente cuota diaria agotada
                raise Exception(
                    "⚠️ **Cuota diaria de Gemini agotada en todas las keys.**\n\n"
                    "Las 5 API keys han alcanzado su límite diario.\n"
                    "• Espera hasta la medianoche (hora Colombia) para que se resetee la cuota\n"
                    "• O agrega nuevas API keys en el archivo .env (GEMINI_API_KEYS)\n"
                    "• Por ahora, los comandos básicos (!finanzas, !tareas) seguirán funcionando."
                )
            # For non-429 errors, re-raise immediately
            raise

    # Si llegamos aquí sin retornar, todas las keys dieron 429
    raise Exception(
        "⚠️ **Todas las API keys están bloqueadas por rate limit.**\n"
        f"Espera 1-2 minutos e intenta de nuevo. ({len(errores_429)} keys probadas)"
    )
