"""
Script de migración: toma el backup y migra a la nueva estructura Kebo.

Nueva estructura:
- users/{userId}/accounts/{accountId}
- users/{userId}/categories/{catId}
- users/{userId}/transactions/{year}/{month}/{txId}
- users/{userId}/goals/{goalId}
- users/{userId}/recurring/{recId}

Uso: python migrar_a_kebo.py backup_YYYYMMDD_HHMMSS.json
"""
import json
import sys
from datetime import datetime
from firebase_admin import firestore
from modules.database import inicializar_firebase

def migrar(archivo_backup, usuario_id="default"):
    db = inicializar_firebase()
    if not db:
        print("❌ No se pudo inicializar Firebase")
        return

    # Cargar backup
    with open(archivo_backup, "r", encoding="utf-8") as f:
        backup = json.load(f)

    print(f"📦 Backup cargado: {backup['fecha']}")
    print(f"   Usuario: {backup['usuario_id']}")

    # Crear documento de usuario si no existe
    user_ref = db.collection("users").document(usuario_id)
    user_ref.set({
        "nombre": "Pool",
        "config": {"moneda": "COP", "tema": "dark"},
        "created_at": firestore.SERVER_TIMESTAMP,
        "migrated_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
    print("✅ Usuario creado/actualizado")

    # Crear cuentas por defecto
    cuentas_default = [
        {"nombre": "Efectivo", "tipo": "cash", "balance": 0, "color": "#10b981", "icono": "💵"},
        {"nombre": "Nequi", "tipo": "debit", "balance": 0, "color": "#8b5cf6", "icono": "💜"},
        {"nombre": "Crédito", "tipo": "credit", "balance": 0, "color": "#ef4444", "icono": "💳"},
    ]
    cuenta_ids = {}
    for cuenta in cuentas_default:
        # Buscar si ya existe
        existing = user_ref.collection("accounts").where("nombre", "==", cuenta["nombre"]).limit(1).stream()
        existing_list = list(existing)
        if existing_list:
            cuenta_ids[cuenta["nombre"]] = existing_list[0].id
            print(f"   ⏭️  Cuenta '{cuenta['nombre']}' ya existe")
        else:
            doc_ref = user_ref.collection("accounts").document()
            doc_ref.set({**cuenta, "created_at": firestore.SERVER_TIMESTAMP})
            cuenta_ids[cuenta["nombre"]] = doc_ref.id
            print(f"   ✅ Cuenta creada: {cuenta['nombre']}")

    # Migrar presupuestos → categorías
    print("\n📁 Migrando presupuestos → categorías...")
    categoria_ids = {}
    for p in backup["colecciones"].get("presupuestos", []):
        cat_nombre = p.get("categoria", "General")
        # Buscar si ya existe
        existing = user_ref.collection("categories").where("nombre", "==", cat_nombre).limit(1).stream()
        existing_list = list(existing)
        if existing_list:
            categoria_ids[cat_nombre] = existing_list[0].id
            # Actualizar budget
            existing_list[0].reference.update({"budget": p.get("limite", 0)})
        else:
            doc_ref = user_ref.collection("categories").document()
            doc_ref.set({
                "nombre": cat_nombre,
                "budget": p.get("limite", 0),
                "color": "#3b82f6",
                "icono": "📊",
                "tipo": "variable",
                "created_at": firestore.SERVER_TIMESTAMP
            })
            categoria_ids[cat_nombre] = doc_ref.id
        print(f"   ✅ {cat_nombre}: ${p.get('limite', 0):,.0f}")

    # Migrar transacciones
    print("\n📁 Migrando transacciones...")
    cuenta_default = cuenta_ids.get("Efectivo", list(cuenta_ids.values())[0])
    cat_default = list(categoria_ids.values())[0] if categoria_ids else None

    count_tx = 0
    for t in backup["colecciones"].get("finanzas", []):
        # Extraer fecha y mes
        fecha_str = t.get("fecha", "")
        timestamp = t.get("timestamp")
        mes_str = t.get("mes", "")

        if not mes_str and fecha_str and len(fecha_str) >= 7:
            mes_str = fecha_str[:7]

        if not mes_str:
            # Usar fecha actual como fallback
            mes_str = datetime.now().strftime("%Y-%m")

        year, month = mes_str.split("-")

        # Buscar categoría
        cat_nombre = t.get("categoria", "General")
        cat_id = categoria_ids.get(cat_nombre, cat_default)

        # Crear transacción en subcol por mes
        tx_data = {
            "tipo": t.get("tipo", "gasto"),  # expense/income
            "monto": float(t.get("monto", 0)),
            "account_id": cuenta_default,
            "category_id": cat_id,
            "descripcion": t.get("descripcion", ""),
            "fecha": fecha_str or datetime.now().strftime("%Y-%m-%d"),
            "tags": [],
            "created_at": timestamp or firestore.SERVER_TIMESTAMP
        }

        user_ref.collection("transactions").document(year).document(month).collection("items").add(tx_data)
        count_tx += 1

    print(f"   ✅ {count_tx} transacciones migradas")

    # Migrar tareas (opcional, las guardamos aparte por ahora)
    print("\n📁 Tareas no se migran (se mantienen en colección legacy)")

    print("\n✅ MIGRACIÓN COMPLETA")
    print(f"   Cuentas: {len(cuenta_ids)}")
    print(f"   Categorías: {len(categoria_ids)}")
    print(f"   Transacciones: {count_tx}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python migrar_a_kebo.py backup_YYYYMMDD_HHMMSS.json")
    else:
        migrar(sys.argv[1])
