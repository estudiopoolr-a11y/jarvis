"""Budget actions for NLP processing."""

def handle_bloque_presupuesto_mensual(prompt_usuario: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle monthly budget block action."""
    from modules.nlp.parsers import _parse_bloque_presupuesto_mensual
    from modules.db import establecer_presupuesto_mes, registrar_transaccion_v2
    from modules.nlp.router import _NOMBRES_MESES
    from datetime import datetime

    try:
        parsed = _parse_bloque_presupuesto_mensual(prompt_usuario)
        if parsed:
            acciones, mes_num, año = parsed

            result = []
            for accion in acciones:
                try:
                    if accion[0] == 'presupuesto':
                        _, categoria, monto, mes, año_mes = accion
                        if establecer_presupuesto_mes(usuario_id, categoria, monto, año_mes, mes):
                            result.append(f"✅ Presupuesto para *{categoria}* = **${monto:,.0f}** ({_NOMBRES_MESES[mes]} {año_mes})")
                        else:
                            result.append(f"⚠️ Error estableciendo presupuesto para *{categoria}*")
                    elif accion[0] == 'gasto':
                        _, categoria, monto, fecha = accion
                        tx_id = registrar_transaccion_v2(
                            usuario_id, "expense", monto, categoria,
                            descripcion=f"Gasto {categoria} ({fecha[:7]})",
                            cuenta_nombre="Efectivo", fecha=fecha
                        )
                        if tx_id:
                            result.append(f"💸 Gasto registrado: **-${monto:,.0f}** en *{categoria}* ({fecha})")
                        else:
                            result.append(f"⚠️ Error registrando gasto de *{categoria}*")
                except Exception as e:
                    print(f"Error en accion {accion}: {e}")
                    result.append(f"⚠️ Error procesando *{accion[1]}*: {e}")

            return f"🤖 **[BLOQUE DE PRESUPUESTO Y GASTOS CARGADO]**\n\n" + "\n".join(result)
    except Exception as e:
        print(f"Error parseando bloque presupuesto/gastos: {e}")
        return f"⚠️ Detecté tu bloque de presupuestos pero falló al procesarlo: `{e}`\n*Intenta separar categorías una por una si persiste.*"

def handle_configuracion_masiva(prompt_usuario: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle massive configuration action."""
    from modules.nlp.parsers import _parse_configuracion_masiva
    from modules.db import limpiar_y_cargar_datos_dinamicos

    try:
        parsed = _parse_configuracion_masiva(prompt_usuario)
        if parsed:
            presupuestos, transacciones = parsed
            result = limpiar_y_cargar_datos_dinamicos(usuario_id, presupuestos, transacciones)
            return f"🤖 **[CONFIGURACIÓN MASIVA CARGADA]**\n{result}"
        return "⚠️ No pude parsear la configuración. Verifica el formato."
    except Exception as e:
        return f"⚠️ Error procesando configuración masiva: {e}"

def handle_tareas_pendientes(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle pending tasks action."""
    from modules.db import obtener_tareas_pendientes

    try:
        tareas = obtener_tareas_pendientes(usuario_id)
        if not tareas:
            return "📋 No tienes tareas pendientes."
        lista = "\n".join([f"• [{t['prioridad']}] {t['tarea']} (Vence: {t['fecha_limite']})" for t in tareas])
        return f"📋 **Tareas pendientes ({len(tareas)}):**\n{lista}"
    except Exception as e:
        return f"⚠️ Error obteniendo tareas pendientes: {e}"

def handle_balance_finanzas(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle balance/finances query action."""
    from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos

    try:
        balance, ingresos, gastos, _ = obtener_balance_financiero(usuario_id)
        presupuestos = obtener_resumen_presupuestos(usuario_id)
        msg = f"💰 **Balance financiero:**\n- Ingresos: +${ingresos:,.0f}\n- Gastos: -${gastos:,.0f}\n- Neto: ${balance:,.0f}\n"
        if presupuestos:
            msg += "- Presupuestos: " + ", ".join([f"{k}: ${v:,.0f}" for k, v in presupuestos.items()])
        else:
            msg += "- No hay presupuestos establecidos."
        return msg
    except Exception as e:
        return f"⚠️ Error obteniendo balance financiero: {e}"

def handle_cuentas_kebo(texto_lc: str, usuario_id: str, es_audio: bool = False) -> str:
    """Handle Kebo accounts management action."""
    import re
    from datetime import datetime
    from modules.db import listar_cuentas, crear_cuenta

    try:
        if any(k in texto_lc for k in ["cuenta", "cuentas"]):
            # Listar cuentas: "mis cuentas", "lista mis cuentas", "ver cuentas"
            if any(k in texto_lc for k in ["mis", "lista", "mostrar", "ver", "cuales", "cuáles"]):
                cuentas = listar_cuentas(usuario_id)
                if not cuentas:
                    return "💳 No tienes cuentas registradas. Di: 'crea cuenta [nombre]' para agregar una."
                msg = "💳 **Tus cuentas:**\n"
                total = 0.0
                for c in cuentas:
                    icono = c.get("icon") or c.get("icono", "💳")
                    balance = float(c.get("balance", 0))
                    total += balance
                    signo = "+" if balance >= 0 else ""
                    nombre = c.get('nombre')
                    institution = c.get("institution", "")
                    last4 = c.get("bank_last4", "")
                    banco_str = f" ({institution}{' ****' + last4 if last4 else ''})" if institution else ""
                    msg += f"  {icono} {nombre}{banco_str}: {signo}${balance:,.0f}\n"
                msg += f"\n💰 **Balance total: ${total:,.0f}**"
                return msg

            # Crear cuenta: "crea cuenta Nequi", "nueva cuenta débito 200k"
            crear_match = re.search(
                r'(?:crea|crear|nueva|agrega|agregar)\s+cuenta\s+(?:llamada\s+|de\s+)?(.+?)(?:\s+con\s+([\d,.]+))?\s*$',
                texto_lc
            )
            if crear_match:
                resto = crear_match.group(1).strip()
                saldo_inicial = 0.0
                if crear_match.group(2):
                    saldo_inicial = float(crear_match.group(2).replace(',', ''))

                # Detectar tipo
                tipo = "cash"
                icono = "💵"
                color = "#10b981"
                if any(k in resto for k in ["credito", "crédito", "credit"]):
                    tipo = "credit"
                    icono = "💳"
                    color = "#ef4444"
                elif any(k in resto for k in ["debito", "débito", "debit", "nequi", "daviplata", "bancolombia"]):
                    tipo = "debit"
                    icono = "💜"
                    color = "#8b5cf6"
                elif any(k in resto for k in ["ahorro", "ahorros", "savings"]):
                    tipo = "savings"
                    icono = "🏦"
                    color = "#3b82f6"

                # Limpiar nombre (quitar la palabra "tipo X")
                nombre = re.sub(r'\s+tipo\s+\w+', '', resto).strip()
                nombre = nombre.title()

                if not nombre:
                    return "⚠️ Necesito el nombre. Ej: 'crea cuenta Nequi tipo débito'"

                # Detectar banco (institution) y últimos 4 dígitos
                institution = ""
                bank_last4 = ""
                bancos_conocidos = ["bancolombia", "davivienda", "bbva", "colpatria", "bogota", "popular", "nequi", "daviplata"]
                for banco in bancos_conocidos:
                    if banco in resto:
                        institution = banco.title()
                        break
                last4_match = re.search(r'(?:terminada|acabada)\s+en\s+(\d{4})', resto)
                if last4_match:
                    bank_last4 = last4_match.group(1)

                cuenta_id = crear_cuenta(usuario_id, nombre, tipo, saldo_inicial, icono, color,
                                         currency="COP", institution=institution, bank_last4=bank_last4)
                if cuenta_id:
                    saldo_str = f" con ${saldo_inicial:,.0f}" if saldo_inicial else ""
                    banco_str = f" ({institution})" if institution else ""
                    last4_str = f" **** {bank_last4}" if bank_last4 else ""
                    return f"✅ Cuenta creada: {icono} **{nombre}** ({tipo}){saldo_str}{banco_str}{last4_str}."
                else:
                    return "⚠️ Error al crear la cuenta."

            # Ver saldo de cuenta específica: "saldo nequi", "cuanto tengo en efectivo"
            saldo_match = re.search(r'(?:saldo|balance|cuanto\s+tengo|cuánto\s+tengo)\s+(?:en\s+|de\s+)?(.+)', texto_lc)
            if saldo_match:
                nombre_buscar = saldo_match.group(1).strip().title()
                cuentas = listar_cuentas(usuario_id)
                for c in cuentas:
                    if nombre_buscar.lower() in c.get('nombre', '').lower():
                        balance = float(c.get("balance", 0))
                        icono = c.get("icono", "💳")
                        signo = "+" if balance >= 0 else ""
                        return f"{icono} **{c.get('nombre')}**: {signo}${balance:,.0f}"
                return f"⚠️ No encontré la cuenta '{nombre_buscar}'."

        return None
    except Exception as e:
        return f"⚠️ Error gestionando cuentas: {e}"