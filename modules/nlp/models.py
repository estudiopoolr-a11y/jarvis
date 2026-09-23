from typing import Literal, Optional

from pydantic import BaseModel


class ItemIntencion(BaseModel):
    tipo: Literal["tarea", "gasto", "ingreso", "presupuesto", "completar_tarea", "configuracion_masiva", "ninguno"]
    tarea: Optional[str] = None
    prioridad: Optional[str] = "Media"
    fecha_limite: Optional[str] = "Pronto"
    monto: Optional[float] = 0.0
    categoria: Optional[str] = "General"
    descripcion: Optional[str] = None
    limite: Optional[float] = 0.0
    presupuestos_dict: Optional[dict] = None
    transacciones_list: Optional[list] = None


PALABRAS_CLAVE_INTENCION = [
    "gasto", "gasté", "compré", "pagué", "compra", "ingreso", "gané", "recibí",
    "pago", "tarea", "pendiente", "recordar", "presupuesto", "límite", "completé",
    "terminé", "hecho", "debo", "cuota", "finanzas", "gastos", "historial", "desglose",
    "borra", "limpia", "reinicia", "configura", "cargar"
]
