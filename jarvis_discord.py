import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from gtts import gTTS
from dotenv import load_dotenv
import time

from modules.ai_brain import (
    pensar_respuesta, pensar_respuesta_audio, procesar_intencion_natural,
    analizar_inversion, _API_KEYS, _key_index
)
from modules.database import (
    guardar_mensaje, obtener_tareas_pendientes, marcar_tarea_completada,
    obtener_balance_financiero, obtener_resumen_presupuestos,
    limpiar_datos_usuario
)
import firebase_admin
from google.cloud.firestore_v1.base_query import FieldFilter

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

# IDs de roles que pueden invocar al bot (configurable aqui)
ALLOWED_ROLE_IDS = [1537704466407497738]  # ID del rol "App" u otro que mencionas

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

    # 5. Mención o adjunto requerido
    formatos_audio = ('.ogg', '.mp3', '.wav', '.m4a', '.aac', '.flac')
    adjunto = next((a for a in message.attachments if a.filename.lower().endswith(formatos_audio) or 'audio' in (a.content_type or '')), None)

    # Detectar menciones de usuario o de roles permitidos
    es_mencion_usuario = bot.user.mentioned_in(message)
    es_mencion_rol = any(role.id in ALLOWED_ROLE_IDS for role in message.role_mentions)

    print(f"[DEBUG] Mencion usuario: {es_mencion_usuario}, Mencion rol: {es_mencion_rol}, Contenido: {message.content[:50]}")

    if not es_mencion_usuario and not es_mencion_rol and not adjunto:
        return

    # 6. Limpiar menciones de usuarios y roles (<@ID>, <@!ID>, <@&ID>)
    import re
    texto_limpio = re.sub(r'<@!?\d+>', '', message.content)
    texto_limpio = re.sub(r'<@&\d+>', '', texto_limpio)
    texto_limpio = texto_limpio.strip()
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
        guardar_mensaje(usuario_id, str(message.author), texto_limpio)
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
            # Formatear movimientos (que son diccionarios) a strings legibles
            ultimos = []
            for t in movimientos[-10:]:
                tipo = t.get("tipo", "gasto")
                monto = t.get("monto", 0)
                cat = t.get("categoria", "General")
                emoji = "🟢" if tipo == "ingreso" else "🔴"
                signo = "+" if tipo == "ingreso" else "-"
                ultimos.append(f"{emoji} {signo}${float(monto):,.0f} en {cat}")
            reporte += "**Últimos movimientos:**\n" + "\n".join(ultimos)
        else:
            reporte += "Sin movimientos registrados."
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error al obtener finanzas: {e}")

# ===== NUEVOS COMANDOS =====

@bot.command(name="presupuestos")
async def ver_presupuestos(ctx):
    """Muestra el estado de todos los presupuestos con barras de progreso."""
    try:
        from modules.database import inicializar_firebase
        if not firebase_admin._apps:
            inicializar_firebase()

        from modules.database import db
        uid = str(ctx.author.id)

        # Obtener presupuestos
        presupuestos = {}
        for doc in db.collection("presupuestos").stream():
            d = doc.to_dict()
            if d.get("usuario_id") == uid:
                presupuestos[d.get("categoria")] = float(d.get("limite", 0))

        # Obtener gastos por categoría
        gastos = {}
        for doc in db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", uid)).stream():
            data = doc.to_dict()
            if data.get("tipo") == "gasto":
                cat = data.get("categoria", "General")
                gastos[cat] = gastos.get(cat, 0) + float(data.get("monto", 0))

        if not presupuestos:
            await ctx.send("⚠️ No tienes presupuestos configurados. Usa `@Jarvis presupuesto Categoría Monto` para crear uno.")
            return

        reporte = "🎯 **ESTADO DE PRESUPUESTOS**\n\n"
        for cat, limite in presupuestos.items():
            gastado = gastos.get(cat, 0)
            pct = min(100, int((gastado / limite) * 100)) if limite > 0 else 0
            barra_llena = int(pct / 10)
            barra_vacia = 10 - barra_llena
            barra = "█" * barra_llena + "░" * barra_vacia

            if pct >= 100:
                estado = "🔴 EXCEDIDO"
                color_emoji = "🚨"
            elif pct >= 90:
                estado = "🟠 CRÍTICO"
                color_emoji = "⚠️"
            elif pct >= 80:
                estado = "🟡 ADVERTENCIA"
                color_emoji = "⚠️"
            else:
                estado = "🟢 OK"
                color_emoji = "✅"

            restante = limite - gastado
            reporte += f"{color_emoji} **{cat}** {estado}\n"
            reporte += f"   {barra} {pct}%\n"
            reporte += f"   Gastado: ${gastado:,.0f} / ${limite:,.0f}\n"
            reporte += f"   Restante: ${max(0, restante):,.0f}\n\n"

        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error al obtener presupuestos: {e}")

