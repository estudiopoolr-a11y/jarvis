from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from modules.db import (
    listar_cuentas, 
    crear_cuenta, 
    actualizar_cuenta, 
    obtener_balance_financiero
)

router = APIRouter()

# ==================== ESQUEMAS PYDANTIC ====================

class AccountBase(BaseModel):
    nombre: str = Field(..., example="Nu")
    tipo: str = Field(..., example="bank") # bank, wallet, cash, savings
    saldo_inicial: float = Field(0.0, example=1000.0)

class AccountUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    saldo: Optional[float] = None

class AccountResponse(BaseModel):
    id: str
    nombre: str
    tipo: str
    saldo: float

# ==================== ENDPOINTS DE CUENTAS ====================

@router.get("/api/kebo/accounts", response_model=List[AccountResponse])
def api_list_accounts(usuario_id: str = "default"):
    """Lista todas las cuentas financieras."""
    try:
        cuentas = listar_cuentas(usuario_id)
        return [
            {"id": c.get("_id"), "nombre": c.get("nombre"), "tipo": c.get("tipo"), "saldo": c.get("balance", 0.0)} 
            for c in cuentas
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/kebo/accounts", response_model=AccountResponse)
def api_create_account(payload: AccountBase, usuario_id: str = "default"):
    """Crea una nueva cuenta financiera."""
    try:
        account_id = crear_cuenta(
            usuario_id, 
            payload.nombre, 
            payload.tipo, 
            payload.saldo_inicial
        )
        if not account_id:
            raise HTTPException(status_code=400, detail="No se pudo crear la cuenta")
        
        return {"id": account_id, "nombre": payload.nombre, "tipo": payload.tipo, "saldo": payload.saldo_inicial}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/kebo/accounts/{account_id}")
def api_update_account(account_id: str, payload: AccountUpdate, usuario_id: str = "default"):
    """Actualiza los datos de una cuenta."""
    try:
        update_data = payload.dict(exclude_unset=True)
        ok = actualizar_cuenta(usuario_id, account_id, update_data)
        if not ok:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        return {"status": "ok", "message": "Cuenta actualizada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/kebo/accounts/balance")
def api_get_total_balance(usuario_id: str = "default"):
    """Obtiene el balance consolidado de todas las cuentas."""
    try:
        balance = obtener_balance_financiero(usuario_id)
        return {"status": "ok", "balance_total": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
