"""
database_v2.py - Nueva estructura Kebo
Mantiene compatibilidad con database.py viejo.

Nueva estructura:
- users/{userId}/accounts/{accountId}
- users/{userId}/categories/{catId}
- users/{userId}/transactions/{year}/{month}/{txId}
- users/{userId}/goals/{goalId}
- users/{userId}/recurring/{recId}
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, initialize_app, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime
import calendar

# Reutilizar la inicialización de database.py
from modules.database import inicializar_firebase

def _get_user_ref(usuario_id="default"):
    """Obtiene referencia al usuario."""
    db = inicializar_firebase()
    if not db:
        return None, None
    return db, db.collection("users").document(usuario_id)

# ==================== USUARIOS ====================

def ensure_user(usuario_id="default", nombre=""):
    """Crea el documento de usuario si no existe."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return
    user_ref.set({
        "nombre": nombre or usuario_id,
        "config": {"moneda": "COP", "tema": "dark"},
        "created_at": firestore.SERVER_TIMESTAMP
    }, merge=True)

# ==================== CUENTAS ====================

def listar_cuentas(usuario_id="default"):
    """Lista todas las cuentas del usuario."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("accounts").stream()
        return [{**d.to_dict(), "_id": d.id} for d in docs]
    except Exception as e:
        print(f"Error listando cuentas: {e}")
        return []

def crear_cuenta(usuario_id, nombre, tipo="cash", balance=0, icono="💵", color="#10b981"):
    """Crea una nueva cuenta."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        doc_ref = user_ref.collection("accounts").document()
        doc_ref.set({
            "nombre": nombre,
            "tipo": tipo,  # cash, debit, credit, savings
            "balance": float(balance),
            "icono": icono,
            "color": color,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error creando cuenta: {e}")
        return None

def actualizar_balance_cuenta(usuario_id, cuenta_id, delta):
    """Suma delta al balance de una cuenta."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return
    try:
        user_ref.collection("accounts").document(cuenta_id).update({
            "balance": firestore.Increment(delta)
        })
    except Exception as e:
        print(f"Error actualizando balance: {e}")

# ==================== CATEGORÍAS ====================

def listar_categorias(usuario_id="default"):
    """Lista todas las categorías."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("categories").stream()
        return [{**d.to_dict(), "_id": d.id} for d in docs]
    except Exception as e:
        print(f"Error listando categorías: {e}")
        return []

def crear_categoria(usuario_id, nombre, budget=0, tipo="variable", icono="📊", color="#3b82f6"):
    """Crea una nueva categoría con presupuesto."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        # Verificar si ya existe
        existing = user_ref.collection("categories").where("nombre", "==", nombre).limit(1).stream()
        existing_list = list(existing)
        if existing_list:
            return existing_list[0].id
        doc_ref = user_ref.collection("categories").document()
        doc_ref.set({
            "nombre": nombre,
            "budget": float(budget),
            "tipo": tipo,
            "icono": icono,
            "color": color,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error creando categoría: {e}")
        return None

def actualizar_presupuesto_categoria(usuario_id, nombre, nuevo_budget):
    """Actualiza el presupuesto de una categoría por nombre."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        docs = user_ref.collection("categories").where("nombre", "==", nombre).limit(1).stream()
        docs_list = list(docs)
        if docs_list:
            docs_list[0].reference.update({"budget": float(nuevo_budget)})
            return True
        return False
    except Exception as e:
        print(f"Error actualizando presupuesto: {e}")
        return False

# ==================== TRANSACCIONES ====================

def registrar_transaccion_v2(usuario_id, tipo, monto, categoria_nombre, descripcion="", cuenta_nombre="Efectivo"):
    """Registra transacción en nueva estructura."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)

        # Buscar o crear categoría
        cat_id = crear_categoria(usuario_id, categoria_nombre)

        # Buscar cuenta
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        if cuenta_list:
            cuenta_id = cuenta_list[0].id
        else:
            cuenta_id = crear_cuenta(usuario_id, cuenta_nombre, "cash")

        # Crear transacción
        ahora = datetime.now()
        year = str(ahora.year)
        month = f"{ahora.month:02d}"
        fecha = ahora.strftime("%Y-%m-%d")

        tx_ref = user_ref.collection("transactions").document(year).document(month).collection("items").document()
        tx_data = {
            "tipo": tipo,  # expense, income
            "monto": float(monto),
            "account_id": cuenta_id,
            "category_id": cat_id,
            "descripcion": descripcion,
            "fecha": fecha,
            "tags": [],
            "created_at": firestore.SERVER_TIMESTAMP
        }
        tx_ref.set(tx_data)

        # Actualizar balance de la cuenta
        if tipo == "expense":
            actualizar_balance_cuenta(usuario_id, cuenta_id, -float(monto))
        else:
            actualizar_balance_cuenta(usuario_id, cuenta_id, float(monto))

        return tx_ref.id
    except Exception as e:
        print(f"Error registrando transacción v2: {e}")
        return None

def obtener_balance_v2(usuario_id="default", mes=None):
    """Obtiene balance del mes actual o especificado."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return 0.0, 0.0, 0.0, []

    if not mes:
        mes = datetime.now().strftime("%Y-%m")

    year, month = mes.split("-")

    try:
        docs = user_ref.collection("transactions").document(year).document(month).collection("items").stream()
        ingresos = 0.0
        gastos = 0.0
        transacciones = []
        for d in docs:
            t = d.to_dict()
            t["_id"] = d.id
            monto = float(t.get("monto", 0))
            tipo = t.get("tipo", "expense")
            transacciones.append(t)
            if tipo == "income":
                ingresos += monto
            else:
                gastos += monto
        balance = ingresos - gastos
        return balance, ingresos, gastos, transacciones
    except Exception as e:
        print(f"Error obteniendo balance v2: {e}")
        return 0.0, 0.0, 0.0, []

def obtener_presupuestos_v2(usuario_id="default", mes=None):
    """Obtiene presupuestos con gastado del mes."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return {}

    if not mes:
        mes = datetime.now().strftime("%Y-%m")

    year, month = mes.split("-")

    try:
        # Obtener categorías con budget
        cats = listar_categorias(usuario_id)
        presupuestos = {}

        # Obtener gastos del mes por categoría
        docs = user_ref.collection("transactions").document(year).document(month).collection("items").stream()
        gastos_por_cat = {}
        for d in docs:
            t = d.to_dict()
            if t.get("tipo") == "expense":
                cat_id = t.get("category_id")
                monto = float(t.get("monto", 0))
                gastos_por_cat[cat_id] = gastos_por_cat.get(cat_id, 0) + monto

        # Combinar
        for cat in cats:
            nombre = cat.get("nombre")
            budget = float(cat.get("budget", 0))
            gastado = gastos_por_cat.get(cat["_id"], 0)
            presupuestos[nombre] = {
                "limite": budget,
                "gastado": gastado,
                "libre": budget - gastado,
                "excedido": (budget - gastado) < 0
            }
        return presupuestos
    except Exception as e:
        print(f"Error presupuestos v2: {e}")
        return {}

# ==================== METAS ====================

def guardar_meta_v2(usuario_id, nombre, monto_objetivo, fecha_limite="", cuenta_nombre="Efectivo"):
    """Crea meta en nueva estructura."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        doc_ref = user_ref.collection("goals").document()
        doc_ref.set({
            "nombre": nombre,
            "monto_objetivo": float(monto_objetivo),
            "current_amount": 0.0,
            "fecha_limite": fecha_limite,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error guardando meta v2: {e}")
        return None
