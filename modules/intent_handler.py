import logging
from modules.db import (
    registrar_prestamo,
    registrar_transaccion,
    actualizar_cuenta,
)
from modules.ai import pensar_respuesta

logger = logging.getLogger('jarvis.intent_handler')

async def ejecutar_intencion_nlp(intent_data: dict, user_id: str = 'default') -> str:
    try:
        intent = intent_data.get('intent')
        texto = intent_data.get('texto', '')
        if intent_data.get('respuesta_directa'):
            return intent_data.get('respuesta_directa')

        if intent == 'REGISTRAR_PRESTAMO':
            persona = intent_data.get('persona', 'desconocido')
            monto = intent_data.get('monto', 0.0)
            tipo = intent_data.get('tipo', 'prestado')
            nota = intent_data.get('concepto', intent_data.get('nota', ''))
            prestamo_id = registrar_prestamo(
                user_id, persona, monto, None, f'Tipo: {tipo} | {nota}'
            )
            if prestamo_id:
                return f'Ok prestamo registrado {monto:,.0f}'
            return 'Error prestamo'

        elif intent == 'REGISTRAR_GASTO':
            monto = intent_data.get('monto', 0.0)
            categoria = intent_data.get('categoria', 'Sin categoria')
            cuenta = intent_data.get('cuenta', 'Efectivo')
            descripcion = intent_data.get('descripcion', '')
            tx_id = registrar_transaccion(user_id, monto, categoria, cuenta, descripcion)
            if tx_id:
                return f'Gasto registrado {monto:,.0f}'
            return 'Error gasto'

        elif intent == 'ACTUALIZAR_CUENTA_KEBO':
            cuenta_nombre = intent_data.get('cuenta', '')
            nuevo_saldo = intent_data.get('nuevo_saldo', 0.0)
            if not cuenta_nombre:
                return 'Error cuenta'
            from modules.db import listar_cuentas
            cuentas = listar_cuentas(user_id)
            cuenta_id = next(
                (c['_id'] for c in cuentas if c.get('nombre', '').lower() == cuenta_nombre.lower()),
                None
            )
            if cuenta_id:
                ok = actualizar_cuenta(user_id, cuenta_id, {'balance': nuevo_saldo})
                if ok:
                    return f'Saldo actualizado {nuevo_saldo:,.0f}'
            return f'No se encontro cuenta'

        elif intent == 'CONVERSACION_GENERAL':
            return pensar_respuesta(texto)

        else:
            return 'No entiendo esa intencion'

    except Exception as e:
        logger.error(f'Error ejecutando intencion NLP: {e}')
        return 'Error interno'
