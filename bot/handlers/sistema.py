"""Handlers de comandos Discord de JARVIS."""
from datetime import datetime, timedelta

import discord
import firebase_admin
from google.cloud.firestore_v1.base_query import FieldFilter

from bot import bot
from bot.state import (
    usuarios_silenciados,
    usuarios_modo_voz,
    canales_activos,
    conversaciones_activas,
)
from bot.services.ai import (
    pensar_respuesta,
    pensar_respuesta_audio,
    procesar_intencion_natural,
    analizar_inversion,
    transcribir_audio,
    _API_KEYS,
    _key_index,
)
from bot.services.db import *  # noqa: F403,F401

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

@bot.command(name="estado")
async def estado_sistema(ctx):
    """Muestra el estado del sistema: API keys, conexión, datos."""
    try:
        from bot.services.db import db, inicializar_firebase
        if not firebase_admin._apps:
            inicializar_firebase()

        uid = str(ctx.author.id)

        # Contar datos del usuario
        num_transacciones = 0
        num_presupuestos = 0
        num_tareas = 0
        for _ in db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", uid)).stream():
            num_transacciones += 1
        for _ in db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", uid)).stream():
            num_presupuestos += 1
        for _ in db.collection("tareas").where(filter=FieldFilter("usuario_id", "==", uid)).where(filter=FieldFilter("completada", "==", False)).stream():
            num_tareas += 1

        # Estado de las API keys (informativo)
        key_actual = _key_index + 1
        total_keys = len(_API_KEYS)

        reporte = "🤖 **ESTADO DEL SISTEMA**\n\n"
        reporte += f"✅ **Bot:** Activo y conectado\n"
        reporte += f"✅ **Firebase:** {'Conectado' if firebase_admin._apps else '❌ Desconectado'}\n"
        reporte += f"🔑 **API Keys Gemini:** Usando {key_actual}/{total_keys}\n"
        reporte += f"📊 **Datos personales:**\n"
        reporte += f"   • {num_transacciones} transacciones\n"
        reporte += f"   • {num_presupuestos} presupuestos\n"
        reporte += f"   • {num_tareas} tareas pendientes\n"

        if uid in usuarios_silenciados:
            tiempo_restante = usuarios_silenciados[uid] - datetime.now()
            horas = tiempo_restante.seconds // 3600
            minutos = (tiempo_restante.seconds % 3600) // 60
            reporte += f"💤 **Modo silencio:** {horas}h {minutos}m restantes\n"
        else:
            reporte += f"🔔 **Notificaciones:** Activas\n"

        if uid in usuarios_modo_voz:
            reporte += f"🎙️ **Modo voz:** Activado\n"
        else:
            reporte += f"🔇 **Modo voz:** Desactivado\n"

        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error al obtener estado: {e}")

@bot.command(name="ayuda")
async def mostrar_ayuda(ctx):
    """Muestra la lista completa de comandos disponibles."""
    ayuda = """🤖 **COMANDOS DISPONIBLES - JARVIS**

**💰 FINANZAS**
`!finanzas` - Balance general con últimos movimientos
`!presupuestos` - Estado de todos los presupuestos con barras
`!historial [N]` - Últimas N transacciones (default: 20)
`!buscar <término>` - Busca por categoría o descripción

**📋 TAREAS**
`!tareas` - Lista de tareas pendientes
`!hecho <descripción>` - Marca tarea como completada

**🧠 ANÁLISIS**
`!inversion <TICKER>` - Análisis de acción (ej: AAPL)

**⚙️ CONTROL**
`!estado` - Estado del sistema y API keys
`!voz` - Activa/desactiva respuestas de audio
`!dormir [horas]` - Silencia por X horas (default: 8)
`!pausar [horas]` - Pausa notificaciones (default: 2)
`!ayuda` - Muestra este mensaje
`!borrar confirmar` - Borra TODOS tus datos (requiere confirmación)

**💬 MENCIÓN NATURAL**
También puedes hablarme directamente con:
`@Jarvis hola` - Saludo con balance
`@Jarvis gasté 50000 en mercado` - Registra gasto
`@Jarvis presupuesto Women 300000` - Configura presupuesto
`@Jarvis tarea llamar al médico mañana Alta` - Crea tarea
`@Jarvis ¿cuánto llevo en Women?` - Consulta con IA
`@App` (rol configurado) - Activa el bot

**🎙️ AUDIO**
Puedes enviar notas de voz y las procesaré con IA.
Para respuestas en audio, usa `!voz` primero.

_Sistemas operativos. JARVIS a la espera de instrucciones._"""
    await ctx.send(ayuda)

@bot.command(name="perfil")
async def ver_perfil(ctx):
    """Muestra el perfil del usuario."""
    try:
        uid = str(ctx.author.id)
        from bot.services.db import obtener_perfil
        perfil = obtener_perfil(uid)

        if not perfil:
            await ctx.send("""👤 **PERFIL**

No tienes perfil configurado. Puedes decirme:
`@Jarvis mi nombre es Daniel`
`@Jarvis vivo en Bogotá`
`@Jarvis tengo 25 años`""")
            return

        reporte = "👤 **TU PERFIL**\n\n"
        for k, v in perfil.items():
            if k != "preferencias":
                reporte += f"• **{k.capitalize()}**: {v}\n"
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")
