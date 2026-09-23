"""bot/events/tts_handler.py - Manejo de Text-to-Speech para respuestas."""
import os
import asyncio
import re

import discord

from bot import TEMP_DIR
from bot.state import usuarios_modo_voz
from bot.services.tts import generar_audio_respuesta

# Peticiones explícitas de respuesta hablada, p. ej. "léeme el resumen" o
# "respóndeme en audio". El modo voz permanente (!voz) sigue funcionando aparte.
_PATRON_VOZ = re.compile(
    r"\b(leeme|léeme|leélo|leelo|en voz|por voz|en audio|nota de voz|dímelo|dimelo)\b",
    re.IGNORECASE,
)


def pide_respuesta_en_voz(texto: str) -> bool:
    """True si el mensaje pide explícitamente una respuesta hablada."""
    return bool(texto and _PATRON_VOZ.search(texto))


async def enviar_tts_si_corresponde(message, usuario_id: str, respuesta_ia: str, forzar: bool = False):
    """Envía audio TTS si el usuario tiene modo voz o lo pidió en este mensaje."""
    if not forzar and usuario_id not in usuarios_modo_voz:
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
