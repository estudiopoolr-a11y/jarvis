#!/usr/bin/env python3
"""Carga financiera consolidada exacta para el usuario maestro.

Reescribe mayo-agosto 2026 en KEBO usando los totales y categorías proporcionados.
No toca septiembre (ya fue limpiado) ni colecciones top-level legacy.
"""
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from modules import database as dbmod

UID = "1536228767180136498"

DATA = {
    "2026-05": {
        "income": 1061159.03,
        "budgets": {
            "Deudas": (140000, 140000), "Moto": (170000, 212700),
            "Use Personal": (50000, 18000), "Gastos Tontos": (20000, 2000),
            "Madre": (185000, 185000), "Futbol": (50000, 50000),
            "Gym": (35000, 35000), "Alimentación": (2000, 70300),
        },
    },
    "2026-06": {
        "income": 1058894.26,
        "budgets": {
            "Gym": (35000, 0), "Madre": (150000, 150000),
            "Padre": (100000, 100000), "Ahorro": (100000, 0),
            "Use Personal": (40000, 50000), "Deudas": (140000, 126000),
            "Gastos Tontos": (40000, 145500), "Moto": (50000, 45000),
        },
    },
    "2026-07": {
        "income": 936455.00,
        "budgets": {
            "Alimentación": (120000, 120000), "Moto": (100000, 222427),
            "Futbol": (50000, 47500), "Use Personal": (100000, 136729),
            "Women": (200000, 265100), "Gastos Tontos": (100000, 130519.69),
            "Préstamos": (100000, 172500),
        },
    },
    "2026-08": {
        "income": 806199.03,
        "budgets": {
            "Alimentación": (150000, 150000), "Madre": (50000, 50000),
            "Use Personal": (50000, 97900), "Moto": (100000, 31000),
            "Deudas": (200000, 205000), "Women": (300000, 332540),
            "Futbol": (25000, 10000),
        },
    },
}


def norm(value):
    return " ".join(str(value or "").casefold().split())


def delete_items(col):
    docs = list(col.stream())
    for doc in docs:
        doc.reference.delete()
    return len(docs)


def main():
    db = dbmod.inicializar_firebase()
    if not db:
        raise SystemExit("Firebase no disponible")

    user = db.collection("users").document(UID)
    categories = {}
    for doc in user.collection("categories").stream():
        data = doc.to_dict() or {}
        name = data.get("nombre") or data.get("name") or ""
        categories[norm(name)] = doc.id

    print(f"Reescribiendo finanzas para users/{UID}")
    for month, month_data in DATA.items():
        tx_items = user.collection("transactions").document(month).collection("items")
        budget_items = user.collection("budgets").document(month).collection("items")
        old_tx = delete_items(tx_items)
        old_budget = delete_items(budget_items)

        # Un item de ingreso mensual.
        tx_items.document(f"income-{month}").set({
            "type": "income",
            "amount": float(month_data["income"]),
            "category_id": categories.get(norm("Salario")),
            "category_name": "Salario",
            "description": f"Ingreso mensual {month}",
            "account_id": None,
            "status": "cleared",
            "tags": ["consolidado-2026"],
            "date": f"{month}-01",
            "created_at": datetime.now(),
        })

        for category, (budget, spent) in month_data["budgets"].items():
            cat_id = categories.get(norm(category))
            budget_items.document().set({
                "category_id": cat_id,
                "category_name": category,
                "amount": float(budget),
                "year": month[:4],
                "month": month[5:7],
                "created_at": datetime.now(),
            })
            if spent:
                tx_items.document().set({
                    "type": "expense",
                    "amount": float(spent),
                    "category_id": cat_id,
                    "category_name": category,
                    "description": f"Gasto consolidado {category} ({month})",
                    "account_id": None,
                    "status": "cleared",
                    "tags": ["consolidado-2026"],
                    "date": f"{month}-15",
                    "created_at": datetime.now(),
                })

        print(f"{month}: limpiados tx={old_tx}, budgets={old_budget}; cargados presupuesto={len(month_data['budgets'])}")

    print("✅ Carga exacta completada.")


if __name__ == "__main__":
    main()
