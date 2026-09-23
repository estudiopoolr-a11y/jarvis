"""Submódulo para transacciones tipo split."""

from __future__ import annotations

from datetime import datetime

from firebase_admin import firestore

from modules.firestore.client import _get_user_ref
from modules.firestore.users import ensure_user
from modules.finance.accounts import actualizar_balance_cuenta
from modules.finance.categories import crear_categoria


def registrar_split(
    usuario_id: str,
    monto_total: float,
    splits: list[dict],
    cuenta_nombre: str = "Efectivo",
    descripcion: str = "",
    status: str = "cleared",
    tags: list[str] | None = None,
):
    """Registra un gasto dividido en varias categorías (Kebo split transaction).

    Estructura en BD:
    - transactions/{year}-{month}/items/{id} con splits=[...]

    También crea transacciones individuales por categoría linkeadas por parent_id.
    """
    if tags is None:
        tags = []

    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None, "DB no disponible"

    try:
        ensure_user(usuario_id)

        # Buscar cuenta
        cuenta_ref = (
            user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        )
        cuenta_list = list(cuenta_ref)
        if not cuenta_list:
            return None, f"No existe la cuenta '{cuenta_nombre}'"
        cuenta_id = cuenta_list[0].id

        ahora = datetime.now()
        year = str(ahora.year)
        month = f"{ahora.month:02d}"
        fecha = ahora.strftime("%Y-%m-%d")

        # Crear transacción padre (split)
        parent_ref = (
            user_ref.collection("transactions")
            .document(f"{year}-{month}")
            .collection("items")
            .document()
        )
        parent_ref.set(
            {
                "type": "expense",
                "amount": float(monto_total),
                "account_id": cuenta_id,
                "description": descripcion or "Gasto dividido",
                "status": status,
                "tags": tags + ["split"],
                "date": fecha,
                "is_split": True,
                "splits": [
                    {"category": s["categoria"], "amount": float(s["monto"])} for s in splits
                ],
                "created_at": firestore.SERVER_TIMESTAMP,
            }
        )

        # Crear transacciones individuales por categoría
        child_ids: list[str] = []
        for split in splits:
            cat_id = crear_categoria(usuario_id, split["categoria"])
            child_ref = (
                user_ref.collection("transactions")
                .document(f"{year}-{month}")
                .collection("items")
                .document()
            )
            child_ref.set(
                {
                    "type": "expense",
                    "amount": float(split["monto"]),
                    "account_id": cuenta_id,
                    "category_id": cat_id,
                    "description": split.get("descripcion", descripcion),
                    "parent_id": parent_ref.id,
                    "is_split_child": True,
                    "status": status,
                    "tags": tags,
                    "date": fecha,
                    "created_at": firestore.SERVER_TIMESTAMP,
                }
            )
            child_ids.append(child_ref.id)

        # Actualizar balance de la cuenta una sola vez
        actualizar_balance_cuenta(usuario_id, cuenta_id, -float(monto_total))

        return parent_ref.id, f"Gasto dividido en {len(splits)} categorías: ${float(monto_total):,.0f}"
    except Exception as e:
        return None, f"Error: {e}"