from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from modules.db import (
    registrar_prestamo, 
    registrar_pago_prestamo, 
    listar_prestamos, 
    eliminar_prestamo, 
    obtener_total_por_cobrar
)

router = APIRouter()

# ==================== ESQUEMAS PYDANTIC ====================

class PrestamoCreate(BaseModel):
    persona: str = Field(..., example="Juan Pérez")
    monto: float = Field(..., gt=0, example=50000.0)
    fecha_limite: Optional[str] = Field(None, example="2026-12-31")
    nota: Optional[str] = Field("", example="Préstamo para viaje")
    tipo: str = Field("prestado", example="prestado") # prestado (yo doy), prestado_a_mi (yo recibo)

class PagoPrestamoCreate(BaseModel):
    prestamo_id: str
    monto_pago: float = Field(..., gt=0)
    fecha: Optional[str] = None

class PrestamoResponse(BaseModel):
    id: str
    persona: str
    monto: float
    fecha_limite: Optional[str]
    estado: str
    nota: str

# ==================== ENDPOINTS DE PRÉSTAMOS ====================

@router.post("/api/v1/prestamos/registrar", response_model=dict)
def api_registrar_prestamo(payload: PrestamoCreate, usuario_id: str = "default"):
    """Registra un nuevo préstamo con validación Pydantic."""
    try:
        prestamo_id = registrar_prestamo(
            usuario_id, 
            payload.persona, 
            payload.monto, 
            payload.fecha_limite, 
            f"Tipo: {payload.tipo} | {payload.nota}"
        )
        if not prestamo_id:
            raise HTTPException(status_code=400, detail="No se pudo registrar el préstamo")
        
        return {"status": "ok", "id": prestamo_id, "persona": payload.persona, "monto": payload.monto}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/prestamos/pagar")
def api_registrar_pago_prestamo(payload: PagoPrestamoCreate, usuario_id: str = "default"):
    """Registra un pago (parcial o total) de un préstamo."""
    try:
        resultado = registrar_pago_prestamo(
            usuario_id, 
            payload.prestamo_id, 
            payload.monto_pago, 
            payload.fecha
        )
        if not resultado:
            raise HTTPException(status_code=404, detail="No se pudo registrar el pago (verifica prestamo_id)")
        
        return {"status": "ok", **resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/prestamos/listar", response_model=List[PrestamoResponse])
def api_listar_prestamos(usuario_id: str = "default", solo_pendientes: bool = False):
    """Lista préstamos. solo_pendientes=true filtra a los no pagados."""
    try:
        prestamos_raw = listar_prestamos(usuario_id, solo_pendientes=solo_pendientes)
        
        # Mapeo de campos Firestore -> Pydantic
        processed = []
        for p in prestamos_raw:
            processed.append({
                "id": p.get("_id"),
                "persona": p.get("borrower_or_lender") or p.get("persona", "Desconocido"),
                "monto": p.get("current_balance") or p.get("monto", 0.0),
                "fecha_limite": p.get("fecha_limite") or p.get("created_at"),
                "estado": p.get("status", "pendiente"),
                "nota": p.get("nota") or p.get("description", "")
            })
        return processed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/v1/prestamos/{prestamo_id}")
def api_eliminar_prestamo(prestamo_id: str, usuario_id: str = "default"):
    """Elimina un préstamo por su ID."""
    try:
        ok = eliminar_prestamo(usuario_id, prestamo_id)
        if not ok:
            raise HTTPException(status_code=404, detail="No se pudo eliminar el préstamo")
        return {"status": "ok", "message": "Eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/prestamos/por-cobrar")
def api_total_por_cobrar(usuario_id: str = "default"):
    """Devuelve el total pendiente por cobrar."""
    try:
        total = obtener_total_por_cobrar(usuario_id)
        return {"status": "ok", "total_por_cobrar": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
