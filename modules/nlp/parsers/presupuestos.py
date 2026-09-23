"""Compatibility facade. Implementation lives in modules.nlp.parsers.budgets."""
from modules.nlp.parsers.budgets import (
    _parse_bloque_presupuesto_mensual,
    _parse_borrar_presupuesto,
    _parse_configuracion_masiva,
    _parse_editar_presupuesto,
    _parse_presupuesto,
    _parse_presupuesto_modificar,
    _parse_presupuesto_multiple,
    _parse_renombrar_presupuesto,
)

__all__ = [
    "_parse_bloque_presupuesto_mensual",
    "_parse_borrar_presupuesto",
    "_parse_configuracion_masiva",
    "_parse_editar_presupuesto",
    "_parse_presupuesto",
    "_parse_presupuesto_modificar",
    "_parse_presupuesto_multiple",
    "_parse_renombrar_presupuesto",
]
