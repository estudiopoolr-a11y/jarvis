from modules.db import (
    registrar_prestamo, 
    registrar_transaccion, 
    actualizar_cuenta,
    obtener_balance_financiero
)
from modules.ai import pensar_respuesta

async def ejecutar_intencion_nlp(intent_data: dict, user_id: str = "default") -> str:
    """
    Ejecuta la acción correspondiente basada en la intención clasificada por el NLP.
    Retorna el mensaje de respuesta formateado para Telegram.
    """
    intent = intent_data.get("intent")
    texto = intent_data.get("texto", "")
    
    try:
        if intent == "REGISTRAR_PRESTAMO":
            persona = intent_data.get("persona", "desconocido")
            monto = intent_data.get("monto", 0.0)
            tipo = intent_data.get("tipo", "prestado")
            nota = intent_data.get("concepto", intent_data.get("nota", ""))
            
            # Usar la función de DB directamente
            prestamo_id = registrar_prestamo(
                user_id, 
                persona, 
                monto, 
                None, 
                f"Tipo: {tipo} | {nota}"
            )
            
            if prestamo_id:
                return f"✅ **Préstamo registrado**: ${monto:,.0f} COP a {persona} ({tipo})."
            return "❌ Hubo un problema al registrar el préstamo."

        elif intent == "REGISTRAR_GASTO":
            monto = intent_data.get("monto", 0.0)
            categoria = intent_data.get("categoria", "Sin categoría")
            cuenta = intent_data.get("cuenta", "Efectivo")
            descripcion = intent_data.get("descripcion", "")
            
            # Buscar ID de cuenta por nombre si es necesario, o usar el nombre directamente si la DB lo soporta
            # Para este flujo, intentamos registrar con el nombre de la cuenta
            tx_id = registrar_transaccion(
                user_id, 
                monto, 
                categoria, 
                cuenta, 
                descripcion
            )
            
            if tx_id:
                return f"💸 **Gasto registrado**: ${monto:,.0f} COP en {categoria} ({cuenta})."
            return "❌ Error al registrar el gasto en Kebo."

        elif intent == "ACTUALIZAR_CUENTA_KEBO":
            cuenta_nombre = intent_data.get("cuenta", "")
            nuevo_saldo = intent_data.get("nuevo_saldo", 0.0)
            
            if not cuenta_nombre:
                return "❌ Por favor indica la cuenta a actualizar."
            
            # Nota: actualizar_cuenta requiere account_id. Necesitamos buscar el ID por nombre.
            from modules.db import listar_cuentas
            cuentas = listar_cuentas(user_id)
            cuenta_id = next((c["_id"] for c in cuentas if c.get("nombre", "").lower() == cuenta_nombre.lower()), None)
            
            if cuenta_id:
                ok = actualizar_cuenta(user_id, cuenta_id, {"balance": nuevo_saldo})
                if ok:
                    return f"🏦 **Saldo actualizado**: {cuenta_nombre} fijado en ${nuevo_saldo:,.0f} COP."
            
            return f"❌ No se encontró la cuenta '{cuenta_nombre}' o no se pudo actualizar."

        elif intent == "CONSULTAR_BALANCE":
            filtro = intent_data.get("filtro", "general")
            resumen = obtener_balance_financiero(user_id)
            
            if filtro == "prestamos_por_cobrar":
                from modules.db import obtener_total_por_cobrar
                total = obtener_total_por_cobrar(user_id)
                return f"💰 **Préstamos por cobrar**: ${total:,.0f} COP."
            return f"🏦 **Balance Financiero**:\n{resumen}"

        elif intent == "CONVERSACION_GENERAL":
            return pensar_respuesta(texto)

        else:
            return "🤔 No estoy seguro de cómo ayudarte con eso, pero puedo registrar gastos, préstamos o darte tu balance."

    except Exception as e:
        print(f"[IntentHandler Error] {e}")
        return f"⚠️ Ocurrió un error al procesar la acción: {str(e)}"
