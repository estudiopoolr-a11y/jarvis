"""
bot/services/tts.py - Generación de audio TTS usando edge-tts.

No bloquea el event loop de Discord; usa hilos separados.
"""
import asyncio
import hashlib
import os
import tempfile

try:
    import edge_tts
except ImportError:  # Permite importar el bot en entornos sin dependencias instaladas.
    edge_tts = None

from bot.state import _tts_cache, cache_tts_hit, cache_tts_store


TEMP_DIR = os.path.join(tempfile.gettempdir(), "jarvis_tts")
os.makedirs(TEMP_DIR, exist_ok=True)


def _limpiar_marca_tts(texto: str) -> str:
    """Quita marcas markdown para TTS."""
    if not texto:
        return ""
    return texto.replace("**", "").replace("*", "").replace("#", "").replace("`", "").strip()


async def _generar_tts_async(texto: str, output_path: str) -> None:
    """Genera audio TTS usando edge-tts (no bloquea event loop)."""
    if cache_tts_hit(texto, output_path):
        return

    if edge_tts is None:
        raise RuntimeError("edge-tts no está instalado")
    communicate = edge_tts.Communicate(texto, "es-MX")
    await communicate.save(output_path)
    cache_tts_store(texto)


def _generar_tts_sincrono(texto: str, output_path: str) -> None:
    """Genera TTS de forma síncrona (fallback)."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_generar_tts_async(texto, output_path))
    finally:
        loop.close()


def generar_audio_respuesta(texto: str, output_path: str | None = None) -> str:
    """
    Genera respuesta de audio usando edge-tts.

    Esta función es NO BLOQUEANTE: lanza la generación en background.
    El archivo estará disponible cuando termine (típicamente <1s).

    Args:
        texto: Texto a convertir a audio
        output_path: Ruta opcional. Si no se da, usa TEMP_DIR/tts_{hash}.mp3

    Returns:
        Ruta al archivo generado, o "" si falló.
    """
    texto_limpio = _limpiar_marca_tts(texto)
    if not texto_limpio:
        return ""

    # Truncar a 800 caracteres, cortando por palabras
    if len(texto_limpio) > 800:
        texto_limpio = texto_limpio[:800].rsplit(" ", 1)[0] + "..."

    if output_path is None:
        cache_key = hashlib.md5(texto_limpio.encode("utf-8")).hexdigest()
        output_path = os.path.join(TEMP_DIR, f"tts_{cache_key}.mp3")

    # Crear directorio padre si no existe
    padre = os.path.dirname(output_path)
    if padre and not os.path.exists(padre):
        os.makedirs(padre, exist_ok=True)

    # Ejecutar en hilo separado para no bloquear el event loop de Discord
    try:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_generar_tts_async(texto_limpio, output_path))
        finally:
            loop.close()
    except Exception as e:
        print(f"Error generando TTS: {e}")
        return ""

    return output_path if os.path.exists(output_path) else ""