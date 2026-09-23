"""Financial consultation actions for NLP processing."""

def handle_listar_categorias(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle listing categories action."""
    from datetime import datetime
    from modules.db import listar_categorias, listar_cuentas, obtener_presupuestos_v2

    ahora = datetime.now()
    mes_actual = ahora.strftime("%Y-%m")

    # Categorías Firestore
    cats = listar_categorias(usuario_id)
    # Cuentas
    cuentas = listar_cuentas(usuario_id)
    # Presupuestos del mes actual
    presupuestos = obtener_presupuestos_v2(usuario_id, mes_actual)

    msg = "📂 **Categorías disponibles:**\n"
    if cats:
        for c in cats:
            nombre = c.get("nombre") or c.get("name", "?")
            icono = c.get("icono") or c.get("icon", "📂")
            msg += f"  {icono} {nombre}\n"
    else:
        msg += "  (ninguna definida)\n"

    # Cuentas
    if cuentas:
        total_cuentas = sum(float(c.get("balance", 0) or 0) for c in cuentas)
        msg += f"\n💳 **Cuentas ({len(cuentas)}):**\n"
        for c in cuentas:
            icono = c.get("icon") or c.get("icono", "💳")
            nombre = c.get("nombre", "?")
            balance = float(c.get("balance", 0) or 0)
            msg += f"  {icono} {nombre}: ${balance:,.0f}\n"
        msg += f"\n💰 **Total en cuentas: ${total_cuentas:,.0f}**\n"

    # Presupuestos del mes
    if presupuestos:
        total_pres = sum(float(p.get("limite", 0) or 0) for p in presupuestos.values())
        msg += f"\n🎯 **Presupuestos {ahora.strftime('%B %Y').title()}:**\n"
        for nombre, info in presupuestos.items():
            limite = float(info.get("limite", 0) or 0)
            gastado = float(info.get("gastado", 0) or 0)
            restante = limite - gastado
            emoji = "✅" if restante >= 0 else "⚠️"
            msg += f"  {emoji} {nombre}: $${limite:,.0f} (gastado: ${gastado:,.0f}, libre: ${restante:,.0f})\n"
        msg += f"\n📊 **Total presupuestado: ${total_pres:,.0f}**\n"

        # Comparar con cuentas
        if total_cuentas > total_pres:
            libre = total_cuentas - total_pres
            msg += f"💡 **Libre (no asignado): ${libre:,.0f}**\n"
    else:
        msg += "\n🎯 No hay presupuestos para este mes.\n"

    return msg

def handle_analisis_financiero(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle financial analysis action."""
    from datetime import datetime
    from modules.db import listar_cuentas, obtener_balance_financiero, obtener_presupuestos_v2
    from modules.finance import reports

    ahora = datetime.now()
    mes_actual = ahora.strftime("%Y-%m")
    nombre_mes = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][ahora.month]

    # Liquidez en cuentas
    cuentas = listar_cuentas(usuario_id)
    liquidez = sum(float(c.get("balance", 0) or 0) for c in cuentas)

    # Balance del mes
    mes_neto, mes_ingresos, mes_gastos, _ = obtener_balance_financiero(usuario_id, mes_actual)

    # Presupuestos
    presupuestos = obtener_presupuestos_v2(usuario_id, mes_actual)

    msg = f"📊 **Análisis financiero - {nombre_mes} {ahora.year}**\n\n"

    # Liquidez
    msg += f"💰 **Liquidez en cuentas:** ${liquidez:,.0f}\n"

    # Flujo del mes
    msg += f"\n📈 **Flujo del mes:**\n"
    msg += f"  Ingresos: +${mes_ingresos:,.0f}\n"
    msg += f"  Gastos: -${mes_gastos:,.0f}\n"
    msg += f"  Neto: ${mes_neto:,.0f}\n"

    # Comparación presupuesto vs gasto
    if presupuestos:
        msg += f"\n🎯 **Presupuestos vs Gastado:**\n"
        total_pres = 0
        total_gastado = 0
        for nombre, info in presupuestos.items():
            limite = float(info.get("limite", 0) or 0)
            gastado = float(info.get("gastado", 0) or 0)
            restante = limite - gastado
            pct = (gastado / limite * 100) if limite > 0 else 0
            emoji = "✅" if restante >= 0 else "⚠️"
            total_pres += limite
            total_gastado += gastado
            msg += f"  {emoji} {nombre}: $${limite:,.0f} / $${gastado:,.0f} ({pct:.0f}%)\n"

        if total_pres > 0:
            msg += f"\n📊 Total: ${total_pres:,.0f} presupuestado, ${total_gastado:,.0f} gastado ({total_gastado/total_pres*100:.0f}%)\n"

            # Gastos sin presupuesto
            gasto_sin_presupuesto = mes_gastos - total_gastado
            if gasto_sin_presupuesto > 0:
                msg += f"\n⚠️ **Gastos sin categoría de presupuesto:** ${gasto_sin_presupuesto:,.0f}\n"
                msg += "💡 Considera agregar categorías para mejorar el seguimiento.\n"

            # Sobrante libre
            if liquidez > total_pres:
                msg += f"\n💡 **Libre (no asignado):** ${liquidez - total_pres:,.0f}\n"
        else:
            msg += "\n⚠️ No hay presupuestos configurados para este mes.\n"

    return msg

