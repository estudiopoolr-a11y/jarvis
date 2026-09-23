"""bot/events/media_processor.py - Procesamiento de archivos adjuntos (audio, txt, imagen)."""
import os

from bot import TEMP_DIR
from bot.services.ai import resolve_ai
from bot.events.context_builder import es_archivo_texto, obtener_ruta_temporal


async def procesar_adjunto(message, adjunto, texto_limpio: str, usuario_id: str, prompt_con_contexto: str) -> str:
    """Procesa un archivo adjunto (audio, txt, csv)."""
    ruta = obtener_ruta_temporal(adjunto)
    await adjunto.save(ruta)

    try:
        if es_archivo_texto(adjunto):
            return _procesar_archivo_texto(ruta, usuario_id)
        else:
            return await _procesar_audio(ruta, texto_limpio, usuario_id, prompt_con_contexto)
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)


def _procesar_archivo_texto(ruta: str, usuario_id: str) -> str:
    """Procesa un archivo TXT o CSV importando sus datos."""
    try:
        from modules.importador_txt import importar_texto
        from modules import db as dbmod

        with open(ruta, "r", encoding="utf-8-sig", errors="replace") as f:
            texto_archivo = f.read()

        db = dbmod.inicializar_firebase()
        if not db:
            return "⚠️ No pude conectar con Firebase para importar el TXT."

        return importar_texto(usuario_id, texto_archivo, db, anio_default=2026)
    except Exception as txt_error:
        return f"⚠️ No pude importar el TXT: `{txt_error}`"


async def _procesar_audio(ruta: str, texto_limpio: str, usuario_id: str, prompt_con_contexto: str) -> str:
    """Procesa un archivo de audio (nota de voz)."""
    texto_transcrito = resolve_ai("transcribir_audio")(ruta)

    if texto_transcrito:
        # Procesar texto transcrito
        respuesta = resolve_ai("procesar_intencion_natural")(texto_transcrito, usuario_id, es_audio=True)
        if respuesta:
            return respuesta
        return resolve_ai("pensar_respuesta")(texto_transcrito)
    else:
        # No se pudo transcribir, usar prompt de audio
        prompt_audio = prompt_con_contexto if texto_limpio else ""
        return resolve_ai("pensar_respuesta_audio")(ruta, prompt_audio, usuario_id)
