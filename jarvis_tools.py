# jarvis_tools.py
from modules.calendar_service import (
    crear_evento, listar_proximos_eventos, buscar_eventos, 
    obtener_evento, actualizar_evento, eliminar_evento,
    CrearEventoInput, BuscarEventoInput, ObtenerEventoInput, ActualizarEventoInput, EliminarEventoInput
)
from modules.finance_service import (
    obtener_saldos, registrar_movimiento, renombrar_cuenta,
    RegistrarMovimientoInput, RenombrarCuentaInput, ConsultarSaldosInput
)

CALENDAR_TOOLS = [
    crear_evento, listar_proximos_eventos, buscar_eventos, 
    obtener_evento, actualizar_evento, eliminar_evento
]

FINANCIAL_TOOLS = [
    obtener_saldos, registrar_movimiento, renombrar_cuenta
]

ALL_TOOLS = CALENDAR_TOOLS + FINANCIAL_TOOLS

TOOL_MAP = {
    "crear_evento": {"func": crear_evento, "input": CrearEventoInput},
    "listar_proximos_eventos": {"func": listar_proximos_eventos, "input": None},
    "buscar_eventos": {"func": buscar_eventos, "input": BuscarEventoInput},
    "obtener_evento": {"func": obtener_evento, "input": ObtenerEventoInput},
    "actualizar_evento": {"func": actualizar_evento, "input": ActualizarEventoInput},
    "eliminar_evento": {"func": eliminar_evento, "input": EliminarEventoInput},
    "obtener_saldos": {"func": obtener_saldos, "input": ConsultarSaldosInput},
    "registrar_movimiento": {"func": registrar_movimiento, "input": RegistrarMovimientoInput},
    "renombrar_cuenta": {"func": renombrar_cuenta, "input": RenombrarCuentaInput},
}
