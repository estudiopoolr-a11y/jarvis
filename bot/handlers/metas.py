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

@bot.command(name="metas")
async def ver_metas(ctx):
    """Muestra todas las metas financieras con proyecciones."""
    try:
        from bot.services.db import obtener_metas, obtener_balance_financiero, proyectar_meta
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
        from bot.services.db import guardar_meta, actualizar_progreso_meta, eliminar_meta, obtener_metas, proyectar_meta, obtener_balance_financiero

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
        from bot.services.db import modificar_presupuesto, obtener_resumen_presupuestos

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
        from bot.services.db import obtener_pagos_fijos
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
        from bot.services.db import guardar_pago_fijo, eliminar_pago_fijo

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
