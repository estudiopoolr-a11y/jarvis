"""Submódulo para listado de transacciones recientes."""

from __future__ import annotations

from datetime import datetime, timedelta

from modules.firestore.client import _get_user_ref


def listar_transacciones_recientes(usuario_id: str = "default", limite: int = 20):
    """Lista las últimas N transacciones."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []

    try:
        ahora = datetime.now()
        transacciones: list[dict] = []

        for i in range(3):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"

            try:
                docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
                for d in docs:
                    t = d.to_dict() or {}
                    t["_id"] = d.id
                    t["_year"] = year
                    t["_month"] = month
                    transacciones.append(t)
            except Exception:
                pass

        transacciones.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return transacciones[:limite]
    except Exception:
        return []