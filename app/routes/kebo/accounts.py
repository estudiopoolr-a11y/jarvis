"""Kebo HTTP routes: accounts."""
from app.api import app

@app.get("/api/kebo/cuentas")
def api_kebo_cuentas(usuario_id: str = "default"):
    """API para widget iPhone: lista de cuentas con balances (NUEVA ESTRUCTURA KEBO)."""
    import traceback
    try:
        from modules.db import listar_cuentas
        cuentas = listar_cuentas(usuario_id)
        return {
            "cuentas": cuentas,
            "total_balance": sum(c.get("balance", 0) for c in cuentas)
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/tasas")
def api_kebo_tasas(usuario_id: str = "default"):
    """Lista tasas de cambio guardadas."""
    try:
        from modules.db import obtener_tasas_cambio, TASAS_DEFAULT
        tasas = obtener_tasas_cambio(usuario_id)
        # Combinar con defaults
        for m, rate in TASAS_DEFAULT.items():
            if m not in tasas:
                tasas[m] = {"rate": rate}
        return {"tasas": tasas}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/balance-multimoneda")
def api_kebo_balance_multimoneda(usuario_id: str = "default", moneda: str = "COP"):
    """Balance total convertido a una moneda específica."""
    try:
        from modules.db import obtener_balance_total_multimoneda
        total = obtener_balance_total_multimoneda(usuario_id, moneda)
        return {"moneda": moneda, "total": total}
    except Exception as e:
        return {"error": True, "message": str(e)}
