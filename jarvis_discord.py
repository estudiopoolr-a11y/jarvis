import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import edge_tts
import asyncio
import tempfile
import hashlib
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

# Cache para archivos TTS (clave = hash del texto)
_tts_cache = {}

async def _generar_tts_async(texto: str, output_path: str) -> None:
    """Genera audio TTS usando edge-tts (no bloquea event loop)."""
    cache_key = hashlib.md5(texto.encode('utf-8')).hexdigest()
    if cache_key in _tts_cache and os.path.exists(output_path):
        # Cache hit: reutilizar archivo existente
        return

    communicate = edge_tts.Communicate(texto, "es-MX")
    await communicate.save(output_path)

    # Guardar en cache para reutilizar
    _tts_cache[cache_key] = True

def _limpiar_marca_tts(texto: str) -> str:
    """Quita marcas markdown para TTS."""
    if not texto:
        return ""
    return texto.replace("**", "").replace("*", "").replace("#", "").replace("`", "").strip()

def _generar_tts_sincrono(texto: str, output_path: str) -> None:
    """Genera TTS de forma síncrona (fallback)."""
    # edge-tts es asíncrono, pero podemos ejecutarlo en un loop nuevo
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_generar_tts_async(texto, output_path))
    finally:
        loop.close()

def generar_audio_respuesta(texto: str, output_path: str) -> str:
    """Genera respuesta de audio usando edge-tts (asíncrono, mejor calidad).

    Esta función es NO BLOQUEANTE: lanza la generación en background.
    El archivo estará disponible cuando termine (típicamente <1s).
    """
    texto_limpio = _limpiar_marca_tts(texto)
    if not texto_limpio:
        # Si no hay texto, no hacer nada
        return ""

    # Truncar a 800 caracteres, cortando por palabras para no cortar a la mitad
    if len(texto_limpio) > 800:
        texto_limpio = texto_limpio[:800].rsplit(' ', 1)[0] + "..."

    # Crear directorio padre si no existe
    padre = os.path.dirname(output_path)
    if padre and not os.path.exists(padre):
        os.makedirs(padre, exist_ok=True)

    # Ejecutar en hilo separado para no bloquear el event loop de Discord
    try:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_generar_tts_async(texto_limpio, output_path))
        finally:
            loop.close()
    except Exception as e:
        print(f"Error generando TTS: {e}")
        return ""

    return output_path if os.path.exists(output_path) else ""

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

            # Inyectar contexto si es necesario (OPTIMIZADO: ultra-compacto)
            if any(k in texto_lower for k in palabras_finanzas) or bool(adjunto):
                movs = [f"{t.get('tipo','?')[:1].upper()}:${t.get('monto',0):,.0f}@{t.get('categoria','?')[:5]}" for t in movimientos[-3:]]
                prompt_con_contexto += f"\n[JARVIS] Bal=${balance:,.0f} Ing=${ingresos:,.0f} Gas=${gastos:,.0f} | Mov:{movs} | Pres:{presupuestos}\nUsa SOLO estos datos."

            if any(k in texto_lower for k in palabras_tareas) or bool(adjunto):
                tareas = obtener_tareas_pendientes(usuario_id)
                prompt_con_contexto += f"\nTareas:{len(tareas)}"

            # Llamada a la IA con contexto limitado
            if adjunto:
                ruta = os.path.join(TEMP_DIR, adjunto.filename)
                await adjunto.save(ruta)

                # OPTIMIZADO: Usar pensar_respuesta_audio directamente (1 sola llamada API)
                # en lugar de transcribir_audio + pensar_respuesta (2-3 llamadas)
                # Si el usuario escribió texto junto al audio, pasarlo como prompt adicional
                prompt_audio = prompt_con_contexto if texto_limpio else ""
                respuesta_ia = pensar_respuesta_audio(ruta, prompt_audio, usuario_id)

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
            # Ejecutar TTS en hilo separado (no bloquea el event loop)
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

# ===== COMANDOS DE ESTADÍSTICAS =====