def handle_sobrante(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle surplus/sobrante action."""
    from datetime import datetime
    from modules.db import listar_cuentas, obtener_presupuestos_v2, obtener_resumen_presupuestos
    from modules.finance import reports

    cuentas = listar_cuentas(usuario_id)
    liquidez = sum(float(c.get("balance", 0) or 0) for c in cuentas)
    ahora = datetime.now()
    mes_actual = ahora.strftime("%Y-%m")

    presupuestos = obtener_presupuestos_v2(usuario_id, mes_actual)
    total_pres = sum(float(p.get("limite", 0) or 0) for p in presupuestos.values())

    libre = liquidez - total_pres

    msg = "💡 **Sobre el remanente:**\n\n"
    msg += f"Tus cuentas suman **${liquidez:,.0f}**.\n"
    msg += f"Tus techos de presupuesto para este mes suman **${total_pres:,.0f}**.\n"
    if libre > 0:
        msg += f"\n✅ Te quedan **${libre:,.0f}** libres (sin asignar a ningún presupuesto).\n"
        msg += "No es necesario crear un presupuesto con este monto — queda disponible en tus cuentas.\n"
    elif libre == 0:
        msg += "\n✅ Todo tu dinero está asignado a presupuestos.\n"
    else:
        msg += f"\n⚠️ Tus presupuestos exceden la liquidez por **${abs(libre):,.0f}**.\n"

    msg += "\n💡 Si quieres asignar este remanente a un presupuesto, usa:\n"
    msg += "`presupuesto Libre <monto>` o `presupuesto Reserva <monto>`"

    return msg

def handle_ajustar_balance(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle balance adjustment explanation action."""
    from datetime import datetime
    from modules.db import listar_cuentas, obtener_presupuestos_v2
    from modules.finance import reports

    cuentas = listar_cuentas(usuario_id)
    liquidez = sum(float(c.get("balance", 0) or 0) for c in cuentas)
    ahora = datetime.now()
    mes_actual = ahora.strftime("%Y-%m")

    presupuestos = obtener_presupuestos_v2(usuario_id, mes_actual)
    total_pres = sum(float(p.get("limite", 0) or 0) for p in presupuestos.values())

    msg = "💡 **Presupuestos vs Balance:**\n\n"
    msg += "Los presupuestos son **techos de gasto**, no representan dinero real en tus cuentas.\n\n"
    msg += f"📊 **Este mes ({ahora.strftime('%B')}):**\n"
    msg += f"  • Liquidez en cuentas: ${liquidez:,.0f}\n"
    msg += f"  • Techos presupuestarios: ${total_pres:,.0f}\n\n"

    if liquidez > total_pres:
        msg += f"✅ Tienes ${liquidez - total_pres:,.0f} libre (no asignado a ningún presupuesto).\n"
    elif liquidez < total_pres:
        msg += f"⚠️ Tus techos superan la liquidez por ${total_pres - liquidez:,.0f}.\n"
        msg += "Esto significa que planeas gastar más de lo que tienes disponible.\n"

    msg += "\n💡 Si quieres crear un presupuesto con el remanente disponible, usa:\n"
    msg += "`presupuesto Libre <monto>` o dime \"crea presupuesto Otros con lo que sobra\""

    return msg