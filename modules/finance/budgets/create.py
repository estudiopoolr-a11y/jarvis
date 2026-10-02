"""modules/finance/budgets/create.py - Funciones para establecer presupuestos."""

from firebase_admin import firestore
from modules.firestore.client import _get_user_ref
from modules.firestore.users import ensure_user
from modules.finance.categories import crear_categoria, _normalizar_cat_str
from datetime import datetime


def establecer_presupuesto_mes(usuario_id, categoria_nombre, monto, year=None, month=None):
    """Establece un presupuesto para una categoría en un mes específico (Kebo style)."""
    # Normalizar nombre de categoría para evitar duplicados por mayúsculas/acentos
    categoria_norm = _normalizar_cat_str(categoria_nombre)
    if not categoria_norm:
        categoria_norm = categoria_nombre.strip()  # fallback a strip si normalización falla
    
    year = str(year) if year else str(datetime.now().year)
    month = f"{int(month):02d}" if month else f"{datetime.now().month:02d}"

    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        # Normalizar año y mes SIEMPRE (evita docs "2026-7" vs "2026-07")
        ensure_user(usuario_id)

        # Buscar o crear categoría (usando nombre normalizado)
        cat_id = crear_categoria(usuario_id, categoria_norm)

        # Buscar si ya existe un presupuesto para esta categoría en este mes
        items_ref = user_ref.collection("budgets").document(f"{year}-{month}").collection("items")
        existing = items_ref.where("category_id", "==", cat_id).limit(1).stream()
        existing_list = list(existing)

        if existing_list:
            existing_list[0].reference.update({"amount": float(monto)})
        else:
            items_ref.document().set({
                "category_id": cat_id,
                "category_name": categoria_norm,  # Guardar nombre normalizado
                "amount": float(monto),
                "year": year,
                "month": month,
                "created_at": firestore.SERVER_TIMESTAMP
            })
        return True
    except Exception as e:
        print(f"Error estableciendo presupuesto mes: {e}")
        return False