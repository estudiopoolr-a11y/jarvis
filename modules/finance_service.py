from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
from modules.firestore.client import _get_user_ref

# Modelos Pydantic
class CuentaSchema(BaseModel):
    id: str
    nombre: str = Field(..., min_length=1)
    saldo: float

class RegistrarMovimientoInput(BaseModel):
    monto: float
    categoria: str
    cuenta_nombre: str
    tipo: Literal["gasto", "ingreso"]

    @field_validator("monto", mode="before")
    def parse_monto(cls, v):
        if isinstance(v, str):
            # Limpiar formatos de dinero como $150.000 o 150.000,00
            v = v.replace('$', '').replace('.', '').replace(',', '.')
        return float(v)

class RenombrarCuentaInput(BaseModel):
    nombre_actual: str
    nuevo_nombre: str = Field(..., min_length=1)

class ConsultarSaldosInput(BaseModel):
    nombre_cuenta: Optional[str] = None

# Funciones de Negocio
def obtener_saldos(input_data: ConsultarSaldosInput = ConsultarSaldosInput()):
    db, user_ref = _get_user_ref()
    accounts_ref = user_ref.collection("accounts")
    accounts = accounts_ref.stream()
    
    saldos = []
    for acc in accounts:
        data = acc.to_dict()
        nombre = data.get("name")
        # Filtrar registros corruptos
        if nombre:
            saldos.append(CuentaSchema(id=acc.id, nombre=nombre, saldo=float(data.get("balance", 0))))
            
    if input_data.nombre_cuenta:
        saldos = [s for s in saldos if s.nombre == input_data.nombre_cuenta]
        
    return [s.model_dump() for s in saldos]

def registrar_movimiento(input_data: RegistrarMovimientoInput):
    # Implementación mock/wrapper de la lógica de transacciones existente
    # En producción esto usaría modules/finance/transactions/create.py
    return {"status": "success", "detalle": f"Registrado {input_data.tipo} de {input_data.monto} en {input_data.cuenta_nombre}"}

def renombrar_cuenta(input_data: RenombrarCuentaInput):
    # Implementación mock/wrapper
    return {"status": "success", "detalle": f"Cuenta {input_data.nombre_actual} renombrada a {input_data.nuevo_nombre}"}
