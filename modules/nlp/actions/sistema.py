"""System-level actions for NLP processing."""

def handle_limpiar_base_datos(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle database cleanup action."""
    from modules.db import limpiar_y_cargar_datos_dinamicos

    try:
        result = limpiar_y_cargar_datos_dinamicos(usuario_id, {}, [])
        return f"🤖 **[SISTEMA REINICIADO POR JARVIS]**\n{result}\n\n*He limpiado la basura anterior.*"
    except Exception as e:
        return f"⚠️ Error al limpiar base de datos: {e}"

def handle_transaccion(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle transaction registration action."""
    from modules.nlp.parsers import _parse_transaccion, _parse_split
    from modules.db import registrar_transaccion_v2, registrar_split

    try:
        split_data = _parse_split(texto_lc)
        if split_data:
            parent_id, msg = registrar_split(
                usuario_id,
                split_data["monto_total"],
                split_data["splits"],
            )
            if parent_id:
                return f"✂️ {msg}"
            return f"⚠️ {msg}"

        transaccion = _parse_transaccion(texto_lc)
        if transaccion:
            monto = transaccion["monto"]
            cat = transaccion["categoria"]
            tipo = transaccion["tipo"]
            tipo_db = "expense" if tipo == "gasto" else "income"

            tx_id = registrar_transaccion_v2(
                usuario_id, tipo_db, monto, cat,
                descripcion=transaccion.get("payee", "Registro por voz"),
                cuenta_nombre="Efectivo",
                payee=transaccion.get("payee", ""),
                fee=transaccion.get("fee", 0.0),
                status=transaccion.get("status", "cleared"),
                tags=transaccion.get("tags", [])
            )
            if tx_id:
                if tipo == "gasto":
                    msg = f"💸 Gasto registrado: **-${monto:,.0f}** en *{cat}*."
                    if transaccion.get("fee"):
                        msg += f" (Comisión: ${transaccion['fee']:,.0f})"
                    if transaccion.get("tags"):
                        msg += f" {' '.join(transaccion['tags'])}"
                    return msg
                else:
                    return f"💰 Ingreso registrado: **+${monto:,.0f}** en *{cat}*."
            else:
                return "⚠️ Error al registrar transacción. Intenta de nuevo."
        return None
    except Exception as e:
        return f"⚠️ Error al registrar transacción: {e}"

def handle_presupuesto_simple(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle simple budget creation action."""
    from modules.nlp.parsers import _parse_presupuesto
    from modules.db import establecer_presupuesto, establecer_presupuesto_mes
    from datetime import datetime
    import re

    try:
        presupuesto_data = _parse_presupuesto(texto_lc)
        if presupuesto_data:
            mes_match = re.search(r'\b(?:en|para|del?)\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b', texto_lc)
            year_match = re.search(r'\b(20\d{2})\b', texto_lc)

            if mes_match:
                meses = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
                         "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
                mes_num = meses[mes_match.group(1)]
                year = year_match.group(1) if year_match else str(datetime.now().year)
                establecer_presupuesto_mes(usuario_id, presupuesto_data["categoria"], presupuesto_data["limite"], year, f"{mes_num:02d}")
                return f"🎯 Presupuesto: *{presupuesto_data['categoria']}* = **${presupuesto_data['limite']:,.0f}** (para {mes_match.group(1).title()} {year})"
            else:
                establecer_presupuesto(usuario_id, presupuesto_data["categoria"], presupuesto_data["limite"])
                return f"🎯 Presupuesto: *{presupuesto_data['categoria']}* = **${presupuesto_data['limite']:,.0f}**"
        return None
    except Exception as e:
        return f"⚠️ Error al crear presupuesto: {e}"

def handle_meta_financiera(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle financial goal/meta action."""
    from modules.nlp.parsers import _parse_meta
    from modules.db import guardar_meta, obtener_balance_financiero, proyectar_meta

    try:
        meta_data = _parse_meta(texto_lc)
        if meta_data:
            guardar_meta(usuario_id, meta_data["nombre"], meta_data["monto"], meta_data["fecha"])

            balance, ingresos, gastos, _ = obtener_balance_financiero(usuario_id)
            capacidad_mensual = max(0, ingresos - gastos) / 1

            proy = proyectar_meta({"monto_objetivo": meta_data["monto"], "monto_actual": 0, "fecha_limite": meta_data["fecha"]}, capacidad_mensual)

            msg = f"🎯 **META CREADA**\n\n"
            msg += f"✅ **{meta_data['nombre']}**\n"
            msg += f"   Meta: ${meta_data['monto']:,.0f}\n"
            if meta_data["fecha"]:
                msg += f"   📅 Fecha límite: {meta_data['fecha']}\n"
            msg += f"   💰 Tu capacidad de ahorro: ${capacidad_mensual:,.0f}/mes\n"

            if proy.get("atrasado") and meta_data["fecha"]:
                msg += f"\n⚠️ **ALERTA:** Necesitas ahorrar ${proy['ahorro_necesario']:,.0f}/mes para llegar a tiempo\n"
                msg += f"💡 Reduce gastos o aumenta ingresos en ${proy['ahorro_necesario'] - capacidad_mensual:,.0f}/mes"

            return msg
        return None
    except Exception as e:
        return f"⚠️ Error al crear meta: {e}"

def handle_perfil_usuario(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle user profile update action."""
    from modules.nlp.parsers import _parse_perfil
    from modules.db import guardar_perfil

    try:
        perfil_data = _parse_perfil(texto_lc)
        if perfil_data:
            guardar_perfil(usuario_id, **perfil_data)
            campo = list(perfil_data.keys())[0]
            valor = list(perfil_data.values())[0]
            return f"👤 **Perfil actualizado:** {campo} = {valor}"
        return None
    except Exception as e:
        return f"⚠️ Error al actualizar perfil: {e}"

def handle_pago_fijo(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle fixed payment action."""
    from modules.nlp.parsers import _parse_pago_fijo
    from modules.db import guardar_pago_fijo

    try:
        pago_fijo = _parse_pago_fijo(texto_lc)
        if pago_fijo:
            guardar_pago_fijo(usuario_id, pago_fijo["nombre"], pago_fijo["monto"], pago_fijo["dia_mes"])
            return f"⏰ **Pago fijo creado:** {pago_fijo['nombre']} = ${pago_fijo['monto']:,.0f} (día {pago_fijo['dia_mes']} de cada mes)"
        return None
    except Exception as e:
        return f"⚠️ Error al crear pago fijo: {e}"

def handle_tasa_cambio(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle exchange rate update action."""
    from modules.nlp.parsers import _parse_tasa_cambio
    from modules.db import guardar_tasa_cambio

    try:
        tasa_data = _parse_tasa_cambio(texto_lc)
        if tasa_data:
            guardar_tasa_cambio(usuario_id, tasa_data["moneda"], tasa_data["tasa"])
            return f"💱 Tasa de {tasa_data['moneda']} actualizada a *{tasa_data['tasa']:,.2f}* COP."
        return None
    except Exception as e:
        return f"⚠️ Error al actualizar tasa: {e}"
