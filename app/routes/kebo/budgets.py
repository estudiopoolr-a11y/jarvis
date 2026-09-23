"""Kebo HTTP routes: budgets."""
from app.api import app

@app.get("/api/kebo/alertas")
def api_kebo_alertas(usuario_id: str = "default"):
    """API para widget: alertas de presupuesto activas."""
    try:
        from modules.db import obtener_alertas_presupuesto
        alertas = obtener_alertas_presupuesto(usuario_id)
        return {"alertas": alertas}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/presupuestos")
def api_kebo_presupuestos(usuario_id: str = "default", mes: str = None):
    """API para widget iPhone: presupuestos con gastado del mes (NUEVA ESTRUCTURA KEBO)."""
    import traceback
    from datetime import datetime
    try:
        from modules.db import obtener_presupuestos_v2
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        presupuestos = obtener_presupuestos_v2(usuario_id, mes)
        return {"mes": mes, "presupuestos": presupuestos}
    except Exception as e:
        return {"error": True, "message": str(e)}


# ==================== ENDPOINTS NUEVAS FEATURES KEBO ====================

@app.get("/api/kebo/subcategorias")
def api_kebo_subcategorias(usuario_id: str = "default", categoria: str = ""):
    """Lista sub-categorías de una categoría padre."""
    try:
        from modules.db import listar_subcategorias, crear_subcategorias_predefinidas
        if not categoria:
            return {"error": True, "message": "Parámetro 'categoria' requerido"}
        subs = listar_subcategorias(usuario_id, categoria)
        return {"categoria": categoria, "subcategorias": subs}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/rollover")
def api_kebo_rollover(usuario_id: str = "default"):
    """Aplica rollover del presupuesto del mes anterior."""
    try:
        from modules.db import aplicar_rollover_presupuesto
        rollovers = aplicar_rollover_presupuesto(usuario_id)
        return {"rollovers_aplicados": rollovers}
    except Exception as e:
        return {"error": True, "message": str(e)}
