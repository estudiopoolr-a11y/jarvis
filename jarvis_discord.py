import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from gtts import gTTS
from dotenv import load_dotenv
import time

from modules.ai_brain import (
    pensar_respuesta, pensar_respuesta_audio, procesar_intencion_natural,
    analizar_inversion
)
from modules.database import (
    guardar_mensaje, obtener_tareas_pendientes, marcar_tarea_completada,
    obtener_balance_financiero, obtener_resumen_presupuestos
)

# Estados en memoria
usuarios_silenciados = {}
usuarios_modo_voz = set()
canales_activos = set()
# Cache para contexto financiero
_finanzas_cache = {}
_CACHE_TTL = 30  # segundos

# Cooldown anti-spam
_last_msg_time = {}
_COOLDOWN_SEGUNDOS = 3

def obtener_contexto_cacheado(usuario_id):
    """Devuelve balance, ingresos, gastos, movimientos, presupuestos cacheado o consulta si no hay cache o expiró."""
    ahora = time.time()
    if usuario_id in _finanzas_cache:
        datos, timestamp = _finanzas_cache[usuario_id]
        if ahora - timestamp < _CACHE_TTL:
            return datos
    # Si no hay cache o expiró, consulta y guarda
    balance, ingresos, gastos, movimientos = obtener_balance_financiero(usuario_id)
    presupuestos = obtener_resumen_presupuestos(usuario_id)
    datos = (balance, ingresos, gastos, movimientos, presupuestos)
    _finanzas_cache[usuario_id] = (datos, ahora)
    return datos

def generar_audio_respuesta(texto: str, output_path: str) -> str:
    texto_limpio = texto.replace("**", "").replace("*", "").replace("#", "").replace("`", "")
    tts = gTTS(text=texto_limpio[:500], lang='es', slow=False)
    tts.save(output_path)
    return output_path

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TEMP_DIR = "temp_audios"
if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

@bot.event
async def on_ready():
    print("==================================================")
    print("Sistemas en línea. JARVIS v3.0 Operativo.")
    print(f"Conectado como: {bot.user}")
    print("==================================================")

@bot.event
async def on_message(message):
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

    # 5. Mención o adjunto requerido
    formatos_audio = ('.ogg', '.mp3', '.wav', '.m4a', '.aac', '.flac')
    adjunto = next((a for a in message.attachments if a.filename.lower().endswith(formatos_audio) or 'audio' in (a.content_type or '')), None)
    es_mencion = bot.user.mentioned_in(message)

    print(f"[DEBUG] Mencion detectada: {es_mencion}, Contenido: {message.content[:50]}")

    if not es_mencion and not adjunto:
        return

    # 6. Limpiar menciones (<@ID> y <@!ID>)
    texto_limpio = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    texto_lower = texto_limpio.lower()

    # 7. Saludo local rápido
    if texto_lower in ["hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches"]:
        try:
            # Usar cache para saludo
            balance, _, _, _, _ = obtener_contexto_cacheado(usuario_id)
            saludo_extra = f" Balance actual: ${balance:,.0f}."
            # Para saludo solo necesitamos balance, no tasks
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
            # Si es audio sin texto, dar instrucción base
            if adjunto and not texto_limpio:
                prompt_con_contexto = "El usuario ha enviado una nota de voz consultando sus finanzas o tareas."
            else:
                prompt_con_contexto = texto_limpio

            # Detectar tipos de consulta
            palabras_finanzas = ["gasto", "gastos", "finanzas", "balance", "movimiento", "dinero", "registre", "presupuesto"]
            palabras_tareas = ["tarea", "tareas", "pendiente", "pendientes", "recordatorio"]

            # Usar cache para contexto de finanzas/tareas
            balance, ingresos, gastos, movimientos, presupuestos = obtener_contexto_cacheado(usuario_id)

            # Inyectar contexto si es necesario
            if any(k in texto_lower for k in palabras_finanzas) or bool(adjunto):
                prompt_con_contexto += (
                    f"\n\n[INFORMACIÓN REAL DE FIREBASE - FINANZAS DEL USUARIO]:\n"
                    f"- Balance Neto: ${balance:,.0f}\n"
                    f"- Ingresos Totales: ${ingresos:,.0f}\n"
                    f"- Gastos Totales: ${gastos:,.0f}\n"
                    f"- Movimientos (últimos 10): {movimientos[-10:] if movimientos else []}\n"
                    f"- Presupuestos: {presupuestos}\n"
                    f"INSTRUCCIÓN CRÍTICA: RESPONDE ÚNICAMENTE con datos de la lista anterior. NO inventes montos, categorías ni fechas."
                )

            if any(k in texto_lower for k in palabras_tareas) or bool(adjunto):
                tareas = obtener_tareas_pendientes(usuario_id)
                prompt_con_contexto += f"\n\n[INFORMACIÓN REAL DE FIREBASE - TAREAS DEL USUARIO]: {tareas}"

            # Llamada a la IA con contexto limitado
            if adjunto:
                ruta = os.path.join(TEMP_DIR, adjunto.filename)
                await adjunto.save(ruta)
                respuesta_ia = pensar_respuesta_audio(ruta, prompt_con_contexto)
                if os.path.exists(ruta): os.remove(ruta)
            else:
                respuesta_ia = pensar_respuesta(prompt_con_contexto)

        except Exception as e:
            print(f"🔥 Error en el procesamiento: {e}")
            respuesta_ia = f"⚠️ Ocurrió un error al procesar tu solicitud: `{e}`"

    # Enviar respuesta
    await message.channel.send(respuesta_ia)

    # Solo TTS si el usuario activó modo voz específicamente, no si solo envió audio
    if usuario_id in usuarios_modo_voz:
        ruta_tts = os.path.join(TEMP_DIR, f"tts_{usuario_id}.mp3")
        try:
            generar_audio_respuesta(respuesta_ia, ruta_tts)
            await message.channel.send(file=discord.File(ruta_tts))
        except Exception as e:
            print(f"Error generando audio TTS: {e}")
        finally:
            if os.path.exists(ruta_tts): os.remove(ruta_tts)

    # Guardar en Firestore
    try:
        guardar_mensaje(str(message.author), usuario_id, texto_limpio, respuesta_ia, tiene_audio=bool(adjunto))
    except Exception as e:
        print(f"Error guardando mensaje en Firestore: {e}")

