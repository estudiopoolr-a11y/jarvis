import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from modules.ai_brain import pensar_respuesta, pensar_respuesta_audio, procesar_intencion_natural
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

@bot.event
async def on_ready():
    print("==================================================")
    print("Sistemas en línea. JARVIS v3.0 Operativo.")
    print(f"Conectado como: {bot.user}")
    print("==================================================")

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    usuario_id = str(message.author.id)

    # 1. Saludo inteligente con resumen matutino
    if any(s in message.content.lower() for s in ["hola", "buenos días", "jarvis"]):
        tareas = obtener_tareas_pendientes(usuario_id)
        balance, _, _, _ = obtener_balance_financiero(usuario_id)
        saludo_extra = f" Balance actual: ${balance:,.0f}."
        if tareas:
            lista = "\n".join([f"• [{t['prioridad']}] {t['tarea']} (Límite: {t['fecha_limite']})" for t in tareas])
            await message.channel.send(f"Estado del sistema.{saludo_extra}\nTareas pendientes:\n{lista}")
        else:
            await message.channel.send(f"Sistemas activos.{saludo_extra} Sin tareas críticas pendientes.")

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

    await message.channel.send(respuesta_ia)
    guardar_mensaje(str(message.author), usuario_id, message.content, respuesta_ia, tiene_audio=bool(adjunto))

# --- COMANDOS ÚTILES ---
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
        await ctx.send("⚠️ No encontré ninguna tarea pendiente que coincida con ese texto.")

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