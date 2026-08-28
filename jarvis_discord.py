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
    obtener_balance_financiero, obtener_resumen_presupuestos
)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TEMP_DIR = "temp_audios"
if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

# Estado de usuarios en memoria
usuarios_silenciados = {}
usuarios_modo_voz = set()
canales_activos = set()

def generar_audio_respuesta(texto: str, output_path: str) -> str:
    texto_limpio = texto.replace("**", "").replace("*", "").replace("#", "").replace("`", "")
    tts = gTTS(text=texto_limpio[:500], lang='es', slow=False)
    tts.save(output_path)
    return output_path

@bot.event
async def on_ready():
    print("==================================================")
    print("Sistemas en línea. JARVIS v3.0 (Firebase Integrated).")
    print(f"Conectado como: {bot.user}")
    print("==================================================")

@bot.event
async def on_message(message):
    # 1. Evitar bucles ignorando a otros bots
    if message.author.bot:
        return

    canales_activos.add(message.channel.id)
    usuario_id = str(message.author.id)

    # 2. Control de usuarios silenciados (!dormir o !pausar)
    if usuario_id in usuarios_silenciados:
        if datetime.now() < usuarios_silenciados[usuario_id]:
            if message.content.startswith("!"):
                await bot.process_commands(message)
            return
        else:
            del usuarios_silenciados[usuario_id]

    # 3. Comandos con prefijo ! (No consumen cuota de Gemini)
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # 4. Detectar adjuntos de audio y validar mención directas (@Jarvis)
    formatos_audio = ('.ogg', '.mp3', '.wav', '.m4a', '.aac', '.flac')
    adjunto = next((a for a in message.attachments if a.filename.lower().endswith(formatos_audio) or 'audio' in (a.content_type or '')), None)
    es_mencion = bot.user.mentioned_in(message)

    # Si NO etiquetan al bot y NO enviaron audio, se ignora el mensaje (ahorro masivo de recursos)
    if not es_mencion and not adjunto:
        return

    # Limpiar mención del mensaje
    texto_limpio = message.content.replace(f"<@{bot.user.id}>", "").strip()
    texto_lower = texto_limpio.lower()

    # 5. Respuesta local a saludos (Evita llamadas innecesarias a la IA)
    if texto_lower in ["hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches"]:
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

    # 6. Intentar registrar intención automática (Gastos, ingresos o tareas detectadas)
    respuesta_intencion = procesar_intencion_natural(texto_limpio, usuario_id)
    if respuesta_intencion:
        await message.channel.send(respuesta_intencion)
        return

    # 7. INYECCIÓN DE CONTEXTO REAL DE FIREBASE
    # Extrae la información registrada en la base de datos para pasársela a Gemini
    prompt_con_contexto = texto_limpio
    
    palabras_finanzas = ["gasto", "gastos", "finanzas", "balance", "movimiento", "dinero", "registre", "presupuesto"]
    palabras_tareas = ["tarea", "tareas", "pendiente", "pendientes", "recordatorio"]

    if any(k in texto_lower for k in palabras_finanzas):
        balance, ingresos, gastos, movimientos = obtener_balance_financiero(usuario_id)
        presupuestos = obtener_resumen_presupuestos(usuario_id)
        prompt_con_contexto += (
            f"\n\n[CONTEXTO REAL FIREBASE FINANZAS]:\n"
            f"- Balance Neto: ${balance:,.0f}\n"
            f"- Ingresos Totales: ${ingresos:,.0f}\n"
            f"- Gastos Totales: ${gastos:,.0f}\n"
            f"- Movimientos registrados: {movimientos}\n"
            f"- Presupuestos: {presupuestos}"
        )

    if any(k in texto_lower for k in palabras_tareas):
        tareas = obtener_tareas_pendientes(usuario_id)
        prompt_con_contexto += f"\n\n[CONTEXTO REAL FIREBASE TAREAS]: {tareas}"

    # 8. Procesamiento ÚNICO con la API de Gemini
    async with message.channel.typing():
        try:
            if adjunto:
                ruta = os.path.join(TEMP_DIR, adjunto.filename)
                await adjunto.save(ruta)
                respuesta_ia = pensar_respuesta_audio(ruta, prompt_con_contexto)
                if os.path.exists(ruta): os.remove(ruta)
            else:
                respuesta_ia = pensar_respuesta(prompt_con_contexto)
        except Exception as e:
            respuesta_ia = f"⚠️ Error al procesar la solicitud: {e}"

    # Enviar respuesta al canal de Discord
    await message.channel.send(respuesta_ia)
    
    # 9. Generar audio TTS si está activo o si el usuario envió nota de voz
    if usuario_id in usuarios_modo_voz or adjunto:
        ruta_tts = os.path.join(TEMP_DIR, f"tts_{usuario_id}.mp3")
        try:
            generar_audio_respuesta(respuesta_ia, ruta_tts)
            await message.channel.send(file=discord.File(ruta_tts))
        except Exception as e:
            print(f"Error generando audio TTS: {e}")
        finally:
            if os.path.exists(ruta_tts): os.remove(ruta_tts)

    # 10. Guardar la conversación en Firestore (Solo 1 registro por mensaje)
    guardar_mensaje(str(message.author), usuario_id, texto_limpio, respuesta_ia, tiene_audio=bool(adjunto))

# --- COMANDOS DEL BOT (!) ---

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
        await ctx.send("🔇 Modo voz desactivado. Volviendo a respuestas en texto.")
    else:
        usuarios_modo_voz.add(usuario_id)
        await ctx.send("🎙️ Modo voz activado. JARVIS adjuntará respuestas en audio.")

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