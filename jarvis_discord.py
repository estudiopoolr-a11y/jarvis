import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from gtts import gTTS
from dotenv import load_dotenv

from modules.ai_brain import (
    pensar_respuesta, pensar_respuesta_audio, procesar_intencion_natural, 
    analizar_inversion
)
from modules.database import (
    guardar_mensaje, obtener_tareas_pendientes, marcar_tarea_completada, 
    obtener_balance_financiero
)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TEMP_DIR = "temp_audios"
if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

# Estado de usuarios: silenciados temporalmente y preferencia de respuesta por voz
usuarios_silenciados = {} # {usuario_id: datetime_hasta}
usuarios_modo_voz = set()  # {usuario_id}
canales_activos = set()     # Guardar canales para notificaciones periódicas

def generar_audio_respuesta(texto: str, output_path: str) -> str:
    texto_limpio = texto.replace("**", "").replace("*", "").replace("#", "").replace("`", "")
    tts = gTTS(text=texto_limpio[:500], lang='es', slow=False) # Límite para evitar audios extensos
    tts.save(output_path)
    return output_path

@bot.event
async def on_ready():
    print("==================================================")
    print("Sistemas en línea. JARVIS v3.0 Operativo.")
    print(f"Conectado como: {bot.user}")
    print("==================================================")
    if not bucle_notificaciones.is_running():
        bucle_notificaciones.start()

@tasks.loop(minutes=30)
async def bucle_notificaciones():
    ahora = datetime.now()
    for canal_id in list(canales_activos):
        canal = bot.get_channel(canal_id)
        if canal:
            # Notificación de control de estado básica
            print(f"[JARVIS Auto-Check {ahora.strftime('%H:%M')}]: Canal {canal_id} activo.")

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    canales_activos.add(message.channel.id)
    usuario_id = str(message.author.id)

    # Verificar si el usuario tiene las notificaciones pausadas/dormidas
    if usuario_id in usuarios_silenciados:
        if datetime.now() < usuarios_silenciados[usuario_id]:
            if message.content.startswith("!"):
                await bot.process_commands(message)
            return
        else:
            del usuarios_silenciados[usuario_id]

    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # 1. Saludo inteligente con resumen matutino
    if any(s in message.content.lower() for s in ["hola", "buenos días", "jarvis"]):
        tareas = obtener_tareas_pendientes(usuario_id)
        balance, _, _, _ = obtener_balance_financiero(usuario_id)
        saludo_extra = f" Balance actual: ${balance:,.0f}."
        if tareas:
            lista = "\n".join([f"• [{t['prioridad']}] {t['tarea']} (Vence: {t['fecha_limite']})" for t in tareas])
            msg = f"Sistemas activos.{saludo_extra}\nTareas pendientes:\n{lista}"
        else:
            msg = f"Sistemas activos.{saludo_extra} Sin tareas críticas pendientes."
        await message.channel.send(msg)
        return

    # 2. Detección automática de intenciones (Gastos, Ingresos, Tareas, Presupuestos)
    respuesta_intencion = procesar_intencion_natural(message.content, usuario_id)
    if respuesta_intencion:
        await message.channel.send(respuesta_intencion)
        return

    # 3. Procesamiento de Audios o Texto Normal
    formatos_audio = ('.ogg', '.mp3', '.wav', '.m4a', '.aac', '.flac')
    adjunto = next((a for a in message.attachments if a.filename.lower().endswith(formatos_audio) or 'audio' in (a.content_type or '')), None)

    async with message.channel.typing():
        if adjunto:
            ruta = os.path.join(TEMP_DIR, adjunto.filename)
            await adjunto.save(ruta)
            respuesta_ia = pensar_respuesta_audio(ruta, message.content)
            if os.path.exists(ruta): os.remove(ruta)
        else:
            respuesta_ia = pensar_respuesta(message.content)

    # Enviar texto o nota de voz según la preferencia activa del usuario
    await message.channel.send(respuesta_ia)
    
    if usuario_id in usuarios_modo_voz or adjunto:
        ruta_tts = os.path.join(TEMP_DIR, f"tts_{usuario_id}.mp3")
        try:
            generar_audio_respuesta(respuesta_ia, ruta_tts)
            await message.channel.send(file=discord.File(ruta_tts))
        except Exception as e:
            print(f"Error generando audio TTS: {e}")
        finally:
            if os.path.exists(ruta_tts): os.remove(ruta_tts)

    guardar_mensaje(str(message.author), usuario_id, message.content, respuesta_ia, tiene_audio=bool(adjunto))

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
    await ctx.send(f"⏸️ Notificaciones y monitoreo silenciados por **{horas} horas**.")

@bot.command(name="voz")
async def alternar_modo_voz(ctx):
    usuario_id = str(ctx.author.id)
    if usuario_id in usuarios_modo_voz:
        usuarios_modo_voz.remove(usuario_id)
        await ctx.send("🔇 Modo voz desactivado. Volviendo a respuestas únicamente en texto.")
    else:
        usuarios_modo_voz.add(usuario_id)
        await ctx.send("🎙️ Modo voz activado. JARVIS adjuntará respuestas de audio a tus mensajes.")

@bot.command(name="tareas")
async def ver_tareas(ctx):
    tareas = obtener_tareas_pendientes(str(ctx.author.id))
    if not tareas:
        await ctx.send("No hay tareas pendientes en cola.")
    else:
        lista = "\n".join([f"• **[{t['prioridad']}]** {t['tarea']} *(Vence: {t['fecha_limite']})*" for t in tareas])
        await ctx.send(f"📋 **Lista de Tareas Activas:**\n{lista}")

@bot.command(name="hecho")
async def terminar_tarea(ctx, *, texto: str):
    completada = marcar_tarea_completada(str(ctx.author.id), texto)
    if completada:
        await ctx.send(f"✔️ Tarea completada y archivada: *'{completada}'*.")
    else:
        await ctx.send("⚠️ No encontré ninguna tarea pendiente que coincida.")

@bot.command(name="finanzas")
async def ver_finanzas(ctx):
    balance, ingresos, gastos, movimientos = obtener_balance_financiero(str(ctx.author.id))
    reporte = f"📊 **BALANCE FINANCIERO GENERAL** 📊\n\n"
    reporte += f"• **Ingresos Totales:** +${ingresos:,.0f}\n"
    reporte += f"• **Gastos Totales:** -${gastos:,.0f}\n"
    reporte += f"• **Balance Neto:** ${balance:,.0f}\n\n"
    if movimientos:
        reporte += "Últimos movimientos:\n" + "\n".join(movimientos[-5:])
    await ctx.send(reporte)

if __name__ == "__main__":
    if TOKEN: bot.run(TOKEN)