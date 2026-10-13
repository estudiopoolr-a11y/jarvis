"""Ingesta de presupuestos mensuales 2026 en Firebase Firestore.

Escribe en la subcoleccion budgets/{YYYY-MM}/items para habilitar el calculo
de porcentaje_uso en el dashboard y los widgets. Los limites son valores
base sugeridos; ajustalos segun tu flujo de caja real.

Colecciones escritas:
- budgets/2026-05/items  -> Moto, Madre, Deudas, Alimentacion, Futbol, Gym, Use personal
- budgets/2026-06/items  -> Madre, Gastos tontos, Deudas, Padre, Use personal, Moto
- budgets/2026-07/items  -> Women, Moto, Prestamos, Use personal, Gastos tontos, Alimentacion, Futbol
- budgets/2026-08/items  -> Deudas, Alimentacion, Use personal, Madre, Moto, Otros

Idempotente: re-ejecutar no duplica; solo sobreescribe los valores.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_admin import firestore  # noqa: E402
from modules.firestore.client import inicializar_firebase  # noqa: E402

# Limites presupuestales por mes y categoria (COP).
# Ajusta estos valores segun tu flujo de caja real.
PRESUPUESTOS_2026 = {
    "2026-05": {
        "Moto": 250000.0,
        "Madre": 200000.0,
        "Deudas": 150000.0,
        "Alimentacion": 100000.0,
        "Futbol": 60000.0,
        "Gym": 40000.0,
        "Use personal": 50000.0,
        "Gastos tontos": 10000.0,
    },
    "2026-06": {
        "Madre": 150000.0,
        "Gastos tontos": 150000.0,
        "Deudas": 130000.0,
        "Padre": 120000.0,
        "Use personal": 60000.0,
        "Moto": 60000.0,
    },
    "2026-07": {
        "Women": 300000.0,
        "Moto": 250000.0,
        "Prestamos": 200000.0,
        "Use personal": 150000.0,
        "Gastos tontos": 150000.0,
        "Alimentacion": 150000.0,
        "Futbol": 60000.0,
    },
    "2026-08": {
        "Deudas": 250000.0,
        "Alimentacion": 180000.0,
        "Use personal": 120000.0,
        "Madre": 60000.0,
        "Moto": 50000.0,
        "Otros": 350000.0,
    },
}


def _escribir_presupuestos(db: firestore.Client) -> int:
    """Escribe los presupuestos por mes. Retorna el total de docs escritos."""
    total_docs = 0
    for mes, categorias in PRESUPUESTOS_2026.items():
        for cat, limite in categorias.items():
            doc_ref = (
                db.collection("budgets")
                .document(mes)
                .collection("items")
                .document(cat)
            )
            doc_ref.set(
                {
                    "categoria": cat,
                    "limite": float(limite),
                    "amount": float(limite),  # alias que lee el dashboard
                    "category_name": cat,
                    "created_at": firestore.SERVER_TIMESTAMP,
                }
            )
            total_docs += 1
        print(f"[OK] Budgets {mes}: {len(categorias)} categorias")
    return total_docs


def main() -> int:
    db = inicializar_firebase()
    if db is None:
        print("[ERR] Firebase no disponible; revisa serviceAccountKey.json / FIREBASE_CREDENTIALS")
        return 1

    print("[OK] Firebase Firestore conectado")
    total = _escribir_presupuestos(db)
    print(f"✓ Presupuestos 2026 seedeados ({total} docs) en budgets/{{YYYY-MM}}/items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
