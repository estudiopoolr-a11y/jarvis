"""Handlers de comandos Discord de JARVIS."""
from bot import bot
from bot.services.db import *  # noqa: F403,F401

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
