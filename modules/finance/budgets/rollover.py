"""modules/finance/budgets/rollover.py - Funciones para aplicar rollover de presupuestos."""

from firebase_admin import firestore
from modules.firestore.client import _get_user_ref
from datetime import datetime, timedelta

def aplicar_rollover_presupuesto(usuario_id, year=None, month=None):
    """Aplica rollover de presupuesto del mes anterior al actual."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return {}
    try:
        ahora = datetime.now()
        if not year:
            year = str(ahora.year)
        if not month:
            month = f"{ahora.month:02d}"

        # Mes anterior
        mes_anterior = ahora.replace(day=1) - timedelta(days=1)
        ant_year = str(mes_anterior.year)
        ant_month = f"{mes_anterior.month:02d}"

        rollovers = {}

        # Leer presupuestos del mes anterior
        try:
            docs_ant = user_ref.collection("budgets").document(f"{ant_year}-{ant_month}").collection("items").stream()
            for d in docs_ant:
                data = d.to_dict()
                cat_id = data.get("category_id")
                cat_nombre = data.get("category_name", "")
                limite_ant = float(data.get("amount", 0))

                # Calcular gastado del mes anterior
                docs_tx = user_ref.collection("transactions").document(f"{ant_year}-{ant_month}").collection("items").stream()
                gastado_ant = 0.0
                for tx in docs_tx:
                    t = tx.to_dict()
                    if (t.get("category_id") == cat_id and
                            (t.get("type") or t.get("tipo", "expense")) == "expense"):
                        gastado_ant += float(t.get("amount") or t.get("monto", 0))

                sobrante = limite_ant - gastado_ant
                if sobrante > 0:
                    rollovers[cat_nombre] = sobrante

                    # Buscar o crear presupuesto del mes actual
                    mes_items = user_ref.collection("budgets").document(f"{year}-{month}").collection("items")
                    existing = mes_items.where("category_id", "==", cat_id).limit(1).stream()
                    existing_list = list(existing)
                    if existing_list:
                        nuevo_limite = float(existing_list[0].to_dict().get("amount", 0)) + sobrante
                        existing_list[0].reference.update({
                            "amount": nuevo_limite,
                            "rollover_from": f"{ant_year}-{ant_month}"
                        })
                    else:
                        mes_items.document().set({
                            "category_id": cat_id,
                            "category_name": cat_nombre,
                            "amount": limite_ant + sobrante,
                            "year": year,
                            "month": month,
                            "rollover_from": f"{ant_year}-{ant_month}",
                            "rollover_amount": sobrante,
                            "created_at": firestore.SERVER_TIMESTAMP
                        })
        except Exception as e:
            print(f"Error en rollover: {e}")

        return rollovers
    except Exception as e:
        print(f"Error aplicando rollover: {e}")
        return {}