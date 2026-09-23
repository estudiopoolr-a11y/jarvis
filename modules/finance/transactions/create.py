"""Submódulo para creación de transacciones.

Responsable de registrar transacciones estándar y divididas.
"""

from datetime import datetime
from firebase_admin import firestore
from modules.firestore.client import _get_user_ref
from modules.firestore.users import ensure_user
from modules.finance.accounts import crear_cuenta, actualizar_balance_cuenta
from modules.finance.categories import crear_categoria

def registrar_transaccion_v2(usuario_id, tipo, monto, categoria_nombre, descripcion="", cuenta_nombre="Efectivo",
                             payee="", fee=0.0, status="cleared", tags=None, fecha=None):
    """Registra transacción en nueva estructura Kebo."""
    if tags is None:
        tags = []
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)

        # Buscar o crear categoría
        cat_id = crear_categoria(usuario_id, categoria_nombre)

        # Buscar cuenta
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        if cuenta_list:
            cuenta_id = cuenta_list[0].id
        else:
            cuenta_id = crear_cuenta(usuario_id, cuenta_nombre, "cash")

        # Fecha de la transacción (por defecto: ahora)
        if not fecha:
            ahora = datetime.now()
            fecha = ahora.strftime("%Y-%m-%d")
        else:
            ahora = datetime.strptime(fecha, "%Y-%m-%d")

        year = str(ahora.year)
        month = f"{ahora.month:02d}"

        tx_ref = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").document()
        tx_ref.set({
            "type": tipo,
            "amount": float(monto),
            "account_id": cuenta_id,
            "category_id": cat_id,
            "payee": payee,
            "description": descripcion,
            "fee": float(fee),
            "status": status,
            "tags": tags,
            "date": fecha,
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # Actualizar balance (considerando fee si es gasto)
        delta = -float(monto)
        if tipo == "income":
            delta = float(monto)
        if fee and tipo == "expense":
            delta -= float(fee)
        actualizar_balance_cuenta(usuario_id, cuenta_id, delta)

        return tx_ref.id
    except Exception as e:
        print(f"Error registrando transacción v2: {e}")
        return None