@bot.command(name="mes")
async def ver_mes(ctx, *, mes: str = None):
    """Muestra resumen de un mes específico. Ej: !mes agosto, !mes 08 2026, !mes actual"""
    try:
        from modules.database import db
        from datetime import datetime, timedelta
        from dateutil import parser as dateparser
        uid = str(ctx.author.id)

        # Determinar el mes a consultar
        ahora = datetime.now()
        anio_actual = ahora.year
        mes_actual = ahora.month

        if mes is None or mes.lower() in ["actual", "este", "este mes"]:
            mes_num = mes_actual
            anio = anio_actual
        elif mes.lower() in ["anterior", "pasado"]:
            mes_num = mes_actual - 1 if mes_actual > 1 else 12
            anio = anio_actual if mes_actual > 1 else anio_actual - 1
        else:
            # Intentar parsear el mes
            try:
                # Formato: "08 2026" o "agosto 2026"
                partes = mes.strip().split()
                if len(partes) >= 2:
                    mes_str = partes[0]
                    anio_str = partes[1]
                else:
                    mes_str = partes[0]
                    anio_str = str(anio_actual)

                # Convertir mes a número
                meses = {
                    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
                    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
                    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
                }

                if mes_str.isdigit():
                    mes_num = int(mes_str)
                else:
                    mes_num = meses.get(mes_str.lower()[:3], mes_actual)

                anio = int(anio_str) if len(anio_str) == 4 else anio_actual
            except:
                mes_num = mes_actual
                anio = anio_actual

        # Calcular fechas del mes
        fecha_inicio = datetime(anio, mes_num, 1)
        if mes_num == 12:
            fecha_fin = datetime(anio + 1, 1, 1) - timedelta(days=1)
        else:
            fecha_fin = datetime(anio, mes_num + 1, 1) - timedelta(days=1)

        # Obtener transacciones del mes
        ingresos = 0.0
        gastos = 0.0
        por_categoria = {}
        num_dias = (fecha_fin - fecha_inicio).days + 1

        for doc in db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", uid)).stream():
            t = doc.to_dict()
            fecha_str = t.get("fecha", "")
            if not fecha_str:
                continue

            try:
                fecha_trans = datetime.strptime(fecha_str, "%Y-%m-%d")
                if fecha_inicio <= fecha_trans <= fecha_fin:
                    monto = float(t.get("monto", 0))
                    tipo = t.get("tipo", "gasto")
                    cat = t.get("categoria", "General")

                    if tipo == "ingreso":
                        ingresos += monto
                    else:
                        gastos += monto
                        por_categoria[cat] = por_categoria.get(cat, 0) + monto
            except:
                continue

        # Nombres de meses
        nombres_meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        reporte = f"📅 **RESUMEN {nombres_meses[mes_num]} {anio}**\n\n"
        reporte += f"💰 **Ingresos:** +${ingresos:,.0f}\n"
        reporte += f"💸 **Gastos:** -${gastos:,.0f}\n"
        reporte += f"📊 **Balance:** ${ingresos - gastos:,.0f}\n\n"

        if por_categoria:
            reporte += "**🔴 Gastos por categoría:**\n"
            for cat, monto in sorted(por_categoria.items(), key=lambda x: x[1], reverse=True):
                pct = (monto / gastos * 100) if gastos > 0 else 0
                reporte += f"   • {cat}: ${monto:,.0f} ({pct:.0f}%)\n"

            reporte += f"\n📈 **Promedio diario:** ${gastos/num_dias:,.0f}\n"
            reporte += f"📆 **Días en el mes:** {num_dias}"

        else:
            reporte += "Sin transacciones registradas este mes."

        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error generando resumen mensual: {e}")

