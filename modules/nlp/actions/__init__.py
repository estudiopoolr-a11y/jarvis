"""Actions grouped by NLP responsibility."""

from .finanzas import (
    handle_listar_categorias,
    handle_analisis_financiero,
    handle_sobrante,
    handle_ajustar_balance,
)
from .presupuestos import (
    handle_bloque_presupuesto_mensual,
    handle_configuracion_masiva,
    handle_tareas_pendientes,
    handle_balance_finanzas,
    handle_cuentas_kebo,
)
from .tareas import (
    handle_completar_tarea,
    handle_nueva_tarea,
    handle_recordatorio,
    handle_listar_recordatorios,
    handle_transacciones_futuras,
    handle_ultimas_transacciones,
)
from .sistema import (
    handle_limpiar_base_datos,
    handle_transaccion,
    handle_presupuesto_simple,
    handle_meta_financiera,
    handle_perfil_usuario,
    handle_pago_fijo,
    handle_tasa_cambio,
)
