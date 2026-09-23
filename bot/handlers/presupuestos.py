"""Handlers de comandos Discord de JARVIS."""
from bot import bot
from bot.services.db import *  # noqa: F403,F401

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

