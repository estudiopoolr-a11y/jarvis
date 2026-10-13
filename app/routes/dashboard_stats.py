from fastapi import APIRouter, HTTPException

from modules.finance.dashboard import obtener_resumen_dashboard

router = APIRouter()


@router.get("/api/finanzas/resumen")
def api_finanzas_resumen(usuario_id: str = "default"):
    try:
        return obtener_resumen_dashboard(usuario_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas de Firebase: {e}",
        ) from e
