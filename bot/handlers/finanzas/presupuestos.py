"""bot/handlers/finanzas/presupuestos.py - Comandos de gestión de presupuestos."""
import discord
import firebase_admin
from google.cloud.firestore_v1.base_query import FieldFilter

from bot import bot
from modules.finance import reports


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

        reporte = reports.formatear_presupuestos(presupuestos, gastos)
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error al obtener presupuestos: {e}")
