"""bot/events.py - Eventos principales del bot Discord JARVIS."""

import asyncio
import os
import re
import time
from datetime import datetime

import discord

from bot import bot, ALLOWED_ROLE_IDS, TEMP_DIR
from bot.state import (
    usuarios_silenciados,
    usuarios_modo_voz,
    canales_activos,
    conversaciones_activas,
    _last_msg_time,
    _CONVERSACION_TTL,
    _CONVERSACION_MAX_MENSAJES,
    _COOLDOWN_SEGUNDOS,
    obtener_contexto_cacheado,
    limpiar_conversaciones_expiradas,
    hay_conversacion_activa,
    registrar_mensaje_conversacion,
    verificar_cooldown,
)
from bot.services.ai import (
    pensar_respuesta,
    pensar_respuesta_audio,
    procesar_intencion_natural,
    analizar_inversion,
    transcribir_audio,
)
from bot.services.db import (
    guardar_mensaje,
    obtener_tareas_pendientes,
    obtener_balance_financiero,
    obtener_resumen_presupuestos,
)
from bot.services.tts import generar_audio_respuesta


@bot.event
async def on_ready():
    print("==================================================")
    print("Sistemas en línea. JARVIS v3.0 Operativo.")
    print(f"Conectado como: {bot.user}")
    print("==================================================")


