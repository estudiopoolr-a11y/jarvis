"""Ingesta de datos financieros 2026 en Firebase Firestore.

Escribe en el esquema raiz que consumen el dashboard y los widgets:
- transactions/{YYYY-MM}/items  : ingresos y gastos por categoria/mes
- categories                   : catalogo de categorias usadas
- loans                        : detalle de prestamos realizados
- finanzas/2026                : nodo resumen (esquema de la directiva)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_admin import firestore  # noqa: E402
from modules.firestore.client import inicializar_firebase  # noqa: E402

# --- Datos fuente: ingresos mensuales 2026 (COP) ---
INGRESOS_2026 = {
    "2026-05": 1061159.03,
    "2026-06": 1058894.26,
    "2026-07": 936455.00,
    "2026-08": 806199.03,
}

# --- Gastos por categoria mes a mes (COP) ---
GASTOS_2026 = {
    "2026-05": {
        "total": 713000.00,
        "categorias": {
            "Moto": 212700.00,
            "Madre": 185000.00,
            "Deudas": 140000.00,
            "Alimentación": 70300.00,
            "Fútbol": 50000.00,
            "Gym": 35000.00,
            "Use personal": 18000.00,
            "Gastos tontos": 2000.00,
        },
    },
    "2026-06": {
        "total": 616500.00,
        "categorias": {
            "Madre": 150000.00,
            "Gastos tontos": 145500.00,
            "Deudas": 126000.00,
            "Padre": 100000.00,
            "Use personal": 50000.00,
            "Moto": 45000.00,
            "Gym": 0.00,
            "Ahorro": 0.00,
            "Préstamos": 0.00,
        },
    },
    "2026-07": {
        "total": 1094775.69,
        "categorias": {
            "Women": 265100.00,
            "Moto": 222427.00,
            "Préstamos": 172500.00,
            "Use personal": 136729.00,
            "Gastos tontos": 130519.69,
            "Alimentación": 120000.00,
            "Fútbol": 47500.00,
        },
    },
    "2026-08": {
        "total": 876440.00,
        "categorias": {
            "Deudas": 205000.00,
            "Alimentación": 150000.00,
            "Use personal": 97900.00,
            "Madre": 50000.00,
            "Moto": 31000.00,
            # Diferencia declarada por el usuario para categorías no detalladas.
            "Otros": 342540.00,
        },
    },
}

# --- Catalogo visual de categorias ---
CATEGORIAS = {
    "Moto": {"icono": "🏍️", "color": "#8b5cf6"},
    "Madre": {"icono": "👩", "color": "#ec4899"},
    "Padre": {"icono": "👨", "color": "#0ea5e9"},
    "Deudas": {"icono": "💳", "color": "#ef4444"},
    "Alimentación": {"icono": "🍎", "color": "#22c55e"},
    "Fútbol": {"icono": "⚽", "color": "#10b981"},
    "Gym": {"icono": "🏋️", "color": "#f59e0b"},
    "Use personal": {"icono": "💸", "color": "#3b82f6"},
    "Gastos tontos": {"icono": "😅", "color": "#6b7280"},
    "Women": {"icono": "👗", "color": "#d946ef"},
    "Ahorro": {"icono": "🐷", "color": "#84cc16"},
    "Préstamos": {"icono": "🤝", "color": "#f97316"},
}

# --- Prestamos individuales (fecha, persona, monto) ---
PRESTAMOS_2026 = [
    {"fecha": "2026-08-24", "persona": "Jhostyn", "monto": 40000.00},
    {"fecha": "2026-08-24", "persona": "Mamá pañales Saló", "monto": 20000.00},
    {"fecha": "2026-07-31", "persona": "Brother", "monto": 50000.00},
    {"fecha": "2026-07-31", "persona": "Cinemark", "monto": 32500.00},
    {"fecha": "2026-07-31", "persona": "Váscula", "monto": 50000.00},
    {"fecha": "2026-07-21", "persona": "Brother", "monto": 20000.00},
    {"fecha": "2026-07-21", "persona": "Brother", "monto": 20000.00},
]


def _mes_tiene_items(db, ym):
    """True si el mes ya tiene transacciones registradas (evita duplicar en re-ejecuciones)."""
    return any(True for _ in db.collection("transactions").document(ym).collection("items").limit(1).stream())


def _crear_categoria_si_falta(db, nombre, icono, color):
    """Crea una categoria solo si no existe una con el mismo nombre."""
    existentes = list(db.collection("categories").where("nombre", "==", nombre).limit(1).stream())
    if existentes:
        return existentes[0].id
    doc = db.collection("categories").document()
    doc.set({
        "nombre": nombre,
        "budget": 0.0,
        "tipo": "variable",
        "icono": icono,
        "color": color,
    })
    return doc.id


def _escribir_transacciones(db):
    """Registra ingresos y gastos por mes en transactions/{YYYY-MM}/items."""
    for ym, ingresos in INGRESOS_2026.items():
        if _mes_tiene_items(db, ym):
            print(f"[SKIP] 2026-{ym[-2:]} ya tiene transacciones; no se duplica")
            continue
        items = db.collection("transactions").document(ym).collection("items")

        # Ingreso mensual
        items.add({
            "type": "income",
            "amount": float(ingresos),
            "category_name": "Ingresos",
            "description": f"Ingresos {ym}",
            "date": f"{ym}-05",
            "created_at": firestore.SERVER_TIMESTAMP,
        })

        # Gastos por categoria
        categorias = GASTOS_2026[ym]["categorias"]
        for categoria, monto in categorias.items():
            if monto <= 0:
                continue
            items.add({
                "type": "expense",
                "amount": float(monto),
                "category_name": categoria,
                "description": f"{categoria} {ym}",
                "date": f"{ym}-15",
                "created_at": firestore.SERVER_TIMESTAMP,
            })
        print(f"[OK] Transacciones {ym}: 1 ingreso + {sum(1 for m in categorias.values() if m > 0)} gastos")


def _escribir_prestamos(db):
    """Registra prestamos individuales idempotentes (persona + fecha + monto)."""
    existentes = {
        (d.get("persona"), d.get("fecha"), float(d.get("monto", 0)))
        for d in (doc.to_dict() or {} for doc in db.collection("loans").stream())
    }
    creados = 0
    for p in PRESTAMOS_2026:
        clave = (p["persona"], p["fecha"], p["monto"])
        if clave in existentes:
            continue
        db.collection("loans").add({
            "persona": p["persona"],
            "monto": float(p["monto"]),
            "monto_original": float(p["monto"]),
            "monto_pagado": 0.0,
            "monto_pendiente": float(p["monto"]),
            "fecha": p["fecha"],
            "nota": "",
            "status": "pendiente",
            "pagos": [],
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        creados += 1
    print(f"[OK] Prestamos: {creados} nuevos ({(len(PRESTAMOS_2026) - creados)} ya existian)")


def _escribir_resumen(db):
    """Escribe el nodo resumen finanzas/2026 con el esquema de la directiva."""
    gastos_por_categoria = {
        f"{ym.replace('-', '_')}": {
            "total": data["total"],
            "categorias": data["categorias"],
        }
        for ym, data in GASTOS_2026.items()
    }
    resumen = {
        "ingresos": {
            **{f"mes_{k[5:]}": v for k, v in INGRESOS_2026.items()},
            "total_ingresos": sum(INGRESOS_2026.values()),
        },
        "gastos_por_categoria": gastos_por_categoria,
        "prestamos_detalle": {
            "acumulado_total": sum(p["monto"] for p in PRESTAMOS_2026),
            "transacciones": [
                {"fecha": p["fecha"], "concepto": p["persona"], "monto": p["monto"]}
                for p in PRESTAMOS_2026
            ],
        },
    }
    db.collection("finanzas").document("2026").set(resumen)
    print("[OK] Resumen finanzas/2026 escrito (ingresos, gastos, prestamos)")


def main():
    db = inicializar_firebase()
    if db is None:
        print("[ERR] Firebase no disponible; revisa serviceAccountKey.json / FIREBASE_CREDENTIALS")
        return 1

    print("[OK] Firebase Firestore conectado")

    # 1. Categorias (solo si faltan)
    for nombre, meta in CATEGORIAS.items():
        cat_id = _crear_categoria_si_falta(db, nombre, meta["icono"], meta["color"])
        print(f"[OK] Categoria '{nombre}' -> {cat_id}")

    # 2. Transacciones mensuales
    _escribir_transacciones(db)

    # 3. Prestamos
    _escribir_prestamos(db)

    # 4. Nodo resumen
    _escribir_resumen(db)

    print("✓ Datos financieros de 2026 indexados y sincronizados exitosamente en Firebase")
    return 0


if __name__ == "__main__":
    sys.exit(main())