@bot.command(name="historial")
async def ver_historial(ctx, cantidad: int = 20):
    """Muestra las últimas N transacciones (por defecto 20)."""
    try:
        from modules.database import db
        uid = str(ctx.author.id)

        docs = list(db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", uid)).stream())

        if not docs:
            await ctx.send("📋 Sin transacciones registradas.")
            return

        # Ordenar por fecha descendente (asumimos que hay campo fecha)
        docs_ordenados = sorted(docs, key=lambda d: d.to_dict().get("fecha", ""), reverse=True)
        ultimos = docs_ordenados[:min(cantidad, len(docs_ordenados))]

        reporte = f"📜 **ÚLTIMAS {len(ultimos)} TRANSACCIONES**\n\n"
        for doc in ultimos:
            t = doc.to_dict()
            tipo = t.get("tipo", "gasto")
            monto = t.get("monto", 0)
            cat = t.get("categoria", "General")
            desc = t.get("descripcion", "")
            fecha = t.get("fecha", "")
            emoji = "🟢" if tipo == "ingreso" else "🔴"
            signo = "+" if tipo == "ingreso" else "-"
            desc_str = f" - {desc}" if desc else ""
            reporte += f"{emoji} {signo}${float(monto):,.0f} en **{cat}**{desc_str}\n"
            reporte += f"   📅 {fecha}\n"

        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error al obtener historial: {e}")

@bot.command(name="buscar")
async def buscar_categoria(ctx, *, termino: str):
    """Busca todas las transacciones que coincidan con el término (categoría o descripción)."""
    try:
        from modules.database import db
        uid = str(ctx.author.id)
        termino_lower = termino.lower()

        resultados = []
        for doc in db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", uid)).stream():
            t = doc.to_dict()
            cat = str(t.get("categoria", "")).lower()
            desc = str(t.get("descripcion", "")).lower()

            if termino_lower in cat or termino_lower in desc:
                resultados.append(t)

        if not resultados:
            await ctx.send(f"🔍 No encontré transacciones que coincidan con **'{termino}'**.")
            return

        total_gastos = sum(float(t.get("monto", 0)) for t in resultados if t.get("tipo") == "gasto")
        total_ingresos = sum(float(t.get("monto", 0)) for t in resultados if t.get("tipo") == "ingreso")

        reporte = f"🔍 **RESULTADOS PARA '{termino}'** ({len(resultados)} transacciones)\n\n"
        reporte += f"💸 Total gastos: ${total_gastos:,.0f}\n"
        reporte += f"💰 Total ingresos: ${total_ingresos:,.0f}\n\n"
        reporte += "**Detalle:**\n"

        for t in resultados[:15]:  # Limitar a 15 para no saturar
            tipo = t.get("tipo", "gasto")
            monto = t.get("monto", 0)
            cat = t.get("categoria", "General")
            desc = t.get("descripcion", "")
            emoji = "🟢" if tipo == "ingreso" else "🔴"
            signo = "+" if tipo == "ingreso" else "-"
            desc_str = f" - {desc}" if desc else ""
            reporte += f"{emoji} {signo}${float(monto):,.0f} en {cat}{desc_str}\n"

        if len(resultados) > 15:
            reporte += f"\n_...y {len(resultados) - 15} más_"

        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error en búsqueda: {e}")

@bot.command(name="estado")
async def estado_sistema(ctx):
    """Muestra el estado del sistema: API keys, conexión, datos."""
    try:
        from modules.database import db, inicializar_firebase
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

@bot.command(name="borrar")
async def borrar_datos(ctx, *, confirmacion: str = None):
    """Borra todos los datos del usuario. Requiere confirmación."""
    if confirmacion != "confirmar":
        await ctx.send("⚠️ **¿Estás seguro?**\n\nEsta acción eliminará TODAS tus transacciones, presupuestos y tareas.\nPara confirmar, escribe: `!borrar confirmar`")
        return

    try:
        resultado = limpiar_datos_usuario(str(ctx.author.id))
        total = sum(resultado.values())

        if total == 0:
            await ctx.send("ℹ️ No hay datos para borrar.")
        else:
            msg = "🗑️ **Datos eliminados correctamente:**\n"
            if resultado["transacciones"] > 0:
                msg += f"   • {resultado['transacciones']} transacciones\n"
            if resultado["presupuestos"] > 0:
                msg += f"   • {resultado['presupuestos']} presupuestos\n"
            if resultado["tareas"] > 0:
                msg += f"   • {resultado['tareas']} tareas\n"
            msg += "\n✅ Base de datos limpia. Puedes recargar datos con el prompt masivo."
            await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"⚠️ Error borrando datos: {e}")

if __name__ == "__main__":
    if TOKEN: bot.run(TOKEN)