@bot.command(name="stats")
async def ver_stats(ctx):
    """Muestra estadísticas generales: promedios, proyecciones, anomalías."""
    try:
        from modules.database import db
        from datetime import datetime, timedelta
        uid = str(ctx.author.id)

        ahora = datetime.now()
        hace_30_dias = ahora - timedelta(days=30)

        # Recolectar datos
        todos_gastos = []
        todos_ingresos = []
        por_categoria = {}
        por_dia = {}

        for doc in db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", uid)).stream():
            t = doc.to_dict()
            monto = float(t.get("monto", 0))
            tipo = t.get("tipo", "gasto")
            cat = t.get("categoria", "General")
            fecha_str = t.get("fecha", "")

            if not fecha_str:
                continue

            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
                clave_dia = fecha.strftime("%Y-%m-%d")

                if tipo == "ingreso":
                    todos_ingresos.append(monto)
                else:
                    todos_gastos.append(monto)
                    por_categoria[cat] = por_categoria.get(cat, 0) + monto
                    por_dia[clave_dia] = por_dia.get(clave_dia, 0) + monto
            except:
                continue

        if not todos_gastos and not todos_ingresos:
            await ctx.send("ℹ️ No hay suficientes datos para estadísticas.")
            return

        total_gastos = sum(todos_gastos)
        total_ingresos = sum(todos_ingresos)
        num_trans = len(todos_gastos) + len(todos_ingresos)

        # Calcular promedios
        promedio_gasto = total_gastos / len(todos_gastos) if todos_gastos else 0
        promedio_ingreso = total_ingresos / len(todos_ingresos) if todos_ingresos else 0

        # Encontrar día con más gastos
        dia_max = max(por_dia.items(), key=lambda x: x[1]) if por_dia else ("N/A", 0)

        reporte = "📊 **ESTADÍSTICAS GENERALES**\n\n"

        reporte += "**💰 INGRESOS**\n"
        reporte += f"   • Total: ${total_ingresos:,.0f}\n"
        reporte += f"   • Promedio por transacción: ${promedio_ingreso:,.0f}\n\n"

        reporte += "**💸 GASTOS**\n"
        reporte += f"   • Total: ${total_gastos:,.0f}\n"
        reporte += f"   • Promedio por transacción: ${promedio_gasto:,.0f}\n"
        reporte += f"   • Día con más gastos: {dia_max[0]} (${dia_max[1]:,.0f})\n\n"

        reporte += "**📈 TOP 5 CATEGORÍAS**\n"
        if por_categoria:
            for i, (cat, monto) in enumerate(sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:5], 1):
                pct = (monto / total_gastos * 100) if total_gastos > 0 else 0
                reporte += f"   {i}. {cat}: ${monto:,.0f} ({pct:.0f}%)\n"

        reporte += "\n**📅 PROYECCIÓN**\n"
        dias_pasados = max(1, (ahora - hace_30_dias).days)
        gasto_diario_promedio = total_gastos / dias_pasados if dias_pasados > 0 else 0
        reporte += f"   • Gasto diario promedio (30 días): ${gasto_diario_promedio:,.0f}\n"
        reporte += f"   • Proyección mensual: ${gasto_diario_promedio * 30:,.0f}\n"
        reporte += f"   • Proyección anual: ${gasto_diario_promedio * 365:,.0f}\n"

        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error calculando estadísticas: {e}")

@bot.command(name="top")
async def ver_top(ctx, limite: int = 5):
    """Muestra el top N de categorías con más gastos."""
    try:
        from modules.database import db
        uid = str(ctx.author.id)

        por_categoria = {}
        for doc in db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", uid)).stream():
            t = doc.to_dict()
            if t.get("tipo") == "gasto":
                cat = t.get("categoria", "General")
                monto = float(t.get("monto", 0))
                por_categoria[cat] = por_categoria.get(cat, 0) + monto

        if not por_categoria:
            await ctx.send("ℹ️ No hay gastos registrados.")
            return

        total_gastos = sum(por_categoria.values())
        limite = min(limite, len(por_categoria))

        reporte = f"🏆 **TOP {limite} CATEGORÍAS DE GASTOS**\n\n"

        emoji_medallas = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for i, (cat, monto) in enumerate(sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:limite], 0):
            pct = (monto / total_gastos * 100) if total_gastos > 0 else 0
            barra_len = int(pct / 5)
            barra = "█" * barra_len + "░" * (20 - barra_len)
            emoji = emoji_medallas[i] if i < 10 else f"{i+1}."

            reporte += f"{emoji} **{cat}** ${monto:,.0f}\n"
            reporte += f"   [{barra}] {pct:.1f}%\n\n"

        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error generando top: {e}")

@bot.command(name="metas")
async def ver_metas(ctx):
    """Muestra todas las metas financieras con proyecciones."""
    try:
        from modules.database import obtener_metas, obtener_balance_financiero, proyectar_meta
        metas = obtener_metas(str(ctx.author.id))

        if not metas:
            await ctx.send("📋 No tienes metas. Crea una con: `@Jarvis meta <nombre> <monto> [fecha]`")
            return

        balance, ingresos, gastos, _ = obtener_balance_financiero(str(ctx.author.id))
        capacidad = max(0, ingresos - gastos)

        reporte = "🎯 **TUS METAS FINANCIERAS**\n\n"

        for m in metas:
            p = proyectar_meta(m, capacidad)
            barra_llena = int(p["porcentaje"] / 10)
            barra = "█" * barra_llena + "░" * (10 - barra_llena)

            if m.get("completada"):
                estado = "✅ COMPLETADA"
                emoji = "🎉"
            elif p["atrasado"] and m.get("fecha_limite"):
                estado = "⚠️ ATRASADA"
                emoji = "🚨"
            else:
                estado = "EN PROGRESO"
                emoji = "🎯"

            reporte += f"{emoji} **{m['nombre']}** ({estado})\n"
            reporte += f"   {barra} {p['porcentaje']:.0f}%\n"
            reporte += f"   ${m['monto_actual']:,.0f} / ${m['monto_objetivo']:,.0f}\n"
            if p["falta"] > 0 and not m.get("completada"):
                reporte += f"   💰 Falta: ${p['falta']:,.0f}\n"
            if m.get("fecha_limite"):
                reporte += f"   📅 Límite: {m['fecha_limite']}\n"
                if not m.get("completada"):
                    reporte += f"   💡 Necesitas: ${p['ahorro_necesario']:,.0f}/mes\n"
            reporte += "\n"

        reporte += f"💼 **Capacidad de ahorro:** ${capacidad:,.0f}/mes"
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error obteniendo metas: {e}")