@bot.event
async def on_message(message):
    print(f"[ON_MESSAGE] Recibido: {message.content[:50] if message.content else 'sin texto'}")

    # 1. Ignorar a cualquier bot
    if message.author.bot:
        return

    canales_activos.add(message.channel.id)
    usuario_id = str(message.author.id)

    # 2. Control de usuarios silenciados
    if usuario_id in usuarios_silenciados:
        if datetime.now() < usuarios_silenciados[usuario_id]:
            if message.content.startswith("!"):
                await bot.process_commands(message)
            return
        else:
            del usuarios_silenciados[usuario_id]

    # 3. Comandos con prefijo !
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # 4. Cooldown anti-spam rápido
    ahora = time.time()
    if _last_msg_time.get(usuario_id, 0) >= ahora - _COOLDOWN_SEGUNDOS:
        return
    _last_msg_time[usuario_id] = ahora

    # 5. Mención, adjunto o conversación activa requerido
    formatos_audio = (".ogg", ".mp3", ".wav", ".m4a", ".aac", ".flac")
    formatos_txt = (".txt", ".csv")

    adjunto = next(
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

    es_mencion_usuario = bot.user.mentioned_in(message)
    es_mencion_rol = any(role.id in ALLOWED_ROLE_IDS for role in message.role_mentions)

    # Mantener TTL de conversaciones
    en_conversacion = hay_conversacion_activa(usuario_id, message.channel.id, ahora=time.time())

    if not es_mencion_usuario and not es_mencion_rol and not adjunto and not en_conversacion:
        return

    # 6. Limpiar menciones de usuarios y roles (<@ID>, <@!ID>, <@&ID>)
    texto_limpio = re.sub(r"<@!?\d+>", "", message.content)
    texto_limpio = re.sub(r"<@&\d+>", "", texto_limpio)
    texto_limpio = texto_limpio.strip()
    texto_lower = texto_limpio.lower()

    # 7. Saludo local rápido
    if texto_lower in [
        "hola",
        "buenos dias",
        "buenos días",
        "buenas tardes",
        "buenas noches",
    ]:
        try:
            balance, *_ = obtener_contexto_cacheado(usuario_id, lambda: _cargar_contexto_financiero(usuario_id))
            saludo_extra = f" Balance actual: ${balance:,.0f}."
            await message.channel.send(f"Sistemas activos.{saludo_extra} Sin tareas críticas pendientes.")
        except Exception as e:
            await message.channel.send(f"⚠️ Error cargando datos locales: {e}")
        return

    # 8. Intento de registro automático de intención
    try:
        respuesta_intencion = procesar_intencion_natural(texto_limpio, usuario_id)
        if respuesta_intencion:
            await message.channel.send(respuesta_intencion)
            return
    except Exception as e:
        print(f"Error procesando intención: {e}")

    # 9. Procesamiento con Gemini
    async with message.channel.typing():
        try:
            if adjunto and not texto_limpio:
                prompt_con_contexto = "El usuario ha enviado una nota de voz consultando sus finanzas o tareas."
            else:
                prompt_con_contexto = texto_limpio

            palabras_finanzas = [
                "gasto",
                "gastos",
                "finanzas",
                "balance",
                "movimiento",
                "dinero",
                "registre",
                "presupuesto",
            ]
            palabras_tareas = [
                "tarea",
                "tareas",
                "pendiente",
                "pendientes",
                "recordatorio",
            ]

            balance, ingresos, gastos, movimientos, presupuestos = obtener_contexto_cacheado(
    usuario_id, lambda: _cargar_contexto_financiero(usuario_id)
)

            if any(k in texto_lower for k in palabras_finanzas) or bool(adjunto):
                movs = [
                    f"{t.get('tipo','?')[:1].upper()}:${t.get('monto',0):,.0f}@{t.get('categoria','?')[:5]}"
                    for t in movimientos[-3:]
                ]
                prompt_con_contexto += (
                    f"\n[JARVIS] Bal=${balance:,.0f} Ing=${ingresos:,.0f} Gas=${gastos:,.0f} | Mov:{movs} | Pres:{presupuestos}\n"
                    "Usa SOLO estos datos."
                )

            if any(k in texto_lower for k in palabras_tareas) or bool(adjunto):
                tareas = obtener_tareas_pendientes(usuario_id)
                prompt_con_contexto += f"\nTareas:{len(tareas)}"

            if adjunto:
                ruta = os.path.join(TEMP_DIR, adjunto.filename)
                await adjunto.save(ruta)

                es_txt = adjunto.filename.lower().endswith((".txt", ".csv")) or (adjunto.content_type or "").startswith("text/")

                if es_txt:
                    try:
                        from modules.importador_txt import importar_texto
                        from modules import db as dbmod

                        with open(ruta, "r", encoding="utf-8-sig", errors="replace") as f:
                            texto_archivo = f.read()

                        db = dbmod.inicializar_firebase()
                        if not db:
                            respuesta_ia = "⚠️ No pude conectar con Firebase para importar el TXT."
                        else:
                            respuesta_ia = importar_texto(usuario_id, texto_archivo, db, anio_default=2026)
                    except Exception as txt_error:
                        respuesta_ia = f"⚠️ No pude importar el TXT: `{txt_error}`"
                else:
                    texto_transcrito = transcribir_audio(ruta)

                    if texto_transcrito:
                        respuesta_ia = procesar_intencion_natural(texto_transcrito, usuario_id)
                        if not respuesta_ia:
                            respuesta_ia = pensar_respuesta(texto_transcrito)
                    else:
                        prompt_audio = prompt_con_contexto if texto_limpio else ""
                        respuesta_ia = pensar_respuesta_audio(ruta, prompt_audio, usuario_id)

                if os.path.exists(ruta):
                    os.remove(ruta)
            else:
                respuesta_ia = pensar_respuesta(prompt_con_contexto)

        except Exception as e:
            print(f"🔥 Error en el procesamiento: {e}")
            respuesta_ia = f"⚠️ Ocurrió un error al procesar tu solicitud: `{e}`"

    # Enviar respuesta
    await message.channel.send(respuesta_ia)

    # Marcar conversación activa
    registrar_mensaje_conversacion(usuario_id, message.channel.id)

    # Solo TTS si el usuario activó modo voz específicamente
    if usuario_id in usuarios_modo_voz:
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

    # Guardar en Firestore
    try:
        guardar_mensaje(usuario_id, str(message.author), texto_limpio)
    except Exception as e:
        print(f"Error guardando mensaje en Firestore: {e}")
