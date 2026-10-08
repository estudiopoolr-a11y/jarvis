from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from app.api import app
from datetime import datetime
from modules.db import (
    obtener_presupuestos_v2, 
    listar_subcategorias, 
    aplicar_rollover_presupuesto
)

# ==================== ESQUEMAS PYDANTIC ====================

class BudgetCreate(BaseModel):
    categoria: str = Field(..., example="Alimentación")
    monto_maximo: float = Field(..., gt=0, example=500.0)
    mes: str = Field(..., example="2026-10") # Formato YYYY-MM

class BudgetUpdate(BaseModel):
    monto_maximo: Optional[float] = Field(None, gt=0)
    mes: Optional[str] = None

class BudgetResponse(BaseModel):
    categoria: str
    monto_maximo: float
    gastado: float
    porcentaje_consumido: float
    estado: str # "ok", "warning", "critical"

# ==================== ENDPOINTS de PRESUPUESTOS ====================

@app.get("/api/kebo/presupuestos", response_model=List[BudgetResponse])
def api_kebo_presupuestos(usuario_id: str = "default", mes: Optional[str] = None):
    """
    Obtiene presupuestos con cálculo dinámico de consumo.
    """
    try:
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        
        presupuestos_raw = obtener_presupuestos_v2(usuario_id, mes)
        
        processed = []
        for p in presupuestos_raw:
            maximo = p.get("monto_maximo", 1.0)
            gastado = p.get("gastado", 0.0)
            porcentaje = (gastado / maximo) * 100
            
            estado = "ok"
            if porcentaje >= 100: estado = "critical"
            elif porcentaje >= 80: estado = "warning"
            
            processed.append({
                "categoria": p.get("categoria"),
                "monto_maximo": maximo,
                "gastado": gastado,
                "porcentaje_consumido": round(porcentaje, 2),
                "estado": estado
            })
        return processed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kebo/presupuestos")
def api_kebo_create_budget(payload: BudgetCreate, usuario_id: str = "default"):
    """Crea un presupuesto mensual para una categoría."""
    try:
        from modules.db import crear_presupuesto
        # Nota: se asume que crear_presupuesto existe en modules.db
        ok = crear_presupuesto(usuario_id, payload.categoria, payload.monto_maximo, payload.mes)
        if not ok:
            raise HTTPException(status_code=400, detail="No se pudo crear el presupuesto")
        return {"status": "ok", "message": "Presupuesto creado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kebo/subcategorias")
def api_kebo_subcategorias(usuario_id: str = "default", categoria: str = ""):
    """Lista sub-categorías de una categoría padre."""
    try:
        if not categoria:
            raise HTTPException(status_code=400, detail="Parámetro 'categoria' requerido")
        subs = listar_subcategorias(usuario_id, categoria)
        return {"categoria": categoria, "subcategorias": subs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kebo/rollover")
def api_kebo_rollover(usuario_id: str = "default"):
    """Aplica rollover del presupuesto del mes anterior."""
    try:
        rollovers = aplicar_rollover_presupuesto(usuario_id)
        return {"status": "ok", "rollovers_aplicados": rollovers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
