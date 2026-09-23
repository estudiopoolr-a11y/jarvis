"""Budget parsers grouped by operation."""
from modules.nlp.parsers.budgets.bulk import (
    _parse_bloque_presupuesto_mensual,
    _parse_configuracion_masiva,
)
from modules.nlp.parsers.budgets.create import (
    _parse_presupuesto,
    _parse_presupuesto_multiple,
)
from modules.nlp.parsers.budgets.delete import _parse_borrar_presupuesto
from modules.nlp.parsers.budgets.update import (
    _parse_editar_presupuesto,
    _parse_presupuesto_modificar,
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
