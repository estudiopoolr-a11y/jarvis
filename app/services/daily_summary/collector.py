"""app/services/daily_summary/collector.py - Recolecta datos para el resumen diario."""

from modules.finance.transactions import listar_transacciones_recientes
from modules.finance.budgets import obtener_presupuestos_v2
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

def obtener_datos(db):
    """Obtiene balance, presupuestos y tareas de todos los usuarios usando estructura Kebo."""
    balance_data = {}
    presupuestos_data = {}
    tareas_data = {}

    USUARIO_ID = "1536228767180136498"

    try:
        # Obtener transacciones recientes para el usuario principal
        transacciones = listar_transacciones_recientes(usuario_id=USUARIO_ID, limite=100)
        balance_data[USUARIO_ID] = {"ingresos": 0.0, "gastos": 0.0}
        for t in transacciones:
            monto = float(t.get("amount", 0))
            if t.get("type") == "income":
                balance_data[USUARIO_ID]["ingresos"] += monto
            elif t.get("type") == "expense":
                balance_data[USUARIO_ID]["gastos"] += monto

        # Obtener presupuestos del mes actual con datos completos (incluye gastado)
        presupuestos_completos = obtener_presupuestos_v2(usuario_id=USUARIO_ID)
        presupuestos_data[USUARIO_ID] = {}
        for cat, data in presupuestos_completos.items():
            presupuestos_data[USUARIO_ID][cat] = {
                "limite": data["limite"],
                "gastado": data.get("gastado", 0),
                "libre": data.get("libre", 0),
            }

        # Tareas pendientes (estructura Kebo: users/{userId}/tasks/)
        docs = db.collection("users").document(USUARIO_ID).collection("tasks").where(filter=FieldFilter("completada", "==", False)).stream()
        for doc in docs:
            t = doc.to_dict()
            tareas_data.setdefault(USUARIO_ID, []).append(t)
    except Exception as e:
        print(f"Error obteniendo datos: {e}")

    return balance_data, presupuestos_data, tareas_data