from fastapi import APIRouter, HTTPException

from modules.finance.dashboard import obtener_resumen_dashboard

router = APIRouter(prefix="/api/widget")


@router.get("/resumen")
def obtener_resumen_widget(usuario_id: str = "default", mes: str | None = None):
    """Return the same live aggregates consumed by the dashboard endpoint."""
    return api_widget_dashboard(usuario_id=usuario_id, mes=mes)

@router.get("/dashboard")
def api_widget_dashboard(usuario_id: str = "", mes: str | None = None):
    """Endpoint único que devuelve TODO lo que necesita el widget iPhone.

    Optimizado para hacer UNA sola llamada HTTP desde el widget.
    Retorna:
        - total_balance_cuentas: suma de saldos de cuentas
        - cuentas: lista de objetos {nombre, disponible}
        - mes: nombre del mes y año (ej: "Octubre 2026")
        - total_ingresos: total de ingresos del mes
        - total_gastos: total de gastos del mes
        - presupuestos: lista de objetos {categoria, gastado, limite, excedido}

    El parámetro opcional `mes` (YYYY-MM) permite consultar un mes histórico;
    si se omite se usa el último mes con transacciones registradas. #
    """
    try:
        return obtener_resumen_dashboard(usuario_id or "default", mes=mes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas del widget: {e}",
        ) from e
