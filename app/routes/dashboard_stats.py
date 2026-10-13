from fastapi import APIRouter, HTTPException

from modules.finance.dashboard import obtener_resumen_dashboard

router = APIRouter()


@router.get("/api/finanzas/resumen")
def api_finanzas_resumen(usuario_id: str = "default", mes: str | None = None):
    """Resumen financiero mensual.

    mes (YYYY-MM) es opcional; sin él se usa el último mes con datos. #
    """
    try:
        return obtener_resumen_dashboard(usuario_id, mes=mes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas de Firebase: {e}",
        ) from e