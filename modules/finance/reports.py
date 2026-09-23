"""Centralized formatting for financial reports (emojis, bars, tables)."""

def crear_barra_progreso(pct: int) -> str:
    """Generates a 10-segment progress bar."""
    barra_llena = int(pct / 10)
    barra_vacia = 10 - barra_llena
    return "█" * barra_llena + "░" * barra_vacia

def formatear_balance_general(balance: float, ingresos: float, gastos: float, movimientos: list = None) -> str:
    """Formats the general financial balance."""
    reporte = f"📊 **BALANCE FINANCIERO GENERAL** 📊\n\n"
    reporte += f"• **Ingresos Totales:** +${ingresos:,.0f}\n"
    reporte += f"• **Gastos Totales:** -${gastos:,.0f}\n"
    reporte += f"• **Balance Neto:** ${balance:,.0f}\n\n"

    if movimientos:
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

    return reporte

def formatear_presupuestos(presupuestos: dict, gastos_por_cat: dict) -> str:
    """Formats budget status with progress bars."""
    if not presupuestos:
        return "⚠️ No tienes presupuestos configurados. Usa `@Jarvis presupuesto Categoría Monto` para crear uno."

    reporte = "🎯 **ESTADO DE PRESUPUESTOS**\n\n"
    for cat, limite in presupuestos.items():
        gastado = gastos_por_cat.get(cat, 0)
        pct = min(100, int((gastado / limite) * 100)) if limite > 0 else 0
        barra = crear_barra_progreso(pct)

        if pct >= 100:
            estado, color_emoji = "🔴 EXCEDIDO", "🚨"
        elif pct >= 90:
            estado, color_emoji = "🟠 CRÍTICO", "⚠️"
        elif pct >= 80:
            estado, color_emoji = "🟡 ADVERTENCIA", "⚠️"
        else:
            estado, color_emoji = "🟢 OK", "✅"

        restante = limite - gastado
        reporte += f"{color_emoji} **{cat}** {estado}\n"
        reporte += f"   {barra} {pct}%\n"
        reporte += f"   Gastado: ${gastado:,.0f} / ${limite:,.0f}\n"
        reporte += f"   Restante: ${max(0, restante):,.0f}\n\n"

    return reporte

def formatear_historial(transacciones: list, cantidad: int) -> str:
    """Formats a list of recent transactions."""
    if not transacciones:
        return "📋 Sin transacciones registradas."

    reporte = f"📜 **ÚLTIMAS {len(transacciones[:cantidad])} TRANSACCIONES**\n\n"
    for t in transacciones[:cantidad]:
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

    return reporte

def formatear_busqueda_categoria(termino: str, resultados: list) -> str:
    """Formats search results for a specific category or term."""
    if not resultados:
        return f"🔍 No encontré transacciones que coincidan con **'{termino}'**."

    total_gastos = sum(float(t.get("monto", 0)) for t in resultados if t.get("tipo") == "gasto")
    total_ingresos = sum(float(t.get("monto", 0)) for t in resultados if t.get("tipo") == "ingreso")

    reporte = f"🔍 **RESULTADOS PARA '{termino}'** ({len(resultados)} transacciones)\n\n"
    reporte += f"💸 Total gastos: ${total_gastos:,.0f}\n"
    reporte += f"💰 Total ingresos: ${total_ingresos:,.0f}\n\n"
    reporte += "**Detalle:**\n"

    for t in resultados[:15]:
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

    return reporte

def formatear_resumen_mes(mes_nombre: str, anio: int, ingresos: float, gastos: float, por_categoria: dict, num_dias: int) -> str:
    """Formats a monthly financial summary."""
    reporte = f"📅 **RESUMEN {mes_nombre} {anio}**\n\n"
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

    return reporte

def formatear_estadisticas(total_ingresos: float, total_gastos: float, promedio_ingreso: float, promedio_gasto: float, dia_max: tuple, top_categorias: list, proyeccion_diaria: float) -> str:
    """Formats general financial statistics."""
    reporte = "📊 **ESTADÍSTICAS GENERALES**\n\n"
    reporte += "**💰 INGRESOS**\n"
    reporte += f"   • Total: ${total_ingresos:,.0f}\n"
    reporte += f"   • Promedio por transacción: ${promedio_ingreso:,.0f}\n\n"

    reporte += "**💸 GASTOS**\n"
    reporte += f"   • Total: ${total_gastos:,.0f}\n"
    reporte += f"   • Promedio por transacción: ${promedio_gasto:,.0f}\n"
    reporte += f"   • Día con más gastos: {dia_max[0]} (${dia_max[1]:,.0f})\n\n"

    reporte += "**📈 TOP 5 CATEGORÍAS**\n"
    for i, (cat, monto, pct) in enumerate(top_categorias, 1):
        reporte += f"   {i}. {cat}: ${monto:,.0f} ({pct:.0f}%)\n"

    reporte += "\n**📅 PROYECCIÓN**\n"
    reporte += f"   • Gasto diario promedio (30 días): ${proyeccion_diaria:,.0f}\n"
    reporte += f"   • Proyección mensual: ${proyeccion_diaria * 30:,.0f}\n"
    reporte += f"   • Proyección anual: ${proyeccion_diaria * 365:,.0f}\n"

    return reporte

def formatear_top_categorias(limite: int, categorias_data: list) -> str:
    """Formats the top N expense categories with bars."""
    if not categorias_data:
        return "ℹ️ No hay gastos registrados."

    reporte = f"🏆 **TOP {limite} CATEGORÍAS DE GASTOS**\n\n"
    emoji_medallas = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for i, (cat, monto, pct) in enumerate(categorias_data, 0):
        barra_len = int(pct / 5)
        barra = "█" * barra_len + "░" * (20 - barra_len)
        emoji = emoji_medallas[i] if i < 10 else f"{i+1}."
        reporte += f"{emoji} **{cat}** ${monto:,.0f}\n"
        reporte += f"   [{barra}] {pct:.1f}%\n\n"

    return reporte
