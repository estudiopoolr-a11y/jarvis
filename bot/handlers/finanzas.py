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

@bot.command(name="presupuestos")
async def ver_presupuestos(ctx):
    """Muestra el estado de todos los presupuestos con barras de progreso."""
    try:
        from bot.services.db import inicializar_firebase
        if not firebase_admin._apps:
            inicializar_firebase()

        from bot.services.db import db
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
        from bot.services.db import db
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
        from bot.services.db import db
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

@bot.command(name="mes")
async def ver_mes(ctx, *, mes: str = None):
    """Muestra resumen de un mes específico. Ej: !mes agosto, !mes 08 2026, !mes actual"""
    try:
        from bot.services.db import db
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
        from bot.services.db import db
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
        from bot.services.db import db
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
