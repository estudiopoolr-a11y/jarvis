"""modules/finance/budgets/delete.py - Funciones para eliminar presupuestos."""

from modules.firestore.client import _get_user_ref
from modules.finance.categories import _cat_exacta, _coincidir_categoria, _normalizar_cat_str
from datetime import datetime

def eliminar_presupuesto_mes(usuario_id, categoria_nombre, year=None, month=None):
    """Elimina un presupuesto mensual de la estructura KEBO."""
    year = str(year) if year else str(datetime.now().year)
    month = f"{int(month):02d}" if month else f"{datetime.now().month:02d}"

    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False

    try:
        items_ref = user_ref.collection("budgets").document(f"{year}-{month}").collection("items")
        docs = list(items_ref.stream())
        if not docs:
            return False

        # Pasada 1: Coincidencia EXACTA
        for doc in docs:
            data = doc.to_dict() or {}
            nombre = str(data.get("category_name", "")).strip()
            if _cat_exacta(nombre, categoria_nombre):
                doc.reference.delete()
                return True

        # Pasada 2: Coincidencia PARCIAL (mejor coincidencia por longitud)
        candidatos = []
        for doc in docs:
            data = doc.to_dict() or {}
            nombre = str(data.get("category_name", "")).strip()
            if _coincidir_categoria(nombre, categoria_nombre):
                candidatos.append(doc)

        if candidatos:
            b_norm = _normalizar_cat_str(categoria_nombre)
            candidatos.sort(key=lambda d: abs(len(_normalizar_cat_str((d.to_dict() or {}).get("category_name", ""))) - len(b_norm)))
            candidatos[0].reference.delete()
            return True

        return False
    except Exception as e:
        print(f"Error eliminando presupuesto mes: {e}")
        return False

def eliminar_todos_presupuestos_mes(usuario_id, year=None, month=None):
    """Elimina todos los presupuestos de un mes específico en la estructura KEBO."""
    year = str(year) if year else str(datetime.now().year)
    month = f"{int(month):02d}" if month else f"{datetime.now().month:02d}"

    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return 0

    try:
        items_ref = user_ref.collection("budgets").document(f"{year}-{month}").collection("items")
        docs = list(items_ref.stream())
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        return count
    except Exception as e:
        print(f"Error eliminando todos los presupuestos del mes: {e}")
        return 0