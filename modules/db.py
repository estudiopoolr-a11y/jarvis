"""Fachada de compatibilidad para Firestore.

La implementación vive en modules/firestore, modules/finance, modules/goals y modules/reminders.
"""
from modules.finance.accounts import actualizar_balance_cuenta, crear_cuenta, listar_cuentas
from modules.finance.analysis import (
    exportar_csv,
    exportar_json_completo,
    obtener_alertas_presupuesto,
    obtener_balance_v2,
    obtener_estadisticas,
)
from modules.finance.budgets import (
    actualizar_presupuesto_categoria,
    aplicar_rollover_presupuesto,
    eliminar_presupuesto_mes,
    eliminar_todos_presupuestos_mes,
    establecer_presupuesto_mes,
    modificar_presupuesto_mes,
    obtener_presupuestos_mes,
    obtener_presupuestos_v2,
    renombrar_presupuesto_mes,
)
from modules.finance.categories import (
    _cat_exacta,
    _coincidir_categoria,
    _normalizar_cat_str,
    crear_categoria,
    crear_categorias_predefinidas,
    crear_subcategoria,
    crear_subcategorias_predefinidas,
    listar_categorias,
    listar_subcategorias,
)
from modules.finance.currency import (
    MONEDAS_SIMBOLO,
    TASAS_DEFAULT,
    convertir_monto,
    guardar_tasa_cambio,
    obtener_balance_total_multimoneda,
    obtener_tasas_cambio,
)
from modules.finance.legacy import (
    actualizar_progreso_meta,
    deduplicar_gastos,
    eliminar_meta,
    eliminar_pago_fijo,
    establecer_presupuesto,
    guardar_mensaje,
    guardar_meta,
    guardar_pago_fijo,
    guardar_perfil,
    guardar_tarea,
    limpiar_y_cargar_datos_dinamicos,
    marcar_tarea_completada,
    modificar_presupuesto,
    obtener_balance_financiero,
    obtener_contexto_financiero,
    obtener_metas,
    obtener_pagos_fijos,
    obtener_perfil,
    obtener_resumen_presupuestos,
    obtener_tareas_pendientes,
    proyectar_meta,
    registrar_transaccion,
)
from modules.finance.loans import (
    eliminar_prestamo,
    listar_prestamos,
    obtener_total_por_cobrar,
    registrar_pago_prestamo,
    registrar_prestamo,
)
from modules.finance.transactions import (
    buscar_transacciones,
    ejecutar_transacciones_futuras,
    listar_transacciones_futuras,
    listar_transacciones_recientes,
    obtener_sugerencias_categoria,
    obtener_sugerencias_payee,
    registrar_split,
    registrar_transaccion_futura,
    registrar_transaccion_v2,
    registrar_transferencia,
)
from modules.firestore.client import USUARIO_PRINCIPAL, _get_user_ref, get_db, inicializar_firebase
from modules.firestore.users import ensure_user
from modules.goals.service import agregar_aporte_meta, guardar_meta_v2, listar_metas_v2
from modules.reminders.service import (
    ejecutar_recurrentes,
    guardar_recordatorio,
    guardar_recurrente,
    listar_recordatorios,
    listar_recurrentes,
    marcar_recordatorio_hecho,
    obtener_recordatorios_hoy,
)


def __getattr__(name):
    if name == "db":
        from modules.firestore import client as fb
        return fb.db
    raise AttributeError(f"module 'modules.db' has no attribute {name!r}")
