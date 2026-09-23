"""modules/finance/budgets/retrieve.py - Funciones para obtener presupuestos."""

from modules.firestore.client import _get_user_ref
from modules.finance.categories import listar_categorias
from datetime import datetime

def obtener_presupuestos_mes(usuario_id, year=None, month=None):
    """Obtiene los presupuestos de un mes específico (Kebo style)."""
    year = str(year) if year else str(datetime.now().year)
    month = f"{int(month):02d}" if month else f"{datetime.now().month:02d}"

    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []

    presupuestos_mes = {}
    try:
        # Primero intentar leer del mes específico
        items_ref = user_ref.collection("budgets").document(f"{year}-{month}").collection("items")
        for d in items_ref.stream():
            data = d.to_dict()
            presupuestos_mes[data.get("category_name")] = float(data.get("amount", 0))
    except Exception:
        pass

    # Si no hay nada en el mes, usar defaults de categories
    if not presupuestos_mes:
        try:
            for d in user_ref.collection("categories").stream():
                data = d.to_dict()
                b = float(data.get("budget", 0))
                if b > 0:
                    presupuestos_mes[data.get("nombre")] = b
        except Exception:
            pass

    return [{"categoria": k, "limite": v, "gastado": 0.0, "year": year, "month": month}
            for k, v in presupuestos_mes.items()]


def obtener_presupuestos_v2(usuario_id="default", mes=None):
    """Obtiene presupuestos con gastado del mes (Kebo style)."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return {}

    if not mes:
        mes = datetime.now().strftime("%Y-%m")
    year, month = mes.split("-")

    try:
        # Obtener presupuestos del mes (Kebo: budgets/{year}/{month}/items/)
        presupuestos_mes = {}
        try:
            items_ref = user_ref.collection("budgets").document(f"{year}-{month}").collection("items")
            for d in items_ref.stream():
                data = d.to_dict()
                presupuestos_mes[data.get("category_name")] = {
                    "limite": float(data.get("amount", 0)),
                    "category_id": data.get("category_id"),
                    "year": year,
                    "month": month
                }
        except Exception:
            pass

        # Si no hay presupuestos en el mes, usar defaults de categories (compatibilidad)
        cats = listar_categorias(usuario_id)
        if not presupuestos_mes:
            for cat in cats:
                nombre = cat.get("nombre")
                budget = float(cat.get("budget", 0))
                if budget > 0:
                    presupuestos_mes[nombre] = {
                        "limite": budget,
                        "category_id": cat["_id"],
                        "year": year,
                        "month": month
                    }

        # Calcular gasto por categoría
        docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
        gastos_por_cat_id = {}
        for d in docs:
            t = d.to_dict()
            tipo = t.get("type") or t.get("tipo", "expense")
            if tipo == "expense":
                cat_id = t.get("category_id")
                monto = float(t.get("amount") or t.get("monto", 0))
                gastos_por_cat_id[cat_id] = gastos_por_cat_id.get(cat_id, 0) + monto

        # Combinar
        presupuestos = {}
        for nombre, info in presupuestos_mes.items():
            gastado = gastos_por_cat_id.get(info["category_id"], 0)
            presupuestos[nombre] = {
                "limite": info["limite"],
                "gastado": gastado,
                "libre": info["limite"] - gastado,
                "excedido": (info["limite"] - gastado) < 0,
                "year": year,
                "month": month
            }
        return presupuestos
    except Exception as e:
        print(f"Error presupuestos v2: {e}")
        return {}