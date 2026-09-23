"""bot/handlers/finanzas/historial.py - Comandos de historial y búsqueda."""
import discord
from google.cloud.firestore_v1.base_query import FieldFilter

from bot import bot
from modules.finance import reports


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

        docs_ordenados = sorted(docs, key=lambda d: d.to_dict().get("fecha", ""), reverse=True)
        transacciones = [doc.to_dict() for doc in docs_ordenados]

        reporte = reports.formatear_historial(transacciones, cantidad)
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

        reporte = reports.formatear_busqueda_categoria(termino, resultados)
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error en búsqueda: {e}")


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

        categorias_data = []
        for cat, monto in sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:limite]:
            pct = (monto / total_gastos * 100) if total_gastos > 0 else 0
            categorias_data.append((cat, monto, pct))

        reporte = reports.formatear_top_categorias(limite, categorias_data)
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error generando top: {e}")