@bot.command(name="meta")
async def gestionar_meta(ctx, accion: str = None, *, texto: str = None):
    """Gestiona metas: crear, progreso, borrar."""
    try:
        uid = str(ctx.author.id)
        from modules.database import guardar_meta, actualizar_progreso_meta, eliminar_meta, obtener_metas, proyectar_meta, obtener_balance_financiero

        if accion == "crear" and texto:
            partes = texto.split()
            if len(partes) >= 2:
                monto_str = partes[-1].replace(',', '')
                try:
                    monto = float(monto_str)
                    nombre = " ".join(partes[:-1])
                    fecha = ""
                    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                    for m in meses:
                        if m in texto.lower():
                            mes_num = meses.index(m) + 1
                            fecha = f"2026-{mes_num:02d}-28"
                            break
                    guardar_meta(uid, nombre, monto, fecha)

                    balance, ingresos, gastos, _ = obtener_balance_financiero(uid)
                    capacidad = max(0, ingresos - gastos)
                    p = proyectar_meta({"monto_objetivo": monto, "monto_actual": 0, "fecha_limite": fecha}, capacidad)

                    msg = f"🎯 **META CREADA**\n\n✅ **{nombre.title()}**\n"
                    msg += f"   Meta: ${monto:,.0f}\n"
                    if fecha:
                        msg += f"   📅 Fecha: {fecha}\n"
                    msg += f"   💰 Tu capacidad de ahorro: ${capacidad:,.0f}/mes\n"
                    if p["atrasado"] and fecha:
                        msg += f"\n⚠️ Necesitas ahorrar ${p['ahorro_necesario']:,.0f}/mes para llegar a tiempo"
                    await ctx.send(msg)
                except ValueError:
                    await ctx.send("⚠️ Formato: `!meta crear <nombre> <monto> [mes]`")
            else:
                await ctx.send("⚠️ Formato: `!meta crear <nombre> <monto> [mes]`")

        elif accion == "progreso" and texto:
            partes = texto.split()
            if len(partes) >= 2:
                try:
                    monto = float(partes[-1].replace(',', ''))
                    nombre = " ".join(partes[:-1])
                    exito = actualizar_progreso_meta(uid, nombre, monto)
                    if exito:
                        metas = obtener_metas(uid)
                        meta = next((m for m in metas if nombre.lower() in m["nombre"].lower()), None)
                        if meta:
                            balance, ingresos, gastos, _ = obtener_balance_financiero(uid)
                            p = proyectar_meta(meta, max(0, ingresos - gastos))
                            barra_llena = int(p['porcentaje'] / 10)
                            barra = "█" * barra_llena + "░" * (10 - barra_llena)
                            msg = f"💰 **PROGRESO ACTUALIZADO**\n\n"
                            msg += f"✅ {meta['nombre']}\n"
                            msg += f"   {barra} {p['porcentaje']:.0f}%\n"
                            msg += f"   ${meta['monto_actual']:,.0f} / ${meta['monto_objetivo']:,.0f}"
                            if meta.get("completada"):
                                msg += f"\n\n🎉 ¡META COMPLETADA!"
                            await ctx.send(msg)
                    else:
                        await ctx.send("⚠️ No encontré esa meta.")
                except ValueError:
                    await ctx.send("⚠️ Formato: `!meta progreso <nombre> <monto>`")
            else:
                await ctx.send("⚠️ Formato: `!meta progreso <nombre> <monto>`")

        elif accion == "borrar" and texto:
            if eliminar_meta(uid, texto):
                await ctx.send(f"🗑️ Meta *'{texto}'* eliminada.")
            else:
                await ctx.send("⚠️ No encontré esa meta.")

        else:
            await ctx.send("""🎯 **GESTIÓN DE METAS**

`!metas` - Ver todas tus metas
`!meta crear <nombre> <monto> [mes]` - Crear meta
`!meta progreso <nombre> <monto>` - Sumar progreso
`!meta borrar <nombre>` - Eliminar meta

**Ejemplos:**
`!meta crear vacaciones 3000000 diciembre`
`!meta crear casa 50000000`
`!meta progreso vacaciones 500000`""")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")


