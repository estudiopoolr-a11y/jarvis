from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from app.api import app
from datetime import datetime
from modules.db import (
    registrar_transaccion, 
    listar_transacciones_recientes,
    transferir_fondos
)

# ==================== ESQUEMAS PYDANTIC ====================

class TransactionCreate(BaseModel):
    monto: float = Field(..., example=50.0)
    categoria: str = Field(..., example="Comida")
    cuenta_id: str = Field(..., example="nu_account_id")
    descripcion: Optional[str] = Field("", example="Almuerzo en oficina")
    fecha: Optional[str] = Field(None, example="2026-10-08") # YYYY-MM-DD
    etiqueta: Optional[str] = Field(None, example="trabajo")

class TransferCreate(BaseModel):
    monto: float = Field(..., gt=0)
    cuenta_origen_id: str
    cuenta_destino_id: str
    nota: Optional[str] = ""

class TransactionResponse(BaseModel):
    id: str
    monto: float
    categoria: str
    cuenta_id: str
    descripcion: str
    fecha: str

# ==================== ENDPOINTS DE TRANSACCIONES ====================

@app.post("/api/kebo/transactions", response_model=TransactionResponse)
def api_create_transaction(payload: TransactionCreate, usuario_id: str = "default"):
    """Registra una transacción etiquetada por cuenta y categoría."""
    try:
        fecha = payload.fecha or datetime.now().strftime("%Y-%m-%d")
        tx_id = registrar_transaccion(
            usuario_id, 
            payload.monto, 
            payload.categoria, 
            payload.cuenta_id, 
            payload.descripcion, 
            fecha, 
            payload.etiqueta
        )
        if not tx_id:
            raise HTTPException(status_code=400, detail="No se pudo registrar la transacción")
        
        return {
            "id": tx_id, 
            "monto": payload.monto, 
            "categoria": payload.categoria, 
            "cuenta_id": payload.cuenta_id, 
            "descripcion": payload.descripcion, 
            "fecha": fecha
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kebo/transactions/transfer")
def api_transfer_funds(payload: TransferCreate, usuario_id: str = "default"):
    """Realiza una transferencia entre cuentas."""
    try:
        ok = transferir_fondos(
            usuario_id, 
            payload.cuenta_origen_id, 
            payload.cuenta_destino_id, 
            payload.monto, 
            payload.nota
        )
        if not ok:
            raise HTTPException(status_code=400, detail="Error en la transferencia de fondos")
        return {"status": "ok", "message": "Transferencia completada exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kebo/transactions/recent", response_model=List[TransactionResponse])
def api_get_recent_transactions(usuario_id: str = "default", limit: int = 10):
    """Obtiene las transacciones más recientes."""
    try:
        txs = listar_transacciones_recientes(usuario_id, limit=limit)
        return [
            {
                "id": t.get("id"), 
                "monto": t.get("monto"), 
                "categoria": t.get("categoria"), 
                "cuenta_id": t.get("cuenta_id"), 
                "descripcion": t.get("descripcion", ""), 
                "fecha": t.get("fecha", "")
            } for t in txs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
