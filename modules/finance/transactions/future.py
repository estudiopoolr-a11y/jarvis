"""Submódulo para transacciones futuras (scheduled transactions)."""

from __future__ import annotations

from datetime import datetime

from firebase_admin import firestore

from modules.firestore.client import _get_user_ref
from modules.firestore.users import ensure_user
from modules.finance.categories import crear_categoria
from modules.finance.accounts import crear_cuenta

from modules.finance.transactions.create import registrar_transaccion_v2


def registrar_transaccion_futura(
    usuario_id: str,
    tipo: str,
    monto: float,
    categoria_nombre: str,
    fecha_futura: str,
    descripcion: str = "",
    cuenta_nombre: str = "Efectivo",
    payee: str = "",
    tags: list[str] | None = None,
    auto_post: bool = True,
):
    """Registra una transacción programada para una fecha futura.

    Estructura: users/{userId}/scheduled_transactions/{id}

    - Si auto_post=True y la fecha ya pasó, se registra inmediatamente.
    - Si no, queda pendiente y se ejecuta cuando llegue la fecha.
    """
    if tags is None:
        tags = []

    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None

    try:
        ensure_user(usuario_id)

        # Si auto_post y fecha ya pasó, registrar inmediatamente
        fecha_dt = datetime.strptime(fecha_futura, "%Y-%m-%d")
        if auto_post and fecha_dt.date() <= datetime.now().date():
            return registrar_transaccion_v2(
                usuario_id,
                tipo,
                monto,
                categoria_nombre,
                descripcion,
                cuenta_nombre,
                payee=payee,
                tags=tags,
            )

        # Buscar o crear categoría
        cat_id = crear_categoria(usuario_id, categoria_nombre)

        # Buscar cuenta
        cuenta_ref = (
            user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        )
        cuenta_list = list(cuenta_ref)
        if cuenta_list:
            cuenta_id = cuenta_list[0].id
        else:
            cuenta_id = crear_cuenta(usuario_id, cuenta_nombre, "cash")

        # Guardar como transacción programada
        doc_ref = user_ref.collection("scheduled_transactions").document()
        doc_ref.set(
            {
                "type": tipo,
                "amount": float(monto),
                "account_id": cuenta_id,
                "category_id": cat_id,
                "categoria_nombre": categoria_nombre,
                "cuenta_nombre": cuenta_nombre,
                "payee": payee,
                "description": descripcion,
                "scheduled_date": fecha_futura,
                "status": "pending",  # pending, executed, cancelled
                "tags": tags,
                "created_at": firestore.SERVER_TIMESTAMP,
            }
        )
        return doc_ref.id
    except Exception:
        return None


def ejecutar_transacciones_futuras(usuario_id: str):
    """Ejecuta transacciones programadas cuya fecha ya llegó."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []

    ejecutadas: list[str] = []
    try:
        hoy = datetime.now().strftime("%Y-%m-%d")
        docs = user_ref.collection("scheduled_transactions").where("status", "==", "pending").stream()

        for d in docs:
            data = d.to_dict() or {}
            fecha = data.get("scheduled_date", "")
            if fecha <= hoy:
                tx_id = registrar_transaccion_v2(
                    usuario_id,
                    data.get("type", "expense"),
                    data.get("amount", 0),
                    data.get("categoria_nombre", "General"),
                    data.get("description", ""),
                    data.get("cuenta_nombre", "Efectivo"),
                    payee=data.get("payee", ""),
                    tags=data.get("tags", []),
                )
                if tx_id:
                    d.reference.update(
                        {
                            "status": "executed",
                            "executed_at": firestore.SERVER_TIMESTAMP,
                            "tx_id": tx_id,
                        }
                    )
                    ejecutadas.append(data.get("description", ""))
        return ejecutadas
    except Exception:
        return []


def listar_transacciones_futuras(usuario_id: str = "default", solo_pendientes: bool = True):
    """Lista transacciones programadas (futuras)."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []

    try:
        docs = user_ref.collection("scheduled_transactions").stream()
        result: list[dict] = []
        for d in docs:
            data = d.to_dict() or {}
            if solo_pendientes and data.get("status") != "pending":
                continue
            data["_id"] = d.id
            result.append(data)
        return sorted(result, key=lambda x: x.get("scheduled_date", ""))
    except Exception:
        return []