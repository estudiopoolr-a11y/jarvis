import os
import sys
from pathlib import Path

from fastapi import File, Form, UploadFile
from fastapi.responses import HTMLResponse

from app.api import USUARIO_PRINCIPAL, ComandoPayload, app
from modules.ai import pensar_respuesta, pensar_respuesta_imagen, procesar_intencion_natural
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos, obtener_tareas_pendientes

# ==================== PRÉSTAMOS ====================

@app.post("/api/prestamos/registrar")
def api_registrar_prestamo(payload: dict):
    """Registra un nuevo préstamo.

    Body: {"usuario_id": "...", "persona": "...", "monto": 30000,
           "fecha": "2026-08-10", "nota": "..."}
    """
    try:
        from modules.db import registrar_prestamo
        usuario_id = payload.get("usuario_id", "default")
        persona = payload.get("persona", "").strip()
        monto = float(payload.get("monto", 0))
        fecha = payload.get("fecha")
        nota = payload.get("nota", "")

        if not persona or monto <= 0:
            return {"error": True, "message": "persona y monto (>0) son requeridos"}

        prestamo_id = registrar_prestamo(usuario_id, persona, monto, fecha, nota)
        if not prestamo_id:
            return {"error": True, "message": "No se pudo registrar el préstamo"}

        return {"status": "ok", "id": prestamo_id, "persona": persona, "monto": monto}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.post("/api/prestamos/pagar")
def api_registrar_pago_prestamo(payload: dict):
    """Registra un pago (parcial o total) de un préstamo.

    Body: {"usuario_id": "...", "prestamo_id": "...", "monto_pago": 10000,
           "fecha": "2026-09-01"}
    """
    try:
        from modules.db import registrar_pago_prestamo
        usuario_id = payload.get("usuario_id", "default")
        prestamo_id = payload.get("prestamo_id", "").strip()
        monto_pago = float(payload.get("monto_pago", 0))
        fecha = payload.get("fecha")

        if not prestamo_id or monto_pago <= 0:
            return {"error": True, "message": "prestamo_id y monto_pago (>0) son requeridos"}

        resultado = registrar_pago_prestamo(usuario_id, prestamo_id, monto_pago, fecha)
        if not resultado:
            return {"error": True, "message": "No se pudo registrar el pago (verifica prestamo_id)"}

        return {"status": "ok", **resultado}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/prestamos/listar")
def api_listar_prestamos(usuario_id: str = "default", solo_pendientes: bool = False):
    """Lista préstamos. solo_pendientes=true filtra a los no pagados."""
    try:
        from modules.db import listar_prestamos, obtener_total_por_cobrar
        prestamos = listar_prestamos(usuario_id, solo_pendientes=solo_pendientes)
        total_por_cobrar = obtener_total_por_cobrar(usuario_id)
        return {
            "status": "ok",
            "total": len(prestamos),
            "total_por_cobrar": total_por_cobrar,
            "prestamos": prestamos,
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.delete("/api/prestamos/{prestamo_id}")
def api_eliminar_prestamo(prestamo_id: str, usuario_id: str = "default"):
    """Elimina un préstamo por su ID."""
    try:
        from modules.db import eliminar_prestamo
        ok = eliminar_prestamo(usuario_id, prestamo_id)
        return {"status": "ok" if ok else "error",
                "message": "Eliminado" if ok else "No se pudo eliminar"}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/prestamos/por-cobrar")
def api_total_por_cobrar(usuario_id: str = "default"):
    """Devuelve el total pendiente por cobrar (suma de préstamos no pagados)."""
    try:
        from modules.db import obtener_total_por_cobrar
        total = obtener_total_por_cobrar(usuario_id)
        return {"status": "ok", "total_por_cobrar": total}
    except Exception as e:
        return {"error": True, "message": str(e)}

