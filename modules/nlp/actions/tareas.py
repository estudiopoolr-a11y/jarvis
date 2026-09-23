"""Task-related actions for NLP processing."""

def handle_completar_tarea(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle task completion action."""
    from modules.nlp.parsers import _parse_completar_tarea
    from modules.db import marcar_tarea_completada

    try:
        completada_texto = _parse_completar_tarea(texto_lc)
        if completada_texto:
            completada = marcar_tarea_completada(usuario_id, completada_texto)
            if completada:
                return f"✅ Tarea completada: *'{completada}'*. Avanza con el siguiente pendiente."
            return "⚠️ No encontré tarea que coincida."
        return None
    except Exception as e:
        return f"⚠️ Error al completar tarea: {e}"

def handle_nueva_tarea(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle new task creation action."""
    from modules.nlp.parsers import _parse_tarea
    from modules.db import guardar_tarea

    try:
        tarea_data = _parse_tarea(texto_lc)
        if tarea_data:
            guardar_tarea(usuario_id, tarea_data["tarea"], tarea_data["prioridad"], tarea_data["fecha_limite"])
            return f"📌 Tarea registrada: *{tarea_data['tarea']}* [Prioridad: {tarea_data['prioridad']}, Vence: {tarea_data['fecha_limite']}]"
        return None
    except Exception as e:
        return f"⚠️ Error al crear tarea: {e}"

def handle_recordatorio(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle reminder action."""
    from modules.nlp.parsers import _parse_recordatorio
    from modules.db import guardar_recordatorio

    try:
        recordatorio_data = _parse_recordatorio(texto_lc)
        if recordatorio_data:
            rem_id = guardar_recordatorio(usuario_id, recordatorio_data["texto"], recordatorio_data["dia"])
            if rem_id:
                return f"🔔 Recordatorio guardado: *{recordatorio_data['texto']}* el día *{recordatorio_data['dia']}*."
            return "⚠️ No se pudo guardar el recordatorio."
        return None
    except Exception as e:
        return f"⚠️ Error al crear recordatorio: {e}"

def handle_listar_recordatorios(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle list reminders action."""
    from modules.db import listar_recordatorios

    try:
        recordatorios = listar_recordatorios(usuario_id)
        if not recordatorios:
            return "🔔 No tienes recordatorios pendientes."
        msg = "🔔 **Tus recordatorios:**\n"
        for r in recordatorios:
            msg += f"  📌 Día {r.get('day')}/{r.get('month')}: {r.get('text')}\n"
        return msg
    except Exception as e:
        return f"⚠️ Error al listar recordatorios: {e}"

def handle_transacciones_futuras(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Crea una transacción programada si el parser coincide; si no, lista las pendientes."""
    from modules.nlp.parsers import _parse_transaccion_futura
    from modules.db import listar_transacciones_futuras, registrar_transaccion_futura

    try:
        futura = _parse_transaccion_futura(texto_lc)
        if futura:
            tx_id = registrar_transaccion_futura(
                usuario_id,
                futura.get("tipo", "expense"),
                futura["monto"],
                futura.get("categoria", "General"),
                futura["fecha"],
                descripcion=futura.get("descripcion", ""),
            )
            if tx_id:
                return (
                    f"📅 Transacción programada: **${futura['monto']:,.0f}** en "
                    f"*{futura.get('categoria', 'General')}* para *{futura['fecha']}*."
                )
            return "⚠️ Error al programar la transacción futura."

        futuras = listar_transacciones_futuras(usuario_id)
        if not futuras:
            return "📅 No hay transacciones programadas."
        msg = "📅 **Transacciones pendientes:**\n"
        for f in futuras:
            msg += f"  📌 {f.get('scheduled_date')}: ${f.get('amount', 0):,.0f} - {f.get('description', '')}\n"
        return msg
    except Exception as e:
        return f"⚠️ Error al listar transacciones futuras: {e}"

def handle_ultimas_transacciones(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle last transactions action."""
    from modules.db import listar_transacciones_recientes

    try:
        transacciones = listar_transacciones_recientes(usuario_id, 10)
        if not transacciones:
            return "📋 No hay transacciones registradas."
        msg = "📋 **Últimas transacciones:**\n"
        for t in transacciones:
            fecha = t.get("fecha", "")[:10]
            tipo = t.get("tipo", "?")
            monto = float(t.get("monto", 0))
            desc = t.get("descripcion", "")[:30]
            emoji = "💸" if tipo == "expense" else "💰" if tipo == "income" else "🔄"
            signo = "-" if tipo == "expense" else "+"
            msg += f"  {emoji} {fecha}: {signo}${monto:,.0f} ({desc})\n"
        return msg
    except Exception as e:
        return f"⚠️ Error al listar transacciones: {e}"