# --- COMANDOS DEL BOT ---

@bot.command(name="inversion")
async def analizar_ticker(ctx, ticker: str):
    async with ctx.typing():
        resultado = analizar_inversion(ticker)
    await ctx.send(resultado)

@bot.command(name="dormir")
async def modo_dormir(ctx, horas: int = 8):
    usuario_id = str(ctx.author.id)
    usuarios_silenciados[usuario_id] = datetime.now() + timedelta(hours=horas)
    tareas = obtener_tareas_pendientes(usuario_id)
    
    msg = f"💤 Modo descanso activado por **{horas} horas**. Notificaciones silenciadas.\n"
    if tareas:
        lista = "\n".join([f"• [{t['prioridad']}] {t['tarea']} (Vence: {t['fecha_limite']})" for t in tareas])
        msg += f"\n**Pendientes obligatorios antes de reiniciar operaciones:**\n{lista}"
    else:
        msg += "\nNo dejas tareas pendientes. Descansa."
    
    await ctx.send(msg)

@bot.command(name="pausar")
async def pausar_notificaciones(ctx, horas: int = 2):
    usuario_id = str(ctx.author.id)
    usuarios_silenciados[usuario_id] = datetime.now() + timedelta(hours=horas)
    await ctx.send(f"⏸️ Notificaciones silenciadas por **{horas} horas**.")

@bot.command(name="voz")
async def alternar_modo_voz(ctx):
    usuario_id = str(ctx.author.id)
    if usuario_id in usuarios_modo_voz:
        usuarios_modo_voz.remove(usuario_id)
        await ctx.send("🔇 Modo voz desactivado. Volviendo a respuestas únicamente en texto.")
    else:
        usuarios_modo_voz.add(usuario_id)
        await ctx.send("🎙️ Modo voz activado. JARVIS adjuntará respuestas de audio.")

@bot.command(name="tareas")
async def ver_tareas(ctx):
    try:
        tareas = obtener_tareas_pendientes(str(ctx.author.id))
        if not tareas:
            await ctx.send("No hay tareas pendientes en cola.")
        else:
            lista = "\n".join([f"• **[{t['prioridad']}]** {t['tarea']} *(Vence: {t['fecha_limite']})*" for t in tareas])
            await ctx.send(f"📋 **Lista de Tareas Activas:**\n{lista}")
    except Exception as e:
        await ctx.send(f"⚠️ Error al obtener tareas: {e}")

@bot.command(name="hecho")
async def terminar_tarea(ctx, *, texto: str):
    try:
        completada = marcar_tarea_completada(str(ctx.author.id), texto)
        if completada:
            await ctx.send(f"✔️ Tarea completada y archivada: *'{completada}'*.")
        else:
            await ctx.send("⚠️ No encontré ninguna tarea pendiente que coincida.")
    except Exception as e:
        await ctx.send(f"⚠️ Error marcando tarea: {e}")

@bot.command(name="finanzas")
async def ver_finanzas(ctx):
    try:
        balance, ingresos, gastos, movimientos = obtener_balance_financiero(str(ctx.author.id))
        reporte = f"📊 **BALANCE FINANCIERO GENERAL** 📊\n\n"
        reporte += f"• **Ingresos Totales:** +${ingresos:,.0f}\n"
        reporte += f"• **Gastos Totales:** -${gastos:,.0f}\n"
        reporte += f"• **Balance Neto:** ${balance:,.0f}\n\n"
        if movimientos:
            reporte += "Últimos movimientos:\n" + "\n".join(movimientos[-10:])
        else:
            reporte += "Sin movimientos registrados."
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error al obtener finanzas: {e}")

if __name__ == "__main__":
    if TOKEN: bot.run(TOKEN)