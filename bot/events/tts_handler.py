"""bot/events/tts_handler.py - Manejo de Text-to-Speech para respuestas."""
import os
import asyncio

import discord

from bot import TEMP_DIR
from bot.state import usuarios_modo_voz
from bot.services.tts import generar_audio_respuesta


async def enviar_tts_si_corresponde(message, usuario_id: str, respuesta_ia: str):
    """Envía audio TTS si el usuario tiene activado el modo voz."""
    if usuario_id not in usuarios_modo_voz:
        return

    ruta_tts = os.path.join(TEMP_DIR, f"tts_{usuario_id}.mp3")
    try:
        exito = await asyncio.to_thread(generar_audio_respuesta, respuesta_ia, ruta_tts)
        if exito and os.path.exists(ruta_tts):
            await message.channel.send(file=discord.File(ruta_tts))
    except Exception as e:
        print(f"Error generando audio TTS: {e}")
    finally:
        if os.path.exists(ruta_tts):
            os.remove(ruta_tts)