@bot.command(name="presupuesto")
async def modificar_presupuesto_cmd(ctx, *, texto: str = None):
    """Modifica un presupuesto existente: !presupuesto <cat> <nuevo_monto>"""
    try:
        uid = str(ctx.author.id)
        from modules.database import modificar_presupuesto, obtener_resumen_presupuestos

        if not texto:
            presupuestos = obtener_resumen_presupuestos(uid)
            if not presupuestos:
                await ctx.send("📋 No tienes presupuestos. Crea uno con `@Jarvis presupuesto <cat> <monto>`")
                return
            lista = "\n".join([f"• **{k}**: ${v:,.0f}" for k, v in presupuestos.items()])
            await ctx.send(f"🎯 **TUS PRESUPUESTOS**\n\n{lista}\n\n**Modificar:** `!presupuesto <cat> <nuevo_monto>`")
            return

        partes = texto.split()
        if len(partes) >= 2:
            try:
                nuevo_monto = float(partes[-1].replace(',', ''))
                categoria = " ".join(partes[:-1])
                modificar_presupuesto(uid, categoria, nuevo_monto)
                await ctx.send(f"🔄 **Presupuesto actualizado:** {categoria.title()} = **${nuevo_monto:,.0f}**")
            except ValueError:
                await ctx.send("⚠️ Formato: `!presupuesto <categoría> <monto>`")
        else:
            await ctx.send("⚠️ Formato: `!presupuesto <categoría> <monto>`\nEjemplo: `!presupuesto Women 400000`")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")


@bot.command(name="pagos")
async def ver_pagos_fijos(ctx):
    """Muestra los pagos fijos mensuales."""
    try:
        uid = str(ctx.author.id)
        from modules.database import obtener_pagos_fijos
        pagos = obtener_pagos_fijos(uid)

        if not pagos:
            await ctx.send("📋 No tienes pagos fijos. Agrega con `@Jarvis pago fijo <nombre> <monto> día <N>`")
            return

        reporte = "⏰ **PAGOS FIJOS MENSUALES**\n\n"
        for p in sorted(pagos, key=lambda x: x.get("dia_mes", 1)):
            reporte += f"📅 **Día {p['dia_mes']}** - {p['nombre']}: ${p['monto']:,.0f}\n"
            reporte += f"   Categoría: {p.get('categoria', 'General')}\n\n"

        total = sum(p.get("monto", 0) for p in pagos)
        reporte += f"💰 **Total mensual:** ${total:,.0f}"
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")


@bot.command(name="pago")
async def gestionar_pago_fijo(ctx, accion: str = None, *, texto: str = None):
    """Gestiona pagos fijos: !pago fijo <nombre> <monto> día <N>"""
    try:
        uid = str(ctx.author.id)
        from modules.database import guardar_pago_fijo, eliminar_pago_fijo

        if accion == "fijo" and texto:
            # !pago fijo <nombre> <monto> día <N>
            import re
            match = re.search(r'(.+?)\s+([\d,.]+)\s+(?:d[ií]a\s+(\d+))?', texto.lower())
            if match:
                nombre = match.group(1).strip().title()
                monto = float(match.group(2).replace(',', ''))
                dia = int(match.group(3)) if match.group(3) else 1
                guardar_pago_fijo(uid, nombre, monto, dia)
                await ctx.send(f"⏰ **Pago fijo creado:** {nombre} = ${monto:,.0f} (día {dia} de cada mes)")
            else:
                await ctx.send("⚠️ Formato: `!pago fijo <nombre> <monto> día <N>`")
        elif accion == "borrar" and texto:
            if eliminar_pago_fijo(uid, texto):
                await ctx.send(f"🗑️ Pago fijo *'{texto}'* eliminado.")
            else:
                await ctx.send("⚠️ No encontré ese pago.")
        else:
            await ctx.send("""⏰ **GESTIÓN DE PAGOS FIJOS**

`!pagos` - Ver todos los pagos
`!pago fijo <nombre> <monto> día <N>` - Crear
`!pago borrar <nombre>` - Eliminar

**Ejemplos:**
`!pago fijo arriendo 1500000 día 5`
`!pago fijo internet 120000 día 10`
`!pago fijo celular 50000 día 20`""")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")


@bot.command(name="perfil")
async def ver_perfil(ctx):
    """Muestra el perfil del usuario."""
    try:
        uid = str(ctx.author.id)
        from modules.database import obtener_perfil
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

if __name__ == "__main__":
    if TOKEN: bot.run(TOKEN)