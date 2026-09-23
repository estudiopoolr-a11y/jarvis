"""Submódulo para manejo de transferencias.

Responsable de registrar transferencias entre cuentas.
"""

from datetime import datetime
from firebase_admin import firestore
from modules.firestore.client import _get_user_ref
from modules.firestore.users import ensure_user

def registrar_transferencia(usuario_id, cuenta_origen, cuenta_destino, monto, descripcion="", fee=0.0):
    """Registra transferencia entre dos cuentas (Kebo style)."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None, "DB no disponible"
    try:
        ensure_user(usuario_id)

        origen_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_origen).limit(1).stream()
        origen_list = list(origen_ref)
        if not origen_list:
            return None, f"No existe la cuenta origen '{cuenta_origen}'"
        origen_id = origen_list[0].id

        destino_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_destino).limit(1).stream()
        destino_list = list(destino_ref)
        if not destino_list:
            return None, f"No existe la cuenta destino '{cuenta_destino}'"
        destino_id = destino_list[0].id

        if origen_id == destino_id:
            return None, "Origen y destino son la misma cuenta"

        # Actualizar balances (con fee si aplica)
        user_ref.collection("accounts").document(origen_id).update({"balance": firestore.Increment(-(float(monto) + float(fee)))})
        user_ref.collection("accounts").document(destino_id).update({"balance": firestore.Increment(float(monto))})

        # Registrar transacción
        ahora = datetime.now()
        year = str(ahora.year)
        month = f"{ahora.month:02d}"
        fecha = ahora.strftime("%Y-%m-%d")

        tx_ref = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").document()
        tx_ref.set({
            "type": "transfer",
            "amount": float(monto),
            "account_id": origen_id,
            "to_account_id": destino_id,
            "description": descripcion or f"Transferencia {cuenta_origen} → {cuenta_destino}",
            "fee": float(fee),
            "status": "cleared",
            "tags": [],
            "date": fecha,
            "created_at": firestore.SERVER_TIMESTAMP
        })

        return tx_ref.id, f"Transferencia de ${float(monto):,.0f} de {cuenta_origen} → {cuenta_destino} completada"
    except Exception as e:
        return None, f"Error: {e}"