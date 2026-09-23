"""modules/finance/budgets/update.py - Funciones para actualizar presupuestos."""

from firebase_admin import firestore
from modules.firestore.client import _get_user_ref
from modules.finance.categories import _cat_exacta, _coincidir_categoria, _normalizar_cat_str, crear_categoria
from datetime import datetime

def actualizar_presupuesto_categoria(usuario_id, nombre, nuevo_budget):
    """Actualiza el presupuesto de una categoría por nombre (compatibilidad)."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        # Actualizar el default en categories
        docs = user_ref.collection("categories").where("nombre", "==", nombre).limit(1).stream()
        docs_list = list(docs)
        if docs_list:
            docs_list[0].reference.update({"budget": float(nuevo_budget)})

        # Actualizar también el mes actual en budgets/{year}/{month}/items/
        ahora = datetime.now()
        year = str(ahora.year)
        month = f"{ahora.month:02d}"
        budget_ref = user_ref.collection("budgets").document(f"{year}-{month}").collection("items")
        existing = budget_ref.where("category_name", "==", nombre).limit(1).stream()
        existing_list = list(existing)
        if existing_list:
            existing_list[0].reference.update({"amount": float(nuevo_budget)})
        else:
            cat_id = docs_list[0].id if docs_list else None
            budget_ref.document().set({
                "category_id": cat_id,
                "category_name": nombre,
                "amount": float(nuevo_budget),
                "created_at": firestore.SERVER_TIMESTAMP
            })
        return True
    except Exception as e:
        print(f"Error actualizando presupuesto: {e}")
        return False

def modificar_presupuesto_mes(usuario_id, categoria_nombre, nuevo_limite, year=None, month=None):
    """Modifica el monto de un presupuesto mensual en la estructura KEBO."""
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
                doc.reference.update({"amount": float(nuevo_limite)})
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
            candidatos[0].reference.update({"amount": float(nuevo_limite)})
            return True

        return False
    except Exception as e:
        print(f"Error modificando presupuesto mes: {e}")
        return False

def renombrar_presupuesto_mes(usuario_id, categoria_antigua, categoria_nueva, year=None, month=None):
    """Renombra un presupuesto existente a una nueva categoría en la estructura KEBO."""
    year = str(year) if year else str(datetime.now().year)
    month = f"{int(month):02d}" if month else f"{datetime.now().month:02d}"

    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False

    try:
        cat_id = crear_categoria(usuario_id, categoria_nueva)
        items_ref = user_ref.collection("budgets").document(f"{year}-{month}").collection("items")
        docs = list(items_ref.stream())
        if not docs:
            return False

        # Pasada 1: Coincidencia EXACTA
        for doc in docs:
            data = doc.to_dict() or {}
            nombre = str(data.get("category_name", "")).strip()
            if _cat_exacta(nombre, categoria_antigua):
                doc.reference.update({
                    "category_name": categoria_nueva,
                    "category_id": cat_id
                })
                return True

        # Pasada 2: Coincidencia PARCIAL (mejor coincidencia por longitud)
        candidatos = []
        for doc in docs:
            data = doc.to_dict() or {}
            nombre = str(data.get("category_name", "")).strip()
            if _coincidir_categoria(nombre, categoria_antigua):
                candidatos.append(doc)

        if candidatos:
            b_norm = _normalizar_cat_str(categoria_antigua)
            candidatos.sort(key=lambda d: abs(len(_normalizar_cat_str((d.to_dict() or {}).get("category_name", ""))) - len(b_norm)))
            candidatos[0].reference.update({
                "category_name": categoria_nueva,
                "category_id": cat_id
            })
            return True

        return False
    except Exception as e:
        print(f"Error renombrando presupuesto mes: {e}")
        return False