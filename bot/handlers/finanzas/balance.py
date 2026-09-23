"""bot/handlers/finanzas/balance.py - Comandos de balance y estadísticas."""
from datetime import datetime, timedelta
import discord
from google.cloud.firestore_v1.base_query import FieldFilter

from bot import bot
from bot.services.db import obtener_balance_financiero
from modules.finance import reports


@bot.command(name="finanzas")
async def ver_finanzas(ctx):
    """Muestra el balance general del usuario."""
    try:
        balance, ingresos, gastos, movimientos = obtener_balance_financiero(str(ctx.author.id))
        reporte = reports.formatear_balance_general(balance, ingresos, gastos, movimientos)
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error al obtener finanzas: {e}")


@bot.command(name="mes")
async def ver_mes(ctx, *, mes: str = None):
    """Muestra resumen de un mes específico. Ej: !mes agosto, !mes 08 2026, !mes actual"""
    try:
        from bot.services.db import db
        uid = str(ctx.author.id)

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
            try:
                partes = mes.strip().split()
                if len(partes) >= 2:
                    mes_str = partes[0]
                    anio_str = partes[1]
                else:
                    mes_str = partes[0]
                    anio_str = str(anio_actual)

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

        fecha_inicio = datetime(anio, mes_num, 1)
        if mes_num == 12:
            fecha_fin = datetime(anio + 1, 1, 1) - timedelta(days=1)
        else:
            fecha_fin = datetime(anio, mes_num + 1, 1) - timedelta(days=1)

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

        nombres_meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        reporte = reports.formatear_resumen_mes(nombres_meses[mes_num], anio, ingresos, gastos, por_categoria, num_dias)
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error generando resumen mensual: {e}")


@bot.command(name="stats")
async def ver_stats(ctx):
    """Muestra estadísticas generales: promedios, proyecciones, anomalías."""
    try:
        from bot.services.db import db
        uid = str(ctx.author.id)

        ahora = datetime.now()
        hace_30_dias = ahora - timedelta(days=30)

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
        promedio_gasto = total_gastos / len(todos_gastos) if todos_gastos else 0
        promedio_ingreso = total_ingresos / len(todos_ingresos) if todos_ingresos else 0
        dia_max = max(por_dia.items(), key=lambda x: x[1]) if por_dia else ("N/A", 0)

        top_categorias = []
        for cat, monto in sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:5]:
            pct = (monto / total_gastos * 100) if total_gastos > 0 else 0
            top_categorias.append((cat, monto, pct))

        dias_pasados = max(1, (ahora - hace_30_dias).days)
        proyeccion_diaria = total_gastos / dias_pasados if dias_pasados > 0 else 0

        reporte = reports.formatear_estadisticas(
            total_ingresos, total_gastos, promedio_ingreso, promedio_gasto,
            dia_max, top_categorias, proyeccion_diaria
        )
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error calculando estadísticas: {e}")
