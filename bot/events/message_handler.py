"""bot/events/message_handler.py - Lógica principal de procesamiento de mensajes."""
import re
import time
from datetime import datetime

import discord

from bot import bot, ALLOWED_ROLE_IDS
from bot.state import (
    usuarios_silenciados,
    canales_activos,
    _last_msg_time,
    _COOLDOWN_SEGUNDOS,
    obtener_contexto_cacheado,
    hay_conversacion_activa,
    registrar_mensaje_conversacion,
    completar_consulta_presupuesto,
)
from bot.services.ai import resolve_ai
from bot.services.db import (
    guardar_mensaje,
    obtener_tareas_pendientes,
    obtener_balance_financiero,
    obtener_contexto_financiero,
    obtener_resumen_presupuestos,
)
from bot.events.media_processor import procesar_adjunto
from bot.events.context_builder import construir_prompt_con_contexto


def _cargar_contexto_financiero(usuario_id: str):
    """Ensambla (balance, ingresos, gastos, movimientos, presupuestos) para el cache."""
    balance, ingresos, gastos, movimientos = obtener_balance_financiero(usuario_id)
    presupuestos = obtener_resumen_presupuestos(usuario_id)
    return balance, ingresos, gastos, movimientos, presupuestos


def _debe_ignorar_mensaje(message, usuario_id: str) -> bool:
    """Verifica si el mensaje debe ser ignorado (bot, silenciado, cooldown)."""
    if message.author.bot:
        return True

    if usuario_id in usuarios_silenciados:
        if datetime.now() < usuarios_silenciados[usuario_id]:
            return True
        else:
            del usuarios_silenciados[usuario_id]

    ahora = time.time()
    if _last_msg_time.get(usuario_id, 0) >= ahora - _COOLDOWN_SEGUNDOS:
        return True
    _last_msg_time[usuario_id] = ahora

    return False


def _obtener_adjunto_relevante(message):
    """Obtiene el adjunto relevante (audio, txt, csv) del mensaje."""
    formatos_audio = (".ogg", ".mp3", ".wav", ".m4a", ".aac", ".flac")
    formatos_txt = (".txt", ".csv")

    return next(
        (
            a
            for a in message.attachments
            if (
                a.filename.lower().endswith(formatos_audio + formatos_txt)
                or "audio" in (a.content_type or "")
                or (a.content_type or "").startswith("text/")
            )
        ),
        None,
    )


def _verificar_permisos_mencion(message) -> bool:
    """Verifica si el mensaje tiene mención válida o está en conversación activa."""
    es_mencion_usuario = bot.user.mentioned_in(message)
    es_mencion_rol = any(role.id in ALLOWED_ROLE_IDS for role in message.role_mentions)
    return es_mencion_usuario or es_mencion_rol


async def _procesar_saludo(message, usuario_id: str, texto_lower: str) -> bool:
    """Procesa saludos rápidos. Retorna True si se manejó el mensaje."""
    saludos = ["hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches"]
    if texto_lower not in saludos:
        return False

    try:
        balance, *_ = obtener_contexto_cacheado(
            usuario_id, lambda: _cargar_contexto_financiero(usuario_id)
        )
        saludo_extra = f" Balance actual: ${balance:,.0f}."
        await message.channel.send(
            f"Sistemas activos.{saludo_extra} Sin tareas críticas pendientes."
        )
    except Exception as e:
        await message.channel.send(f"⚠️ Error cargando datos locales: {e}")
    return True


async def _procesar_intencion_deterministica(message, texto_limpio: str, usuario_id: str) -> bool:
    """Intenta procesar con parser determinístico. Retorna True si se manejó."""
    try:
        respuesta_intencion = resolve_ai("procesar_intencion_natural")(
            texto_limpio, usuario_id, es_audio=False
        )
        if respuesta_intencion:
            await message.channel.send(respuesta_intencion)
            return True
    except Exception as e:
        print(f"Error procesando intención: {e}")
    return False


async def _procesar_con_gemini(message, texto_limpio: str, usuario_id: str, adjunto):
    """Procesa el mensaje con Gemini como fallback."""
    async with message.channel.typing():
        try:
            respuesta_ia = await _ejecutar_gemini(message, texto_limpio, usuario_id, adjunto)
        except Exception as e:
            print(f"🔥 Error en el procesamiento: {e}")
            respuesta_ia = f"⚠️ Ocurrió un error al procesar tu solicitud: `{e}`"

    await message.channel.send(respuesta_ia)
    return respuesta_ia


async def _ejecutar_gemini(message, texto_limpio: str, usuario_id: str, adjunto) -> str:
    """Ejecuta la llamada a Gemini con el contexto apropiado."""
    if adjunto and not texto_limpio:
        prompt_con_contexto = "El usuario ha enviado una nota de voz consultando sus finanzas o tareas."
    else:
        prompt_con_contexto = texto_limpio

    texto_lower = texto_limpio.lower()

    # Enriquecer contexto si es necesario
    balance, ingresos, gastos, movimientos, presupuestos = obtener_contexto_cacheado(
        usuario_id, lambda: _cargar_contexto_financiero(usuario_id)
    )

    prompt_con_contexto = construir_prompt_con_contexto(
        prompt_con_contexto, texto_lower, usuario_id, adjunto
    )

    # Procesar adjunto si existe
    if adjunto:
        return await procesar_adjunto(message, adjunto, texto_limpio, usuario_id, prompt_con_contexto)
    else:
        return resolve_ai("pensar_respuesta")(prompt_con_contexto)


async def handle_message(message):
    """Handler principal de mensajes."""
    print(f"[ON_MESSAGE] Recibido: {message.content[:50] if message.content else 'sin texto'}")

    usuario_id = str(message.author.id)
    canales_activos.add(message.channel.id)

    # Verificar si debe ignorar
    if _debe_ignorar_mensaje(message, usuario_id):
        return

    # Comandos con prefijo !
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Verificar permisos (mención o conversación activa)
    adjunto = _obtener_adjunto_relevante(message)
    en_conversacion = hay_conversacion_activa(usuario_id, message.channel.id, ahora=time.time())

    if not _verificar_permisos_mencion(message) and not adjunto and not en_conversacion:
        return

    # Limpiar menciones
    texto_limpio = re.sub(r"<@!?\d+>", "", message.content)
    texto_limpio = re.sub(r"<@&\d+>", "", texto_limpio)
    texto_limpio = texto_limpio.strip()
    texto_limpio = completar_consulta_presupuesto(usuario_id, texto_limpio)
    texto_lower = texto_limpio.lower()

    # Saludo rápido
    if await _procesar_saludo(message, usuario_id, texto_lower):
        return

    # Intento determinístico
    if await _procesar_intencion_deterministica(message, texto_limpio, usuario_id):
        registrar_mensaje_conversacion(usuario_id, message.channel.id)
        return

    # Fallback a Gemini
    respuesta_ia = await _procesar_con_gemini(message, texto_limpio, usuario_id, adjunto)

    # Registrar conversación
    registrar_mensaje_conversacion(usuario_id, message.channel.id)

    # TTS si está habilitado
    from bot.events.tts_handler import enviar_tts_si_corresponde
    await enviar_tts_si_corresponde(message, usuario_id, respuesta_ia)

    # Guardar en Firestore
    try:
        guardar_mensaje(usuario_id, str(message.author), texto_limpio)
    except Exception as e:
        print(f"Error guardando mensaje en Firestore: {e}")
