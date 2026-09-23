"""Paquete para gestión de transacciones.

Reexporta las funciones públicas de los submódulos para mantener compatibilidad.
"""

from modules.finance.transactions.create import registrar_transaccion_v2
from modules.finance.transactions.transfer import registrar_transferencia
from modules.finance.transactions.future import (
    registrar_transaccion_futura,
    ejecutar_transacciones_futuras,
    listar_transacciones_futuras,
)
from modules.finance.transactions.recent import listar_transacciones_recientes
from modules.finance.transactions.search import (
    buscar_transacciones,
    obtener_sugerencias_payee,
    obtener_sugerencias_categoria,
)
from modules.finance.transactions.split import registrar_split

__all__ = [
    "registrar_transaccion_v2",
    "registrar_transferencia",
    "registrar_transaccion_futura",
    "ejecutar_transacciones_futuras",
    "listar_transacciones_futuras",
    "listar_transacciones_recientes",
    "buscar_transacciones",
    "registrar_split",
    "obtener_sugerencias_payee",
    "obtener_sugerencias_categoria",
]
