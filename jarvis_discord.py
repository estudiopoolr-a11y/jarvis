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
    analizar_inversion, transcribir_audio, _API_KEYS, _key_index
)
from modules.database import (
    guardar_mensaje, obtener_tareas_pendientes, marcar_tarea_completada,
    obtener_balance_financiero, obtener_resumen_presupuestos
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
    formatos_txt = ('.txt', '.csv')
    adjunto = next((a for a in message.attachments if (
        a.filename.lower().endswith(formatos_audio + formatos_txt)
        or 'audio' in (a.content_type or '')
        or (a.content_type or '').startswith('text/')
    )), None)

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

                es_txt = adjunto.filename.lower().endswith((".txt", ".csv")) or (adjunto.content_type or "").startswith("text/")

                if es_txt:
                    # TXT/CSV: parsear e importar directamente (sin Gemini)
                    try:
                        with open(ruta, "r", encoding="utf-8-sig", errors="replace") as f:
                            texto_archivo = f.read()

                        from modules.importador_txt import importar_texto
                        dbmod = __import__("modules.database", fromlist=["inicializar_firebase"])
                        db = dbmod.inicializar_firebase()
                        if not db:
                            respuesta_ia = "⚠️ No pude conectar con Firebase para importar el TXT."
                        else:
                            respuesta_ia = importar_texto(usuario_id, texto_archivo, db, anio_default=2026)
                    except Exception as txt_error:
                        print(f"[TXT] Error importando archivo: {txt_error}")
                        respuesta_ia = f"⚠️ No pude importar el TXT: `{txt_error}`"
                else:
                    # AUDIO: transcribir primero, luego parsers determinísticos.
                    texto_transcrito = transcribir_audio(ruta)

                    if texto_transcrito:
                        print(f"[AUDIO] Transcripción: {texto_transcrito[:100]}")
                        respuesta_ia = procesar_intencion_natural(texto_transcrito, usuario_id)
                        if respuesta_ia:
                            print(f"[AUDIO] ✅ Parser determinístico matcheó")
                        else:
                            # Si no matchea, ir a Gemini con el texto.
                            print(f"[AUDIO] Sin parser match → Gemini con texto")
                            respuesta_ia = pensar_respuesta(texto_transcrito)
                    else:
                        print(f"[AUDIO] Transcripción falló → modo audio directo")
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

@bot.command(name="diagnostico")
async def diagnostico(ctx):
    """Diagnóstico de lectura Kebo del usuario (para depurar ¿por qué $0?)."""
    try:
        from modules.database import _get_user_ref, inicializar_firebase, obtener_balance_financiero
        if not firebase_admin._apps:
            inicializar_firebase()
        uid = str(ctx.author.id)
        _, user_ref = _get_user_ref(uid)
        partes = [f"🔎 **Diagnóstico para `{uid}`**"]
        if not user_ref:
            partes.append("⚠️ user_ref vacío")
            await ctx.send("\n".join(partes))
            return

        # 1) ¿Existe el doc de usuario?
        try:
            udoc = user_ref.get()
            partes.append(f"• Doc usuario existe: {udoc.exists}")
        except Exception as e:
            partes.append(f"• Error get usuario: {e}")

        # 2) Listar meses de transactions
        try:
            meses = [d.id for d in user_ref.collection("transactions").stream()]
            partes.append(f"• Meses en transactions: {meses}")
        except Exception as e:
            partes.append(f"• Error listando transactions: {e}")

        # 3) Contar items en julio
        try:
            items = list(user_ref.collection("transactions").document("2026-07").collection("items").stream())
            partes.append(f"• Items en 2026-07: {len(items)}")
            if items:
                t0 = items[0].to_dict() or {}
                partes.append(f"• Primer item keys: {list(t0.keys())}")
                partes.append(f"• type={t0.get('type')} amount={t0.get('amount')} date={t0.get('date')}")
        except Exception as e:
            partes.append(f"• Error items 2026-07: {e}")

        # 4) Qué retorna obtener_balance_financiero
        try:
            balance = obtener_balance_financiero(uid)
            partes.append(f"• obtener_balance_financiero → {balance[:3]}, #{len(balance[3])} mov")
        except Exception as e:
            partes.append(f"• Error obtener_balance_financiero: {e}")

        await ctx.send("\n".join(partes))
    except Exception as e:
        await ctx.send(f"⚠️ Error en diagnostico: {e}")

@bot.command(name="buscar_historial")
async def buscar_historial(ctx):
    """Recorre todos los usuarios y reporta dónde hay transacciones/budgets por mes."""
    try:
        from modules.database import inicializar_firebase, db
        if not firebase_admin._apps:
            inicializar_firebase()

        lineas = []
        usuarios = list(db.collection("users").stream())
        lineas.append(f"🔎 **{len(usuarios)} usuarios encontrados**")

        # Meses de interés (mayo-agosto 2026) probados de forma directa,
        # porque listar la subcolección transactions NO devuelve docs implícitos.
        fechas_probar = ["2026-08", "2026-07", "2026-06", "2026-05", "2026-04"]

        for udoc in usuarios:
            uid = udoc.id
            ref = db.collection("users").document(uid)
            meses_tx = []
            suma_tx = 0
            for mi in fechas_probar:
                try:
                    items = list(ref.collection("transactions").document(mi).collection("items").stream())
                    if items:
                        meses_tx.append(f"{mi}({len(items)})")
                        suma_tx += len(items)
                except Exception:
                    pass
            meses_bud = []
            for mi in fechas_probar:
                try:
                    boutems = list(ref.collection("budgets").document(mi).collection("items").stream())
                    if boutems:
                        meses_bud.append(f"{mi}({len(boutems)})")
                except Exception:
                    pass

            etiqueta = "**← TU CUENTA**" if uid == str(ctx.author.id) else ""
            lineas.append(
                f"\n📁 **{uid}** {etiqueta}\n"
                f"   • transactions KEBO: {meses_tx or 'ninguno'}  (total {suma_tx})\n"
                f"   • budgets KEBO: {meses_bud or 'ninguno'}"
            )

        # ---- LEGACY: finanzas/ y presupuestos/ ----
        try:
            leg_fin = {}
            for d in db.collection("finanzas").stream():
                t = d.to_dict() or {}
                k = str(t.get("usuario_id", "?"))
                mes = t.get("mes", "?")
                leg_fin.setdefault(k, {}).setdefault(mes, 0)
                leg_fin[k][mes] += 1
            lineas.append("\n🗄️ **Legacy `finanzas/`** (movimientos por usuario y mes):")
            if not leg_fin:
                lineas.append("   vacío")
            for k, meses in leg_fin.items():
                desglose = ", ".join(f"{m}: {n}" for m, n in meses.items())
                mk = "**← TU CUENTA**" if k == str(ctx.author.id) else ""
                lineas.append(f"   • `{k}` {mk} → {desglose}")
        except Exception as e:
            lineas.append(f"   ⚠️ Error finanzas legacy: {e}")

        try:
            leg_pres = {}
            for d in db.collection("presupuestos").stream():
                p = d.to_dict() or {}
                k = str(p.get("usuario_id", "?"))
                leg_pres[k] = leg_pres.get(k, 0) + 1
            lineas.append("\n🗄️ **Legacy `presupuestos/`** (por usuario):")
            if not leg_pres:
                lineas.append("   vacío")
            for k, n in leg_pres.items():
                mk = "**← TU CUENTA**" if k == str(ctx.author.id) else ""
                lineas.append(f"   • `{k}` {mk} → {n} presupuestos")
        except Exception as e:
            lineas.append(f"   ⚠️ Error presupuestos legacy: {e}")

        await ctx.send("\n".join(lineas))
    except Exception as e:
        await ctx.send(f"⚠️ Error en buscar_historial: {e}")

@bot.command(name="corregir_gastos")
async def corregir_gastos(ctx, arg: str = ""):
    """Muestra/elimina gastos duplicados de julio 2026.
    Uso: !corregir_gastos          → vista previa (no borra)
         !corregir_gastos confirmar → borra los duplicados
    """
    try:
        from modules.database import deduplicar_gastos, inicializar_firebase
        if not firebase_admin._apps:
            inicializar_firebase()
        uid = str(ctx.author.id)
        dry_run = arg.strip().lower() != "confirmar"
        reporte = deduplicar_gastos(uid, 2026, 7, dry_run=dry_run)
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error en corregir_gastos: {e}")

@bot.command(name="migrar_finanzas")
async def migrar_finanzas(ctx, arg: str = ""):
    """Migra finanzas/presupuestos legacy → Kebo (tu cuenta) y borra legacy.
    Uso: !migrar_finanzas            → vista previa (no migra ni borra)
         !migrar_finanzas confirmar  → migra y deja solo Kebo
    """
    try:
        from modules import database as dbmod
        if not firebase_admin._apps:
            dbmod.inicializar_firebase()
        db = dbmod.db if dbmod.db else dbmod.inicializar_firebase()
        uid = str(ctx.author.id)
        confirmar = arg.strip().lower() == "confirmar"

        # ---------- Leer legacy ----------
        finanzas = {}
        for d in db.collection("finanzas").stream():
            t = d.to_dict() or {}
            # solo movimientos del usuario (o los que no tienen usuario = suyos)
            t_uid = str(t.get("usuario_id", ""))
            if t_uid and t_uid not in (uid, "default"):
                continue
            mes = t.get("mes") or ""
            finanzas.setdefault(mes, []).append(t)

        presupuestos = {p.get("categoria", "?").capitalize(): float(p.get("limite", 0))
                        for p in db.collection("presupuestos").stream()
                        if not p.to_dict().get("usuario_id") or str(p.to_dict().get("usuario_id")) in (uid, "default")}

        # ---------- Resumen ----------
        total_ing = sum(t.get("monto", 0) for ms in finanzas.values() for t in ms
                        if str(t.get("tipo")).lower().startswith("ing"))
        total_gas = sum(t.get("monto", 0) for ms in finanzas.values() for t in ms
                        if str(t.get("tipo")).lower().startswith("gas"))

        lineas = [f"🗄️ **LEGACY — finanzas/ y presupuestos/**"]
        if not finanzas and not presupuestos:
            lineas.append("\n✅ No hay data legacy de finanzas que migrar.")
        else:
            lineas.append(f"\n📈 **finanzas/** por mes:")
            for mes in sorted(finanzas):
                movs = finanzas[mes]
                lineas.append(f"   `{mes or 'sin-mes'}` → {len(movs)} movs")
            lineas.append(f"\n   • Ingresos legacy: +${total_ing:,.2f}")
            lineas.append(f"   • Gastos legacy:   -${total_gas:,.2f}")
            if presupuestos:
                lineas.append(f"\n📑 **presupuestos/** legacy ({len(presupuestos)}):")
                for cat, m in presupuestos.items():
                    lineas.append(f"   • {cat}: ${m:,.0f}")

            # Detección de julio duplicado: cuánto hay en legacy de 2026-07
            jul_legacy = finanzas.get("2026-07") or []
            lineas.append(f"\n⚠️ **Julio en legacy**: {len(jul_legacy)} movs "
                          f"(vs {len(list(db.collection('users').document(uid).collection('transactions').document('2026-07').collection('items').stream()))} en Kebo)")

        if confirmar:
            if not finanzas and not presupuestos:
                await ctx.send("\n".join(lineas) + "\n\nNada que migrar.")
                return
            # ---------- Migrar finanzas legacy → Kebo ----------
            mig_s = mig_g = 0
            for mes, movs in finanzas.items():
                if not mes:
                    continue
                year, month = mes.split("-")
                for t in movs:
                    tipo = str(t.get("tipo")).lower()
                    tipo_k = "income" if tipo.startswith("ing") else "expense"
                    cat = str(t.get("categoria")).capitalize()
                    monto = float(t.get("monto", 0))
                    fecha = f"{int(year):04d}-{int(month):02d}-15"
                    try:
                        dbmod.registrar_transaccion_v2(
                            uid, tipo_k, monto, cat,
                            descripcion=str(t.get("descripcion", "")),
                            cuenta_nombre="Efectivo",
                            fecha=fecha,
                        )
                        if tipo_k == "income":
                            mig_s += 1
                        else:
                            mig_g += 1
                    except Exception as e:
                        await ctx.send(f"⚠️ No migré {cat} ${monto}: {e}")
            # ---------- Migrar presupuestos legacy → Kebo ----------
            # sin mes conocido: al mes más reciente con actividad
            meses_orden = sorted([m for m in finanzas if m], reverse=True)
            for cat, monto in presupuestos.items():
                y_m = None
                # si ya hay un presupuesto de esa cat en julio, no lo piso
                if y_m is None and meses_orden:
                    y_m = meses_orden[0]
                if not y_m:
                    continue
                year, month = y_m.split("-")
                try:
                    dbmod.establecer_presupuesto_mes(uid, cat, monto,
                                                     year=int(year), month=int(month))
                except Exception as e:
                    await ctx.send(f"⚠️ No migré presupuesto {cat}: {e}")
            lineas.append(f"\n🚀 **Migrado a Kebo**: {mig_s} ingresos + {mig_g} gastos + "
                          f"{len(presupuestos)} presupuestos")
            # ---------- Borrar legacy ----------
            n_fin = sum(len(v) for v in finanzas.values())
            try:
                for d in db.collection("finanzas").stream():
                    d.reference.delete()
                for d in db.collection("presupuestos").stream():
                    d.reference.delete()
                lineas.append(f"\n🗑️ **Legacy borrado**: {n_fin} finanzas + {len(presupuestos)} presupuestos. "
                              f"Solo queda KEBO.")
            except Exception as e:
                lineas.append(f"\n⚠️ Migrado pero no pude borrar legacy: {e}")
        else:
            lineas.append("\n\nℹ️ Vista previa — nada migrado ni borrado.")
            lineas.append("Para migrar y dejar solo Kebo: `!migrar_finanzas confirmar`")

        await ctx.send("\n".join(lineas))
    except Exception as e:
        await ctx.send(f"⚠️ Error en migrar_finanzas: {e}")

@bot.command(name="consolidar")
async def consolidar(ctx, *, arg: str = ""):
    """Consolida finanzas KEBO de 'default' → tu cuenta.
    Uso:
      !consolidar                      → muestra julio (default vs tuyo) lado a lado
      !consolidar mostrar              → re-muestra julio comparado
      !consolidar copiar may,jun,ago   → copia esos meses de default a tu cuenta
      !consolidar copiar todo          → copia todos los meses EXCEPTO julio
      !consolidar copiar julio         → copia también julio (tras revisar)
    """
    try:
        from modules import database as dbmod
        if not firebase_admin._apps:
            dbmod.inicializar_firebase()
        db = dbmod.db if dbmod.db else dbmod.inicializar_firebase()
        uid = str(ctx.author.id)
        ORIGEN = "default"
        MESES = ["2026-05", "2026-06", "2026-07", "2026-08"]

        def leer_items(user_id, mes):
            out = []
            base = db.collection("users").document(user_id).collection("transactions").document(mes).collection("items")
            try:
                for d in base.stream():
                    it = d.to_dict() or {}
                    it["_id"] = d.id
                    it["_mes"] = mes
                    out.append(it)
            except Exception:
                pass
            return out

        def desc(item):
            tipo = item.get("type", "expense")
            m = float(item.get("amount", item.get("monto", 0)))
            signo = "+" if tipo == "income" else "-"
            emoji = "🟢" if tipo == "income" else "🔴"
            cat = str(item.get("category_name") or item.get("categoria") or item.get("category_id") or "?")
            d = item.get("date", "") or item.get("_mes")
            return f"{emoji} {signo}${m:,.0f} · {cat} · {d[:10]}"

        accion = arg.strip().lower()

        # ---------- Ver julio comparado ----------
        if not accion or accion == "mostrar":
            jul_def = leer_items(ORIGEN, "2026-07")
            jul_uid = leer_items(uid, "2026-07")
            lineas = [f"🔁 **JULIO comparado** — `default` ({len(jul_def)}) vs TU cuenta ({len(jul_uid)})\n"]
            lineas.append(f"**En `default` (importado):**")
            lineas += [f"   {desc(x)}" for x in jul_def] or ["   (nada)"]
            lineas.append(f"\n**En TU cuenta (del bloque):**")
            lineas += [f"   {desc(x)}" for x in jul_uid] or ["   (nada)"]
            total_def = sum(float(x.get("amount", x.get("monto", 0))) for x in jul_def if x.get("type") != "income")
            lineas.append(f"\nℹ️ Subtotal gasto julio `default`: -${total_def:,.0f}. "
                          f"Cuando lo revises: `!consolidar copiar todo` (excluye julio) o `!consolidar copiar julio`.")
            await ctx.send("\n".join(lineas))
            return

        # ---------- Copiar meses ----------
        if accion.startswith("copiar"):
            resto = accion.replace("copiar", "").strip().lower()
            if resto in ("todo", "all", ""):
                meses = [m for m in MESES if m != "2026-07"]
            else:
                pedido = [p.strip() for p in resto.replace(" ", "").split(",") if p.strip()]
                meses = []
                for m in MESES:
                    partes = m.split("-")
                    y = partes[0]
                    num = str(int(partes[1]))
                    if num in pedido or y in pedido or m in pedido or m.replace("-", "") in pedido:
                        meses.append(m)
                if "julio" in resto or "jul" in resto or "7" in pedido:
                    meses.append("2026-07")

            if not meses:
                await ctx.send("ℹ️ No se copió nada. Meses válidos: may, jun, jul, ago.")
                return

            # Resolver categoría: default items guardan category_name? si no, por category_id
            # -> usar registrar_transaccion_v2 (resuelve/crea categoría y cuenta bajo el uid)
            copiadas = migradas_ing = migradas_gas = 0
            duplicadas = []
            for mes in meses:
                items = leer_items(ORIGEN, mes)
                for it in items:
                    tipo = it.get("type", "expense")
                    monto = abs(float(it.get("amount", it.get("monto", 0))))
                    fecha = it.get("date", "")
                    descripcion = it.get("description", "")
                    # nombre de categoría: si hay category_name usar; si no, intentar por category_id
                    cat = it.get("category_name") or None
                    if not cat and it.get("category_id"):
                        try:
                            cid = db.collection("users").document(ORIGEN).collection("categories").document(str(it["category_id"])).get()
                            if cid.exists:
                                cat = cid.to_dict().get("nombre", it["category_id"])
                        except Exception:
                            cat = None
                    if not cat:
                        cat = it.get("category_id") or "General"

                    try:
                        dbmod.registrar_transaccion_v2(
                            uid, tipo, monto, str(cat).capitalize(),
                            descripcion=descripcion or f"Importado {mes}",
                            cuenta_nombre="Efectivo",
                            fecha=fecha if fecha else f"{mes}-15",
                        )
                        copiadas += 1
                        if tipo == "income":
                            migradas_ing += 1
                        else:
                            migradas_gas += 1
                    except Exception as e:
                        duplicadas.append(f"{mes}: {desc(it)} → {e}")

            res = [f"✅ Consolidado `default` → TU cuenta: **{copiadas}** transacciones "
                   f"({migradas_ing} ing, {migradas_gas} gas) en {', '.join(meses)}"]
            if duplicadas:
                res.append(f"\n⚠️ No se copiaron {len(duplicadas)}:")
                res += [f"   • {x}" for x in duplicadas[:10]]
            res.append("\nRevisa con `!finanzas` o `!buscar_historial`.")
            await ctx.send("\n".join(res))
            return

        await ctx.send("ℹ️ Uso: `!consolidar` | `!consolidar mostrar` | `!consolidar copiar may,jun,ago|todo|julio`")
    except Exception as e:
        await ctx.send(f"⚠️ Error en consolidar: {e}")

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
