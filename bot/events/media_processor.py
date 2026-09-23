"""bot/events/media_processor.py - Procesamiento de archivos adjuntos (audio, txt, imagen)."""
import os

from bot import TEMP_DIR
from bot.services.ai import resolve_ai
from bot.events.context_builder import es_archivo_texto, obtener_ruta_temporal


async def procesar_adjunto(message, adjunto, texto_limpio: str, usuario_id: str, prompt_con_contexto: str) -> str:
    """Procesa un archivo adjunto (audio, txt, csv, imagen)."""
    ruta = obtener_ruta_temporal(adjunto)
    await adjunto.save(ruta)

    try:
        if es_archivo_texto(adjunto):
            return _procesar_archivo_texto(ruta, usuario_id)
        elif _es_imagen(adjunto):
            return _procesar_imagen(ruta, texto_limpio, usuario_id)
        else:
            return await _procesar_audio(ruta, texto_limpio, usuario_id, prompt_con_contexto)
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)


_FORMATOS_IMAGEN = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")


def _es_imagen(adjunto) -> bool:
    """Determina si el adjunto es una imagen, por extensión o content-type."""
    nombre = (adjunto.filename or "").lower()
    tipo = adjunto.content_type or ""
    return nombre.endswith(_FORMATOS_IMAGEN) or tipo.startswith("image/")


def _procesar_imagen(ruta: str, texto_limpio: str, usuario_id: str) -> str:
    """Enruta una imagen a factura (flujo de presupuesto) o a OCR de texto.

    La lectura la hace Gemini Vision; el registro del gasto, si lo hay, lo hace
    el router determinístico. Gemini nunca escribe en Firestore.
    """
    from modules.gemini.vision import analizar_factura, extraer_texto_imagen

    factura = analizar_factura(ruta)
    if factura:
        return _registrar_factura(factura, usuario_id)

    texto = extraer_texto_imagen(ruta)
    if texto_limpio:
        return f"📸 **Texto extraído de la imagen:**\n{texto}\n\n_Tu nota: {texto_limpio}_"
    return f"📸 **Texto extraído de la imagen:**\n{texto}"


def _registrar_factura(factura: dict, usuario_id: str) -> str:
    """Pasa el total leído al flujo determinístico de transacciones.

    Si el router no logra registrarlo (categoría sin coincidencia, por ejemplo),
    devuelve los datos leídos para que el usuario confirme con un comando.
    """
    comando = f"gasté {factura['monto']} en {factura['categoria']} {factura['comercio']}"
    try:
        respuesta = resolve_ai("procesar_intencion_natural")(comando, usuario_id, es_audio=False)
    except Exception as e:
        print(f"Error registrando factura por flujo determinístico: {e}")
        respuesta = None

    if respuesta:
        return f"🧾 Factura leída: **${factura['monto']:,.0f}** en {factura['comercio']}.\n{respuesta}"

    return (
        f"🧾 Leí una factura de **${factura['monto']:,.0f}** en {factura['comercio']} "
        f"(categoría sugerida: {factura['categoria']}), pero no pude registrarla automáticamente.\n"
        f"Para guardarla, escríbeme: `{comando}`"
    )


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
