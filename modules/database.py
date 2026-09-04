"""
database.py - JARVIS Database Module
====================================

Estructura Firestore estilo KEBO:
users/{userId}/
  ├── accounts/{accountId}                 # Cuentas con metadata Kebo:
  │   ├── name, type (cash|savings|checking|credit|investment)
  │   ├── currency, institution, bank_last4
  │   ├── balance, icon, color
  │
  ├── categories/{categoryId}              # Categorías con sub-categorías
  │   ├── name, icon, color, type (fijo|variable)
  │   └── subcategories/{subId}: name, icon, color
  │       ⭐ Ejemplo: "Comida" → "Restaurantes", "Mercado", "Panadería"
  │
  ├── transactions/{year}/{month}/items/{txId}    # Transacciones por mes
  │   ├── type (income|expense|transfer)
  │   ├── amount, account_id, category_id
  │   ├── payee, description, fee, status (pending|cleared)
  │   ├── tags, date, created_at
  │
  ├── budgets/{year}/{month}/items/{id}          # ⭐ Presupuestos por mes+año (Kebo style)
  │   ├── category_id, category_name, amount
  │
  ├── goals/{goalId}                       # Metas de ahorro
  │   ├── name, target_amount, current_amount, deadline
  │
  └── recurring/{recId}                    # Pagos recurrentes
      ├── name, amount, day, frequency, category_id, account_id

Estructura legacy (compatibilidad):
- finanzas/, presupuestos/, metas/, pagos_fijos/, tareas/

Autor: JARVIS AI Assistant
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, initialize_app, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta

db = None

# ==================== FIREBASE ====================

def inicializar_firebase():
    """Inicializa Firebase Firestore soportando variables de entorno, creación automática de archivo temporal o archivo local."""
    global db
    if not firebase_admin._apps:
        firebase_json_str = (
            os.getenv("FIREBASE_CREDENTIALS") or
            os.getenv("FIREBASE_CREDENTIALS_JSON") or
            os.getenv("FIREBASE_KEY") or
            os.getenv("FIREBASE_SERVICE_ACCOUNT")
        )

        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")

        if firebase_json_str:
            try:
                firebase_json_str = firebase_json_str.strip()
                if (firebase_json_str.startswith("'") and firebase_json_str.endswith("'")) or \
                   (firebase_json_str.startswith('"') and firebase_json_str.endswith('"')):
                    firebase_json_str = firebase_json_str[1:-1].strip()

                with open(cred_path, "w", encoding="utf-8") as f:
                    f.write(firebase_json_str)

                cred = credentials.Certificate(cred_path)
                initialize_app(cred)
                print("✅ Firebase inicializado con éxito creando archivo de credenciales desde la variable de entorno de Render.")
            except Exception as e:
                print(f"❌ Error crítico procesando credenciales desde la variable de entorno: {e}")
                try:
                    cred_dict = json.loads(firebase_json_str)
                    cred = credentials.Certificate(cred_dict)
                    initialize_app(cred)
                    print("✅ Firebase inicializado con éxito desde diccionario JSON directo.")
                except Exception as e2:
                    print(f"❌ Error secundario al inicializar con diccionario: {e2}")

        if not firebase_admin._apps:
            if os.path.exists(cred_path):
                try:
                    cred = credentials.Certificate(cred_path)
                    initialize_app(cred)
                    print(f"✅ Firebase inicializado desde archivo local '{cred_path}'.")
                except Exception as e:
                    print(f"❌ Error cargando archivo local '{cred_path}': {e}")
            else:
                print("⚠️ Advertencia CRÍTICA: No se encontró la variable de entorno FIREBASE_CREDENTIALS ni el archivo de credenciales en Render.")

    if firebase_admin._apps:
        db = firestore.client()
    return db


# ==================== HELPERS ====================

def _get_user_ref(usuario_id="default"):
    """Obtiene referencia al documento del usuario (estructura Kebo)."""
    if not db: inicializar_firebase()
    if not db:
        return None, None
    return db, db.collection("users").document(usuario_id)


# ==================== MONEDAS Y CONVERSIONES (KEBO) ====================

# Tasas de cambio default (COP base). Se pueden actualizar con tasas reales.
# Estructura: users/{userId}/exchange_rates/{currency}/ (rate, updated_at)
TASAS_DEFAULT = {
    "COP": 1.0,
    "USD": 4100.0,   # 1 USD = 4100 COP
    "EUR": 4500.0,   # 1 EUR = 4500 COP
    "GBP": 5200.0,   # 1 GBP = 5200 COP
    "MXN": 230.0,    # 1 MXN = 230 COP
    "ARS": 4.5,      # 1 ARS = 4.5 COP
}

MONEDAS_SIMBOLO = {
    "COP": "$",
    "USD": "US$",
    "EUR": "€",
    "GBP": "£",
    "MXN": "$",
    "ARS": "$",
}


def convertir_monto(monto, de_moneda, a_moneda="COP"):
    """Convierte un monto entre monedas usando tasas guardadas o default."""
    if de_moneda == a_moneda:
        return float(monto)
    _, user_ref = _get_user_ref()
    if not user_ref:
        return float(monto)
    try:
        # Intentar leer tasa guardada
        rate_doc = user_ref.collection("exchange_rates").document(de_moneda).get()
        if rate_doc.exists:
            rate = rate_doc.to_dict().get("rate", TASAS_DEFAULT.get(de_moneda, 1.0))
        else:
            rate = TASAS_DEFAULT.get(de_moneda, 1.0)
        # Convertir a COP primero, luego a la moneda destino
        en_cop = float(monto) * rate
        if a_moneda == "COP":
            return en_cop
        # Leer tasa destino
        rate_dest = user_ref.collection("exchange_rates").document(a_moneda).get()
        if rate_dest.exists:
            rate_dest_val = rate_dest.to_dict().get("rate", TASAS_DEFAULT.get(a_moneda, 1.0))
        else:
            rate_dest_val = TASAS_DEFAULT.get(a_moneda, 1.0)
        return en_cop / rate_dest_val
    except Exception:
        return float(monto)


def guardar_tasa_cambio(usuario_id, moneda, tasa):
    """Guarda una tasa de cambio personalizada para el usuario."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        user_ref.collection("exchange_rates").document(moneda).set({
            "rate": float(tasa),
            "updated_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
        return True
    except Exception as e:
        print(f"Error guardando tasa: {e}")
        return False


def obtener_tasas_cambio(usuario_id):
    """Obtiene todas las tasas de cambio guardadas."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return {}
    try:
        tasas = {}
        for d in user_ref.collection("exchange_rates").stream():
            tasas[d.id] = d.to_dict()
        return tasas
    except Exception:
        return {}


def obtener_balance_total_multimoneda(usuario_id, moneda_base="COP"):
    """Obtiene el balance total convertido a una moneda base.
    Suma balances de todas las cuentas, convirtiendo cada una a la moneda base.
    """
    cuentas = listar_cuentas(usuario_id)
    total = 0.0
    for c in cuentas:
        balance = float(c.get("balance", 0))
        currency = c.get("currency", "COP")
        total += convertir_monto(balance, currency, moneda_base)
    return total


# ==================== USUARIOS (KEBO) ====================

def ensure_user(usuario_id="default", nombre=""):
    """Crea el documento de usuario si no existe."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return
    user_ref.set({
        "nombre": nombre or usuario_id,
        "config": {"moneda": "COP", "tema": "dark"},
        "created_at": firestore.SERVER_TIMESTAMP
    }, merge=True)


# ==================== CUENTAS (KEBO) ====================

def listar_cuentas(usuario_id="default"):
    """Lista todas las cuentas del usuario (estilo Kebo).
    Incluye: nombre, type, currency, institution, bank_last4, balance, icon, color.
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("accounts").stream()
        cuentas = []
        for d in docs:
            data = d.to_dict()
            # Compatibilidad: viejo (tipo/icono) -> nuevo (type/icon)
            cuentas.append({
                "_id": d.id,
                "nombre": data.get("nombre", ""),
                "type": data.get("type") or data.get("tipo", "cash"),    # Kebo: type
                "currency": data.get("currency", "COP"),                   # Kebo: currency
                "institution": data.get("institution", ""),              # Kebo: institution
                "bank_last4": data.get("bank_last4", ""),                  # Kebo: bank_last4
                "balance": float(data.get("balance", 0)),
                "icon": data.get("icon") or data.get("icono", "💵"),      # Kebo: icon
                "color": data.get("color", "#10b981"),
                # Alias legacy
                "tipo": data.get("type") or data.get("tipo", "cash"),
                "icono": data.get("icon") or data.get("icono", "💵"),
            })
        return cuentas
    except Exception as e:
        print(f"Error listando cuentas: {e}")
        return []

def crear_cuenta(usuario_id, nombre, tipo="cash", balance=0, icono="💵", color="#10b981",
                 currency="COP", institution="", bank_last4=""):
    """Crea una nueva cuenta con metadata estilo Kebo.
    tipo: cash | savings | checking | credit | investment
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        doc_ref = user_ref.collection("accounts").document()
        doc_ref.set({
            "nombre": nombre,
            "type": tipo,                          # Campo Kebo: 'type' en inglés
            "currency": currency,                  # Campo Kebo: moneda base
            "institution": institution,            # Campo Kebo: banco (Bancolombia, Davivienda, etc.)
            "bank_last4": bank_last4,              # Campo Kebo: últimos 4 dígitos
            "balance": float(balance),
            "icon": icono,                         # Campo Kebo: 'icon' en inglés
            "color": color,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error creando cuenta: {e}")
        return None

def actualizar_balance_cuenta(usuario_id, cuenta_id, delta):
    """Suma delta al balance de una cuenta."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return
    try:
        user_ref.collection("accounts").document(cuenta_id).update({
            "balance": firestore.Increment(delta)
        })
    except Exception as e:
        print(f"Error actualizando balance: {e}")


# ==================== CATEGORÍAS (KEBO) ====================

CATEGORIAS_PREDEFINIDAS = [
    {"nombre": "Alimentación", "icono": "🍔", "color": "#f59e0b", "tipo": "variable"},
    {"nombre": "Transporte", "icono": "🚗", "color": "#6366f1", "tipo": "variable"},
    {"nombre": "Servicios", "icono": "💡", "color": "#8b5cf6", "tipo": "fijo"},
    {"nombre": "Arriendo", "icono": "🏠", "color": "#ec4899", "tipo": "fijo"},
    {"nombre": "Entretenimiento", "icono": "🎬", "color": "#06b6d4", "tipo": "variable"},
    {"nombre": "Salud", "icono": "🏥", "color": "#ef4444", "tipo": "variable"},
    {"nombre": "Educación", "icono": "📚", "color": "#3b82f6", "tipo": "variable"},
    {"nombre": "Ropa", "icono": "👕", "color": "#10b981", "tipo": "variable"},
    {"nombre": "Hogar", "icono": "🏡", "color": "#84cc16", "tipo": "variable"},
    {"nombre": "Mascotas", "icono": "🐕", "color": "#f97316", "tipo": "variable"},
    {"nombre": "Celular", "icono": "📱", "color": "#a855f7", "tipo": "fijo"},
    {"nombre": "Internet", "icono": "🌐", "color": "#14b8a6", "tipo": "fijo"},
    {"nombre": "Deudas", "icono": "💳", "color": "#f43f5e", "tipo": "fijo"},
    {"nombre": "Ahorro", "icono": "🏦", "color": "#22c55e", "tipo": "variable"},
    {"nombre": "Inversión", "icono": "📈", "color": "#eab308", "tipo": "variable"},
    {"nombre": "Otros", "icono": "📦", "color": "#6b7280", "tipo": "variable"},
]

def listar_categorias(usuario_id="default"):
    """Lista todas las categorías."""
    _, user_ref = _get_user_ref(usuario_id)
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
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
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

def crear_categorias_predefinidas(usuario_id="default"):
    """Crea todas las categorías predefinidas para un usuario."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return 0
    try:
        ensure_user(usuario_id)
        count = 0
        for cat in CATEGORIAS_PREDEFINIDAS:
            existing = user_ref.collection("categories").where("nombre", "==", cat["nombre"]).limit(1).stream()
            existing_list = list(existing)
            if not existing_list:
                doc_ref = user_ref.collection("categories").document()
                doc_ref.set({
                    "nombre": cat["nombre"],
                    "icono": cat["icono"],
                    "color": cat["color"],
                    "tipo": cat["tipo"],
                    "budget": 0.0,
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                count += 1
        return count
    except Exception as e:
        print(f"Error creando categorías predefinidas: {e}")
        return 0


# ==================== SUB-CATEGORÍAS (KEBO) ====================

SUB_CATEGORIAS_PREDEFINIDAS = {
    "Alimentación": [
        {"nombre": "Restaurantes", "icono": "🍽️", "color": "#f59e0b"},
        {"nombre": "Mercado", "icono": "🛒", "color": "#10b981"},
        {"nombre": "Panadería", "icono": "🥖", "color": "#eab308"},
        {"nombre": "Café", "icono": "☕", "color": "#8b5cf6"},
        {"nombre": "Delivery", "icono": "🛵", "color": "#06b6d4"},
    ],
    "Transporte": [
        {"nombre": "Uber/DiDi", "icono": "🚗", "color": "#6366f1"},
        {"nombre": "Gasolina", "icono": "⛽", "color": "#ef4444"},
        {"nombre": "Transporte público", "icono": "🚌", "color": "#3b82f6"},
        {"nombre": "Parqueadero", "icono": "🅿️", "color": "#6b7280"},
    ],
    "Entretenimiento": [
        {"nombre": "Cine", "icono": "🎬", "color": "#ec4899"},
        {"nombre": "Streaming", "icono": "📺", "color": "#ef4444"},
        {"nombre": "Videojuegos", "icono": "🎮", "color": "#8b5cf6"},
        {"nombre": "Conciertos", "icono": "🎵", "color": "#f59e0b"},
    ],
    "Salud": [
        {"nombre": "Medicamentos", "icono": "💊", "color": "#ef4444"},
        {"nombre": "Doctor", "icono": "👨‍⚕️", "color": "#3b82f6"},
        {"nombre": "Gimnasio", "icono": "🏋️", "color": "#10b981"},
        {"nombre": "Veterinaria", "icono": "🐕", "color": "#f97316"},
    ],
}


def listar_subcategorias(usuario_id, categoria_nombre):
    """Lista sub-categorías de una categoría padre."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        # Buscar categoría padre
        cats = user_ref.collection("categories").where("nombre", "==", categoria_nombre).limit(1).stream()
        cats_list = list(cats)
        if not cats_list:
            return []
        cat_id = cats_list[0].id
        docs = user_ref.collection("categories").document(cat_id).collection("subcategories").stream()
        return [{**d.to_dict(), "_id": d.id} for d in docs]
    except Exception as e:
        print(f"Error listando subcategorías: {e}")
        return []


def crear_subcategoria(usuario_id, categoria_nombre, sub_nombre, icono="📁", color="#6b7280"):
    """Crea una sub-categoría dentro de una categoría padre."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        cats = user_ref.collection("categories").where("nombre", "==", categoria_nombre).limit(1).stream()
        cats_list = list(cats)
        if not cats_list:
            return None
        cat_id = cats_list[0].id
        doc_ref = user_ref.collection("categories").document(cat_id).collection("subcategories").document()
        doc_ref.set({
            "nombre": sub_nombre,
            "icono": icono,
            "color": color,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error creando subcategoría: {e}")
        return None


def crear_subcategorias_predefinidas(usuario_id):
    """Crea todas las sub-categorías predefinidas para un usuario."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return 0
    count = 0
    for cat_nombre, subcats in SUB_CATEGORIAS_PREDEFINIDAS.items():
        cats = user_ref.collection("categories").where("nombre", "==", cat_nombre).limit(1).stream()
        cats_list = list(cats)
        if not cats_list:
            continue
        cat_id = cats_list[0].id
        for sub in subcats:
            existing = user_ref.collection("categories").document(cat_id).collection("subcategories").where("nombre", "==", sub["nombre"]).limit(1).stream()
            if not list(existing):
                user_ref.collection("categories").document(cat_id).collection("subcategories").document().set({
                    "nombre": sub["nombre"],
                    "icono": sub["icono"],
                    "color": sub["color"],
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                count += 1
    return count


def actualizar_presupuesto_categoria(usuario_id, nombre, nuevo_budget):
    """Actualiza el presupuesto de una categoría por nombre (compatibilidad).
    En la nueva estructura Kebo, el budget vive en budgets/{year}/{month}/items/.
    Esta función actualiza ambos: el default en categories y el mes actual.
    """
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
        # Buscar presupuesto existente para esta categoría en este mes
        budget_ref = user_ref.collection("budgets").document(year).collection(month).collection("items")
        existing = budget_ref.where("category_name", "==", nombre).limit(1).stream()
        existing_list = list(existing)
        if existing_list:
            existing_list[0].reference.update({"amount": float(nuevo_budget)})
        else:
            # Buscar category_id
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


def establecer_presupuesto_mes(usuario_id, categoria_nombre, monto, year=None, month=None):
    """Establece un presupuesto para una categoría en un mes específico (Kebo style).
    Estructura: users/{userId}/budgets/{year}/{month}/items/{id}
    """
    if not year:
        year = str(datetime.now().year)
    if not month:
        month = f"{datetime.now().month:02d}"

    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        ensure_user(usuario_id)

        # Buscar o crear categoría
        cat_id = crear_categoria(usuario_id, categoria_nombre)

        # Buscar si ya existe un presupuesto para esta categoría en este mes
        items_ref = user_ref.collection("budgets").document(year).collection(month).collection("items")
        existing = items_ref.where("category_id", "==", cat_id).limit(1).stream()
        existing_list = list(existing)

        if existing_list:
            existing_list[0].reference.update({"amount": float(monto)})
        else:
            items_ref.document().set({
                "category_id": cat_id,
                "category_name": categoria_nombre,
                "amount": float(monto),
                "year": year,
                "month": month,
                "created_at": firestore.SERVER_TIMESTAMP
            })
        return True
    except Exception as e:
        print(f"Error estableciendo presupuesto mes: {e}")
        return False


def obtener_presupuestos_mes(usuario_id, year=None, month=None):
    """Obtiene los presupuestos de un mes específico (Kebo style).
    Si no hay presupuestos para ese mes, usa los default de categories.
    """
    if not year:
        year = str(datetime.now().year)
    if not month:
        month = f"{datetime.now().month:02d}"

    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []

    presupuestos_mes = {}
    try:
        # Primero intentar leer del mes específico
        items_ref = user_ref.collection("budgets").document(year).collection(month).collection("items")
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


# ==================== TRANSACCIONES (KEBO) ====================

def registrar_transaccion_v2(usuario_id, tipo, monto, categoria_nombre, descripcion="", cuenta_nombre="Efectivo",
                             payee="", fee=0.0, status="cleared", tags=None):
    """Registra transacción en nueva estructura Kebo.

    Campos estilo Kebo:
    - payee: Beneficiario/comercio (ej. "D1", "Netflix", "Uber")
    - fee: Comisión adicional (transferencias internacionales, etc.)
    - status: "pending" | "cleared" (si ya se procesó en el banco)
    - tags: lista de hashtags transversales (ej. ["#vacaciones", "#proyecto"])
    """
    if tags is None:
        tags = []
    _, user_ref = _get_user_ref(usuario_id)
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

        tx_ref = user_ref.collection("transactions").document(year).collection(month).collection("items").document()
        tx_ref.set({
            "type": tipo,                          # Kebo usa 'type' en inglés
            "amount": float(monto),                # Kebo usa 'amount' en inglés
            "account_id": cuenta_id,
            "category_id": cat_id,
            "payee": payee,                        # Kebo: beneficiario/comercio
            "description": descripcion,            # Kebo: 'description' en inglés
            "fee": float(fee),                     # Kebo: comisión
            "status": status,                      # Kebo: pending | cleared
            "tags": tags,                          # Kebo: etiquetas transversales
            "date": fecha,                         # Kebo: 'date' en inglés
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # Actualizar balance (considerando fee si es gasto)
        delta = -float(monto)
        if tipo == "income":
            delta = float(monto)
        if fee and tipo == "expense":
            delta -= float(fee)
        actualizar_balance_cuenta(usuario_id, cuenta_id, delta)

        return tx_ref.id
    except Exception as e:
        print(f"Error registrando transacción v2: {e}")
        return None

def registrar_transferencia(usuario_id, cuenta_origen, cuenta_destino, monto, descripcion="", fee=0.0):
    """Registra transferencia entre dos cuentas (Kebo style).
    - tipo: 'transfer' (no cuenta como gasto ni ingreso)
    - No afecta estadísticas de gastos mensuales
    - fee: comisión cobrada por el banco
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None, "DB no disponible"
    try:
        ensure_user(usuario_id)

        origen_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_origen).limit(1).stream()
        origen_list = list(origen_ref)
        if not origen_list:
            return None, f"No existe la cuenta origen '{cuenta_origen}'"
        origen_id = origen_list[0].id

        destino_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_destino).limit(1).stream()
        destino_list = list(destino_ref)
        if not destino_list:
            return None, f"No existe la cuenta destino '{cuenta_destino}'"
        destino_id = destino_list[0].id

        if origen_id == destino_id:
            return None, "Origen y destino son la misma cuenta"

        # Actualizar balances (con fee si aplica)
        user_ref.collection("accounts").document(origen_id).update({"balance": firestore.Increment(-(float(monto) + float(fee)))})
        user_ref.collection("accounts").document(destino_id).update({"balance": firestore.Increment(float(monto))})

        # Registrar transacción
        ahora = datetime.now()
        year = str(ahora.year)
        month = f"{ahora.month:02d}"
        fecha = ahora.strftime("%Y-%m-%d")

        tx_ref = user_ref.collection("transactions").document(year).collection(month).collection("items").document()
        tx_ref.set({
            "type": "transfer",                    # Kebo: type en inglés
            "amount": float(monto),                # Kebo: amount en inglés
            "account_id": origen_id,
            "to_account_id": destino_id,
            "description": descripcion or f"Transferencia {cuenta_origen} → {cuenta_destino}",
            "fee": float(fee),                     # Kebo: comisión
            "status": "cleared",                   # Kebo: status
            "tags": [],                            # Kebo: tags
            "date": fecha,                         # Kebo: date en inglés
            "created_at": firestore.SERVER_TIMESTAMP
        })

        return tx_ref.id, f"Transferencia de ${float(monto):,.0f} de {cuenta_origen} → {cuenta_destino} completada"
    except Exception as e:
        return None, f"Error: {e}"


def registrar_split(usuario_id, monto_total, splits, cuenta_nombre="Efectivo", descripcion="",
                   status="cleared", tags=None):
    """Registra un gasto dividido en varias categorías (Kebo split transaction).

    splits: lista de dicts [{categoria: str, monto: float, descripcion: str}, ...]
    El total de los splits debe coincidir con monto_total.

    Estructura en BD:
    - transactions/{year}/{month}/items/{id} con splits=[...]

    También crea transacciones individuales linkeadas por parent_id.
    """
    if tags is None:
        tags = []
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None, "DB no disponible"
    try:
        ensure_user(usuario_id)

        # Buscar cuenta
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        if not cuenta_list:
            return None, f"No existe la cuenta '{cuenta_nombre}'"
        cuenta_id = cuenta_list[0].id

        ahora = datetime.now()
        year = str(ahora.year)
        month = f"{ahora.month:02d}"
        fecha = ahora.strftime("%Y-%m-%d")

        # Crear transacción padre (split)
        parent_ref = user_ref.collection("transactions").document(year).collection(month).collection("items").document()
        parent_ref.set({
            "type": "expense",
            "amount": float(monto_total),
            "account_id": cuenta_id,
            "description": descripcion or "Gasto dividido",
            "status": status,
            "tags": tags + ["split"],
            "date": fecha,
            "is_split": True,
            "splits": [{"category": s["categoria"], "amount": float(s["monto"])} for s in splits],
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # Crear transacciones individuales por categoría
        child_ids = []
        for split in splits:
            cat_id = crear_categoria(usuario_id, split["categoria"])
            child_ref = user_ref.collection("transactions").document(year).collection(month).collection("items").document()
            child_ref.set({
                "type": "expense",
                "amount": float(split["monto"]),
                "account_id": cuenta_id,
                "category_id": cat_id,
                "description": split.get("descripcion", descripcion),
                "parent_id": parent_ref.id,
                "is_split_child": True,
                "status": status,
                "tags": tags,
                "date": fecha,
                "created_at": firestore.SERVER_TIMESTAMP
            })
            child_ids.append(child_ref.id)
            # No actualizamos balance aquí (se hace con el parent)

        # Actualizar balance de la cuenta una sola vez
        actualizar_balance_cuenta(usuario_id, cuenta_id, -float(monto_total))

        return parent_ref.id, f"Gasto dividido en {len(splits)} categorías: ${float(monto_total):,.0f}"
    except Exception as e:
        return None, f"Error: {e}"


# ==================== TRANSACCIONES FUTURAS (KEBO) ====================

def registrar_transaccion_futura(usuario_id, tipo, monto, categoria_nombre, fecha_futura,
                                 descripcion="", cuenta_nombre="Efectivo",
                                 payee="", tags=None, auto_post=True):
    """Registra una transacción programada para una fecha futura.

    Estructura: users/{userId}/scheduled_transactions/{id}
    - Si auto_post=True y la fecha ya pasó, se registra inmediatamente
    - Si no, queda pendiente y se ejecuta cuando llegue la fecha
    """
    if tags is None:
        tags = []
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)

        # Si auto_post y fecha ya pasó, registrar inmediatamente
        fecha_dt = datetime.strptime(fecha_futura, "%Y-%m-%d")
        if auto_post and fecha_dt.date() <= datetime.now().date():
            return registrar_transaccion_v2(
                usuario_id, tipo, monto, categoria_nombre, descripcion, cuenta_nombre,
                payee=payee, tags=tags
            )

        # Buscar o crear categoría
        cat_id = crear_categoria(usuario_id, categoria_nombre)

        # Buscar cuenta
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        if cuenta_list:
            cuenta_id = cuenta_list[0].id
        else:
            cuenta_id = crear_cuenta(usuario_id, cuenta_nombre, "cash")

        # Guardar como transacción programada
        doc_ref = user_ref.collection("scheduled_transactions").document()
        doc_ref.set({
            "type": tipo,
            "amount": float(monto),
            "account_id": cuenta_id,
            "category_id": cat_id,
            "categoria_nombre": categoria_nombre,
            "cuenta_nombre": cuenta_nombre,
            "payee": payee,
            "description": descripcion,
            "scheduled_date": fecha_futura,
            "status": "pending",  # pending, executed, cancelled
            "tags": tags,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error registrando transacción futura: {e}")
        return None


def ejecutar_transacciones_futuras(usuario_id):
    """Ejecuta las transacciones programadas cuya fecha ya llegó.
    Llamar vía cron diariamente.
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    ejecutadas = []
    try:
        hoy = datetime.now().strftime("%Y-%m-%d")
        docs = user_ref.collection("scheduled_transactions").where("status", "==", "pending").stream()
        for d in docs:
            data = d.to_dict()
            fecha = data.get("scheduled_date", "")
            if fecha <= hoy:
                # Ejecutar
                tx_id = registrar_transaccion_v2(
                    usuario_id,
                    data.get("type", "expense"),
                    data.get("amount", 0),
                    data.get("categoria_nombre", "General"),
                    data.get("description", ""),
                    data.get("cuenta_nombre", "Efectivo"),
                    payee=data.get("payee", ""),
                    tags=data.get("tags", [])
                )
                if tx_id:
                    d.reference.update({"status": "executed", "executed_at": firestore.SERVER_TIMESTAMP, "tx_id": tx_id})
                    ejecutadas.append(data.get("description", ""))
        return ejecutadas
    except Exception as e:
        print(f"Error ejecutando futuras: {e}")
        return []


def listar_transacciones_futuras(usuario_id="default", solo_pendientes=True):
    """Lista transacciones programadas (futuras)."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("scheduled_transactions").stream()
        result = []
        for d in docs:
            data = d.to_dict()
            if solo_pendientes and data.get("status") != "pending":
                continue
            data["_id"] = d.id
            result.append(data)
        return sorted(result, key=lambda x: x.get("scheduled_date", ""))
    except Exception:
        return []


# ==================== BÚSQUEDA AVANZADA (KEBO) ====================

def buscar_transacciones(usuario_id, texto="", categoria="", cuenta="", status="",
                       fecha_desde="", fecha_hasta="", tipo="", tags=None,
                       limite=100):
    """Búsqueda avanzada de transacciones con múltiples filtros.

    Filtros:
    - texto: búsqueda en description/payee
    - categoria: nombre de categoría exacto
    - cuenta: nombre de cuenta
    - status: pending | cleared
    - fecha_desde/hasta: rango de fechas (YYYY-MM-DD)
    - tipo: income | expense | transfer
    - tags: lista de tags a filtrar
    """
    if tags is None:
        tags = []
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        # Obtener categorías y cuentas para mapear IDs
        cats = listar_categorias(usuario_id)
        cat_nombres = {c["_id"]: c.get("nombre", "") for c in cats}
        cuentas = listar_cuentas(usuario_id)
        cuenta_nombres = {c["_id"]: c.get("nombre", "") for c in cuentas}

        resultados = []
        ahora = datetime.now()

        # Buscar en últimos 12 meses
        for i in range(12):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            try:
                docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
                for d in docs:
                    t = d.to_dict()
                    t["_id"] = d.id
                    t["_year"] = year
                    t["_month"] = month

                    # Filtro por texto
                    if texto:
                        desc = (t.get("description") or "").lower()
                        payee = (t.get("payee") or "").lower()
                        if texto.lower() not in desc and texto.lower() not in payee:
                            continue

                    # Filtro por categoría
                    if categoria:
                        cat_id = t.get("category_id", "")
                        cat_nombre = cat_nombres.get(cat_id, "")
                        if categoria.lower() not in cat_nombre.lower():
                            continue

                    # Filtro por cuenta
                    if cuenta:
                        acc_id = t.get("account_id", "")
                        acc_nombre = cuenta_nombres.get(acc_id, "")
                        if cuenta.lower() not in acc_nombre.lower():
                            continue

                    # Filtro por status
                    if status and t.get("status", "cleared") != status:
                        continue

                    # Filtro por tipo
                    tipo_val = t.get("type") or t.get("tipo", "expense")
                    if tipo and tipo_val != tipo:
                        continue

                    # Filtro por rango de fechas
                    fecha_tx = t.get("date") or t.get("fecha", "")
                    if fecha_desde and fecha_tx < fecha_desde:
                        continue
                    if fecha_hasta and fecha_tx > fecha_hasta:
                        continue

                    # Filtro por tags
                    if tags:
                        t_tags = t.get("tags", [])
                        if not any(tag in t_tags for tag in tags):
                            continue

                    resultados.append(t)
            except Exception:
                pass

        # Ordenar por fecha descendente
        resultados.sort(key=lambda x: x.get("date") or x.get("fecha", ""), reverse=True)
        return resultados[:limite]
    except Exception as e:
        print(f"Error en búsqueda avanzada: {e}")
        return []


# ==================== SUGERENCIAS DE PAYEE (KEBO) ====================

def obtener_sugerencias_payee(usuario_id, prefijo, limite=10):
    """Obtiene sugerencias de payee basadas en el historial.

    Busca en transactions los payees que coinciden con el prefijo
    y los ordena por frecuencia de uso.
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        # Contar frecuencia de cada payee
        ahora = datetime.now()
        conteo = {}

        for i in range(12):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            try:
                docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
                for d in docs:
                    t = d.to_dict()
                    payee = t.get("payee", "")
                    if payee and prefijo.lower() in payee.lower():
                        conteo[payee] = conteo.get(payee, 0) + 1
            except Exception:
                pass

        # Ordenar por frecuencia
        sugeridos = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
        return [{"payee": p, "frecuencia": f} for p, f in sugeridos[:limite]]
    except Exception:
        return []


def obtener_sugerencias_categoria(usuario_id, prefijo, limite=10):
    """Obtiene sugerencias de categoría basadas en el historial."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        conteo = {}
        ahora = datetime.now()

        for i in range(12):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            try:
                docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
                for d in docs:
                    t = d.to_dict()
                    cat_id = t.get("category_id", "")
                    if not cat_id:
                        continue
                    # Obtener nombre de categoría
                    cats = listar_categorias(usuario_id)
                    cat_nombre = next((c.get("nombre", "") for c in cats if c.get("_id") == cat_id), "")
                    if cat_nombre and prefijo.lower() in cat_nombre.lower():
                        conteo[cat_nombre] = conteo.get(cat_nombre, 0) + 1
            except Exception:
                pass

        sugeridos = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
        return [{"categoria": c, "frecuencia": f} for c, f in sugeridos[:limite]]
    except Exception:
        return []


def listar_transacciones_recientes(usuario_id="default", limite=20):
    """Lista las últimas N transacciones."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        ahora = datetime.now()
        transacciones = []
        for i in range(3):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            try:
                docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
                for d in docs:
                    t = d.to_dict()
                    t["_id"] = d.id
                    t["_year"] = year
                    t["_month"] = month
                    transacciones.append(t)
            except Exception:
                pass
        transacciones.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return transacciones[:limite]
    except Exception as e:
        print(f"Error listando transacciones: {e}")
        return []


# ==================== BALANCE Y PRESUPUESTOS (KEBO) ====================

def aplicar_rollover_presupuesto(usuario_id, year=None, month=None):
    """Aplica rollover de presupuesto del mes anterior al actual.
    Lo que no se gastó se suma al presupuesto del nuevo mes.
    Estructura: budgets/{year}/{month}/items/{id} con campo rollover_from
    """
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
            docs_ant = user_ref.collection("budgets").document(ant_year).document(ant_month).collection("items").stream()
            for d in docs_ant:
                data = d.to_dict()
                cat_id = data.get("category_id")
                cat_nombre = data.get("category_name", "")
                limite_ant = float(data.get("amount", 0))

                # Calcular gastado del mes anterior
                docs_tx = user_ref.collection("transactions").document(ant_year).document(ant_month).collection("items").stream()
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
                    mes_items = user_ref.collection("budgets").document(year).collection(month).collection("items")
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
                            "amount": limite_ant + sobrante,  # original + rollover
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


def obtener_balance_v2(usuario_id="default", mes=None):
    """Obtiene balance del mes actual o especificado.
    Compatible con ambos: campo nuevo (type/amount) y legacy (tipo/monto).
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return 0.0, 0.0, 0.0, []

    if not mes:
        mes = datetime.now().strftime("%Y-%m")
    year, month = mes.split("-")

    try:
        docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
        ingresos = 0.0
        gastos = 0.0
        transacciones = []
        for d in docs:
            t = d.to_dict()
            t["_id"] = d.id
            # Compatibilidad: nuevos campos (amount/type) y legacy (monto/tipo)
            monto = float(t.get("amount") or t.get("monto", 0))
            tipo = t.get("type") or t.get("tipo", "expense")
            transacciones.append(t)
            if tipo == "income":
                ingresos += monto
            elif tipo == "expense":
                gastos += monto
        return ingresos - gastos, ingresos, gastos, transacciones
    except Exception as e:
        print(f"Error obteniendo balance v2: {e}")
        return 0.0, 0.0, 0.0, []

def obtener_presupuestos_v2(usuario_id="default", mes=None):
    """Obtiene presupuestos con gastado del mes (Kebo style).
    Lee de budgets/{year}/{month}/items/ primero, luego fallback a categories.budget.
    """
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
            items_ref = user_ref.collection("budgets").document(year).collection(month).collection("items")
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
        docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
        gastos_por_cat_id = {}
        for d in docs:
            t = d.to_dict()
            # Compatibilidad: type/tipo y amount/monto
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


# ==================== METAS (KEBO) ====================

def guardar_meta_v2(usuario_id, nombre, monto_objetivo, fecha_limite="", cuenta_nombre="Efectivo"):
    """Crea meta en nueva estructura."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        cuenta_id = cuenta_list[0].id if cuenta_list else None

        doc_ref = user_ref.collection("goals").document()
        doc_ref.set({
            "nombre": nombre,
            "monto_objetivo": float(monto_objetivo),
            "current_amount": 0.0,
            "fecha_limite": fecha_limite,
            "account_id": cuenta_id,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error guardando meta v2: {e}")
        return None

def listar_metas_v2(usuario_id="default"):
    """Lista todas las metas."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("goals").stream()
        metas = []
        for d in docs:
            meta = d.to_dict()
            meta["_id"] = d.id
            obj = float(meta.get("monto_objetivo", 0))
            cur = float(meta.get("current_amount", 0))
            meta["porcentaje"] = round((cur / max(obj, 1)) * 100, 1) if obj > 0 else 0
            meta["restante"] = max(0, obj - cur)
            metas.append(meta)
        return metas
    except Exception as e:
        print(f"Error listando metas: {e}")
        return []

def agregar_aporte_meta(usuario_id, meta_nombre, monto):
    """Agrega un aporte a una meta."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False, "DB no disponible"
    try:
        docs = user_ref.collection("goals").where("nombre", "==", meta_nombre).limit(1).stream()
        docs_list = list(docs)
        if not docs_list:
            return False, f"No encontré la meta '{meta_nombre}'"

        meta_ref = docs_list[0].reference
        meta = docs_list[0].to_dict()
        nuevo_current = float(meta.get("current_amount", 0)) + float(monto)
        objetivo = float(meta.get("monto_objetivo", 0))
        completada = nuevo_current >= objetivo

        aporte_ref = meta_ref.collection("aportes").document()
        aporte_ref.set({
            "monto": float(monto),
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "created_at": firestore.SERVER_TIMESTAMP
        })

        meta_ref.update({"current_amount": nuevo_current, "completada": completada})
        pct = round((nuevo_current / max(objetivo, 1)) * 100, 1)
        return True, f"Aporte de ${float(monto):,.0f} registrado. Progreso: {pct}%"
    except Exception as e:
        return False, f"Error: {e}"


# ==================== RECURRENTES (KEBO) ====================

# ==================== RECORDATORIOS POR VOZ (KEBO) ====================

def guardar_recordatorio(usuario_id, texto, dia, month=None, year=None, categoria="", monto=0):
    """Guarda un recordatorio único (no recurrente).

    texto: descripción del recordatorio (ej. "Pagar arriendo")
    dia: día del mes (1-31)
    categoria: categoría asociada (ej. "Arriendo")
    monto: monto asociado si aplica (ej. 1500000)
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        ahora = datetime.now()
        if not year:
            year = str(ahora.year)
        if not month:
            month = f"{ahora.month:02d}"

        # Si el día ya pasó este mes, mover al siguiente
        dia_int = int(dia) if isinstance(dia, str) else dia
        if dia_int < ahora.day:
            # Avanzar al siguiente mes
            proximo = ahora.replace(day=1) + timedelta(days=32)
            year = str(proximo.year)
            month = f"{proximo.month:02d}"

        doc_ref = user_ref.collection("reminders").document()
        doc_ref.set({
            "text": texto,
            "day": dia_int,
            "month": month,
            "year": year,
            "categoria": categoria,
            "monto": float(monto),
            "done": False,
            "notified_at": None,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error guardando recordatorio: {e}")
        return None


def listar_recordatorios(usuario_id, pendientes=True):
    """Lista recordatorios pendientes o todos."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("reminders").stream()
        result = []
        for d in docs:
            data = d.to_dict()
            if pendientes and data.get("done"):
                continue
            data["_id"] = d.id
            result.append(data)
        result.sort(key=lambda x: (int(x.get("year", 0)), int(x.get("month", 0)), int(x.get("day", 1))))
        return result
    except Exception:
        return []


def obtener_recordatorios_hoy(usuario_id):
    """Obtiene los recordatorios que tocan hoy."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        ahora = datetime.now()
        hoy = ahora.day
        mes_actual = f"{ahora.month:02d}"
        year_actual = str(ahora.year)

        docs = user_ref.collection("reminders").where("done", "==", False).stream()
        result = []
        for d in docs:
            data = d.to_dict()
            if data.get("day") == hoy:
                # Coincide con mes actual O es mensual (month="*")
                if data.get("month") in [mes_actual, "*"] and data.get("year") in [year_actual, "*"]:
                    data["_id"] = d.id
                    result.append(data)
        return result
    except Exception:
        return []


def marcar_recordatorio_hecho(usuario_id, reminder_id):
    """Marca un recordatorio como completado."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        user_ref.collection("reminders").document(reminder_id).update({
            "done": True,
            "done_at": firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception:
        return False


def guardar_recurrente(usuario_id, nombre, monto, frecuencia, dia, cuenta_nombre="Efectivo", categoria_nombre="General"):
    """Crea un gasto/ingreso recurrente."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        cuenta_id = cuenta_list[0].id if cuenta_list else None
        cat_id = crear_categoria(usuario_id, categoria_nombre)

        doc_ref = user_ref.collection("recurring").document()
        doc_ref.set({
            "nombre": nombre,
            "monto": float(monto),
            "frecuencia": frecuencia,
            "dia": int(dia),
            "account_id": cuenta_id,
            "category_id": cat_id,
            "activo": True,
            "ultima_ejecucion": None,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error guardando recurrente: {e}")
        return None

def listar_recurrentes(usuario_id="default"):
    """Lista todos los recurrentes activos."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("recurring").where("activo", "==", True).stream()
        return [{**d.to_dict(), "_id": d.id} for d in docs]
    except Exception as e:
        print(f"Error listando recurrentes: {e}")
        return []

def ejecutar_recurrentes(usuario_id="default"):
    """Ejecuta los recurrentes que tocan hoy."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        hoy = datetime.now()
        dia_hoy = hoy.day
        dia_semana = hoy.weekday()

        recurrentes = listar_recurrentes(usuario_id)
        ejecutados = []

        for rec in recurrentes:
            frecuencia = rec.get("frecuencia", "monthly")
            dia_rec = int(rec.get("dia", 1))
            cuenta_id = rec.get("account_id")
            nombre = rec.get("nombre")
            monto = float(rec.get("monto", 0))

            toca = False
            if frecuencia == "monthly" and dia_hoy == dia_rec:
                toca = True
            elif frecuencia == "weekly" and dia_semana == dia_rec:
                toca = True

            if toca and cuenta_id:
                year = str(hoy.year)
                month = f"{hoy.month:02d}"
                fecha = hoy.strftime("%Y-%m-%d")

                tx_ref = user_ref.collection("transactions").document(year).collection(month).collection("items").document()
                tx_ref.set({
                    "type": "expense",                              # Kebo: type en inglés
                    "amount": monto,                                 # Kebo: amount en inglés
                    "account_id": cuenta_id,
                    "description": f"🔁 {nombre} (recurrente)",     # Kebo: description en inglés
                    "status": "cleared",                            # Kebo: status
                    "tags": ["recurrente"],                          # Kebo: tags
                    "date": fecha,                                   # Kebo: date en inglés
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "recurring_id": rec["_id"]
                })

                user_ref.collection("accounts").document(cuenta_id).update({
                    "balance": firestore.Increment(-monto)
                })
                user_ref.collection("recurring").document(rec["_id"]).update({
                    "ultima_ejecucion": firestore.SERVER_TIMESTAMP
                })
                ejecutados.append(nombre)

        return ejecutados
    except Exception as e:
        print(f"Error ejecutando recurrentes: {e}")
        return []


# ==================== ALERTAS (KEBO) ====================

def obtener_alertas_presupuesto(usuario_id="default"):
    """Genera alertas cuando el gasto supera el 80% del presupuesto."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        mes = datetime.now().strftime("%Y-%m")
        year, month = mes.split("-")

        cats = listar_categorias(usuario_id)
        alertas = []

        docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
        gastos_por_cat = {}
        for d in docs:
            t = d.to_dict()
            # Compatibilidad: nuevos campos (type/amount) y legacy (tipo/monto)
            tipo = t.get("type") or t.get("tipo", "expense")
            if tipo == "expense":
                cat_id = t.get("category_id")
                monto = float(t.get("amount") or t.get("monto", 0))
                gastos_por_cat[cat_id] = gastos_por_cat.get(cat_id, 0) + monto

        for cat in cats:
            budget = float(cat.get("budget", 0))
            if budget <= 0:
                continue
            gastado = gastos_por_cat.get(cat["_id"], 0)
            pct = (gastado / budget) * 100

            if pct >= 100:
                alertas.append({
                    "tipo": "excedido",
                    "categoria": cat.get("nombre"),
                    "porcentaje": round(pct, 1),
                    "mensaje": f"🚨 {cat.get('nombre')} EXCEDIDO: ${gastado:,.0f} de ${budget:,.0f}"
                })
            elif pct >= 80:
                alertas.append({
                    "tipo": "alerta",
                    "categoria": cat.get("nombre"),
                    "porcentaje": round(pct, 1),
                    "mensaje": f"⚠️ {cat.get('nombre')} al {pct:.0f}%: ${gastado:,.0f} de ${budget:,.0f}"
                })

        return alertas
    except Exception as e:
        print(f"Error generando alertas: {e}")
        return []


# ==================== ESTADÍSTICAS (KEBO) ====================

def obtener_estadisticas(usuario_id="default", meses=6):
    """Obtiene estadísticas de gastos por categoría y tendencia."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return {}
    try:
        stats = {"por_categoria": {}, "por_mes": {}, "tendencia": []}
        ahora = datetime.now()
        meses_data = {}

        for i in range(meses):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            mes_key = f"{year}-{month}"

            try:
                docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
                ingresos_mes = 0.0
                gastos_mes = 0.0

                for d in docs:
                    t = d.to_dict()
                    # Compatibilidad: nuevos campos (type/amount) y legacy (tipo/monto)
                    monto = float(t.get("amount") or t.get("monto", 0))
                    tipo = t.get("type") or t.get("tipo", "expense")

                    if tipo == "income":
                        ingresos_mes += monto
                    elif tipo == "expense":
                        gastos_mes += monto
                        cat_id = t.get("category_id")
                        if cat_id not in stats["por_categoria"]:
                            stats["por_categoria"][cat_id] = {"total": 0, "nombre": cat_id}
                        stats["por_categoria"][cat_id]["total"] += monto

                meses_data[mes_key] = {"ingresos": ingresos_mes, "gastos": gastos_mes, "balance": ingresos_mes - gastos_mes}
            except Exception:
                pass

        stats["por_mes"] = meses_data
        for mes_key in sorted(meses_data.keys()):
            stats["tendencia"].append({"mes": mes_key, **meses_data[mes_key]})

        cats = listar_categorias(usuario_id)
        cat_nombres = {c["_id"]: c.get("nombre", "Desconocida") for c in cats}
        for cat_id in stats["por_categoria"]:
            if cat_id in cat_nombres:
                stats["por_categoria"][cat_id]["nombre"] = cat_nombres[cat_id]

        return stats
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        return {}


# ==================== EXPORTAR (KEBO) ====================

def exportar_json_completo(usuario_id="default"):
    """Exporta todos los datos del usuario a JSON."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        export = {
            "fecha_export": datetime.now().isoformat(),
            "usuario_id": usuario_id,
            "cuentas": listar_cuentas(usuario_id),
            "categorias": listar_categorias(usuario_id),
            "metas": listar_metas_v2(usuario_id),
            "recurrentes": listar_recurrentes(usuario_id),
            "transacciones": {}
        }

        ahora = datetime.now()
        for i in range(12):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            mes_key = f"{year}-{month}"
            try:
                docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
                export["transacciones"][mes_key] = [{**d.to_dict(), "_id": d.id} for d in docs]
            except Exception:
                pass

        return export
    except Exception as e:
        print(f"Error exportando: {e}")
        return None

def exportar_csv(usuario_id="default", mes=None):
    """Exporta transacciones del mes a CSV."""
    if not mes:
        mes = datetime.now().strftime("%Y-%m")
    year, month = mes.split("-")
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None, "DB no disponible"
    try:
        docs = user_ref.collection("transactions").document(year).collection(month).collection("items").stream()
        lineas = ["Fecha,Tipo,Monto,Descripción"]
        for d in docs:
            t = d.to_dict()
            fecha = t.get("fecha", "")
            tipo = t.get("tipo", "")
            monto = t.get("monto", 0)
            desc = t.get("descripcion", "").replace(",", ";").replace("\n", " ")
            lineas.append(f"{fecha},{tipo},{monto},{desc}")
        return "\n".join(lineas), f"export_{mes}.csv"
    except Exception as e:
        return None, f"Error: {e}"


# ==================== FUNCIONES LEGACY (para compatibilidad) ====================
# Estas funciones usan la estructura ANTIGUA de Firestore (colecciones planas)

def obtener_balance_financiero(usuario_id: str = "default", mes: str = None):
    """Obtener balance financiero de estructura legacy."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return 0.0, 0.0, 0.0, []

    try:
        filter_criteria = FieldFilter("usuario_id", "==", str(usuario_id))
        if mes:
            filter_criteria = FieldFilter("mes", "==", mes)

        docs = db.collection("finanzas").where(filter=filter_criteria).stream()
        ingresos = 0.0
        gastos = 0.0
        transacciones = []
        for doc in docs:
            t = doc.to_dict()
            monto = float(t.get("monto", 0))
            tipo = t.get("tipo", "gasto")
            transacciones.append(t)
            if tipo == "ingreso":
                ingresos += monto
            else:
                gastos += monto
        return ingresos - gastos, ingresos, gastos, transacciones
    except Exception as e:
        print(f"Error obteniendo balance legacy: {e}")
        return 0.0, 0.0, 0.0, []

def obtener_resumen_presupuestos(usuario_id: str = "default", mes: str = None):
    """Obtener presupuestos de estructura legacy."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return {}

    try:
        filter_criteria = FieldFilter("usuario_id", "==", str(usuario_id))
        p_docs = db.collection("presupuestos").where(filter=filter_criteria).stream()
        presupuestos = {}
        for doc in p_docs:
            d = doc.to_dict()
            presupuestos[d.get("categoria")] = float(d.get("limite", 0))
        return presupuestos
    except Exception as e:
        print(f"Error obteniendo presupuestos legacy: {e}")
        return {}

def obtener_tareas_pendientes(usuario_id: str = "default"):
    """Obtener tareas pendientes (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return []
    try:
        docs = db.collection("tareas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).where(filter=FieldFilter("completada", "==", False)).stream()
        tareas = []
        for doc in docs:
            t = doc.to_dict()
            t["id"] = doc.id
            tareas.append(t)
        return tareas
    except Exception as e:
        print(f"Error obteniendo tareas: {e}")
        return []

def guardar_tarea(usuario_id: str, tarea: str, prioridad: str = "Media", fecha_limite: str = "Pronto"):
    """Guardar tarea (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return
    try:
        db.collection("tareas").add({
            "usuario_id": str(usuario_id),
            "tarea": tarea,
            "prioridad": prioridad,
            "fecha_limite": fecha_limite,
            "completada": False,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error guardando tarea: {e}")

def marcar_tarea_completada(usuario_id: str, texto_busqueda: str):
    """Marcar tarea como completada (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return None
    try:
        docs = db.collection("tareas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).where(filter=FieldFilter("completada", "==", False)).stream()
        for doc in docs:
            data = doc.to_dict()
            if texto_busqueda.lower() in data.get("tarea", "").lower():
                doc.reference.update({"completada": True})
                return data.get("tarea")
    except Exception as e:
        print(f"Error completando tarea: {e}")
    return None

def registrar_transaccion(usuario_id: str, tipo: str, monto: float, categoria: str, descripcion: str):
    """Registrar transacción en estructura legacy."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return ""
    try:
        from datetime import datetime
        mes_actual = datetime.now().strftime("%Y-%m")
        db.collection("finanzas").add({
            "usuario_id": str(usuario_id),
            "tipo": tipo.lower(),
            "monto": float(monto),
            "categoria": categoria.capitalize(),
            "descripcion": descripcion,
            "mes": mes_actual,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error registrando transacción legacy: {e}")
    return ""

def establecer_presupuesto(usuario_id: str, categoria: str, limite: float):
    """Establecer presupuesto (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return
    try:
        db.collection("presupuestos").document(f"{usuario_id}_{categoria.lower()}").set({
            "usuario_id": str(usuario_id),
            "categoria": categoria.capitalize(),
            "limite": float(limite)
        })
    except Exception as e:
        print(f"Error estableciendo presupuesto: {e}")

def modificar_presupuesto(usuario_id: str, categoria: str, nuevo_limite: float):
    """Modificar presupuesto (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return False
    try:
        doc_id = f"{usuario_id}_{categoria.lower()}"
        db.collection("presupuestos").document(doc_id).set({
            "usuario_id": str(usuario_id),
            "categoria": categoria.capitalize(),
            "limite": float(nuevo_limite),
            "actualizado": firestore.SERVER_TIMESTAMP
        }, merge=True)
        return True
    except Exception as e:
        print(f"Error modificando presupuesto: {e}")
        return False

def limpiar_y_cargar_datos_dinamicos(usuario_id: str, presupuestos: dict, transacciones: list):
    """Reestructurar base de datos (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return "Error de conexión a Firebase"
    try:
        for col_name in ["finanzas", "presupuestos", "tareas"]:
            docs = db.collection(col_name).stream()
            for doc in docs:
                doc.reference.delete()
        for cat, limite in presupuestos.items():
            db.collection("presupuestos").document(f"{usuario_id}_{cat.lower()}").set({
                "usuario_id": str(usuario_id),
                "categoria": cat.capitalize(),
                "limite": float(limite)
            })
        for t in transacciones:
            db.collection("finanzas").add({
                "usuario_id": str(usuario_id),
                "tipo": t.get("tipo", "gasto").lower(),
                "monto": float(t.get("monto", 0)),
                "categoria": t.get("categoria", "General").capitalize(),
                "descripcion": t.get("descripcion", "Movimiento registrado"),
                "timestamp": firestore.SERVER_TIMESTAMP
            })
        return f"✅ Base de datos reestructurada con éxito. {len(presupuestos)} presupuestos y {len(transacciones)} transacciones cargadas."
    except Exception as e:
        return f"❌ Error reestructurando base de datos: {e}"

def obtener_contexto_financiero(usuario_id: str = "default") -> str:
    """Contexto ultra-compacto para el AI."""
    balance_neto, ingresos, gastos, transacciones = obtener_balance_financiero(usuario_id)
    presupuestos = obtener_resumen_presupuestos(usuario_id)
    tareas = obtener_tareas_pendientes(usuario_id)
    pres_str = str(presupuestos) if presupuestos else "{}"
    ultimas = []
    for t in transacciones[-3:]:
        ultimas.append(f"{t.get('tipo','?')[:1].upper()}:{t.get('monto',0):,.0f}@{t.get('categoria','?')[:4]}")
    tareas_str = f"{len(tareas)} tareas" if tareas else "sin tareas"
    return f"[JARVIS] Balance=${balance_neto:,.0f} Ing=${ingresos:,.0f} Gas=${gastos:,.0f} | Pres:{pres_str} | Mov:{ultimas} | {tareas_str}"

def guardar_mensaje(usuario_id: str, remitente: str, mensaje: str):
    """Guardar mensaje en historial (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return
    try:
        db.collection("historial_chat").add({
            "usuario_id": str(usuario_id),
            "remitente": remitente,
            "mensaje": mensaje,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error guardando mensaje: {e}")

def guardar_meta(usuario_id: str, nombre: str, monto_objetivo: float, fecha_limite: str = "", categoria: str = "General"):
    """Guardar meta (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return
    try:
        db.collection("metas").document(f"{usuario_id}_{nombre.lower().replace(' ', '_')[:30]}").set({
            "usuario_id": str(usuario_id),
            "nombre": nombre.title(),
            "monto_objetivo": float(monto_objetivo),
            "monto_actual": 0.0,
            "fecha_limite": fecha_limite,
            "categoria": categoria.capitalize(),
            "completada": False,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error guardando meta: {e}")

def obtener_metas(usuario_id: str = "default"):
    """Obtener metas (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return []
    try:
        docs = db.collection("metas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        metas = []
        for doc in docs:
            m = doc.to_dict()
            m["id"] = doc.id
            metas.append(m)
        return metas
    except Exception as e:
        print(f"Error obteniendo metas: {e}")
        return []

def actualizar_progreso_meta(usuario_id: str, nombre: str, monto_actual: float):
    """Actualizar progreso meta (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return False
    try:
        doc_id = f"{usuario_id}_{nombre.lower().replace(' ', '_')[:30]}"
        doc_ref = db.collection("metas").document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            nuevo_monto = float(data.get("monto_actual", 0)) + float(monto_actual)
            completada = nuevo_monto >= float(data.get("monto_objetivo", 0))
            doc_ref.update({"monto_actual": nuevo_monto, "completada": completada})
            return True
    except Exception as e:
        print(f"Error actualizando meta: {e}")
    return False

def eliminar_meta(usuario_id: str, nombre: str):
    """Eliminar meta (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return False
    try:
        nombre_norm = nombre.lower().strip()
        docs = db.collection("metas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        for doc in docs:
            data = doc.to_dict()
            if nombre_norm in data.get("nombre", "").lower():
                doc.reference.delete()
                return True
    except Exception as e:
        print(f"Error eliminando meta: {e}")
    return False

def proyectar_meta(meta: dict, capacidad_ahorro_mensual: float) -> dict:
    """Calcular proyección de meta."""
    from datetime import datetime
    objetivo = float(meta.get("monto_objetivo", 0))
    actual = float(meta.get("monto_actual", 0))
    falta = max(0, objetivo - actual)
    meses_restantes = 12
    fecha_limite_str = meta.get("fecha_limite", "")
    if fecha_limite_str:
        try:
            fecha_limite = datetime.strptime(fecha_limite_str, "%Y-%m-%d")
            hoy = datetime.now()
            meses_restantes = max(1, (fecha_limite - hoy).days // 30)
        except (ValueError, TypeError):
            meses_restantes = 12
    ahorro_necesario = falta / meses_restantes if meses_restantes > 0 else falta
    meses_proyectados = falta / capacidad_ahorro_mensual if capacidad_ahorro_mensual > 0 else float('inf')
    atrasado = meses_proyectados > meses_restantes
    return {
        "objetivo": objetivo, "actual": actual, "falta": falta,
        "porcentaje": min(100, (actual / objetivo * 100)) if objetivo > 0 else 0,
        "meses_restantes": meses_restantes, "ahorro_necesario": ahorro_necesario,
        "ahorro_capacidad": capacidad_ahorro_mensual,
        "meses_proyectados": meses_proyectados, "atrasado": atrasado
    }

def guardar_pago_fijo(usuario_id: str, nombre: str, monto: float, dia_mes: int, categoria: str = "General"):
    """Guardar pago fijo (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return
    try:
        doc_id = f"{usuario_id}_{nombre.lower().replace(' ', '_')[:30]}"
        db.collection("pagos_fijos").document(doc_id).set({
            "usuario_id": str(usuario_id),
            "nombre": nombre.title(),
            "monto": float(monto),
            "dia_mes": int(dia_mes),
            "categoria": categoria.capitalize(),
            "activo": True,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error guardando pago fijo: {e}")

def obtener_pagos_fijos(usuario_id: str = "default"):
    """Obtener pagos fijos (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return []
    try:
        docs = db.collection("pagos_fijos").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        pagos = []
        for doc in docs:
            p = doc.to_dict()
            p["id"] = doc.id
            pagos.append(p)
        return pagos
    except Exception as e:
        print(f"Error obteniendo pagos fijos: {e}")
        return []

def eliminar_pago_fijo(usuario_id: str, nombre: str):
    """Eliminar pago fijo (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return False
    try:
        nombre_norm = nombre.lower().strip()
        docs = db.collection("pagos_fijos").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        for doc in docs:
            data = doc.to_dict()
            if nombre_norm in data.get("nombre", "").lower():
                doc.reference.delete()
                return True
    except Exception as e:
        print(f"Error eliminando pago fijo: {e}")
    return False

def guardar_perfil(usuario_id: str, **datos):
    """Guardar perfil (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return
    try:
        db.collection("perfiles").document(str(usuario_id)).set(datos, merge=True)
    except Exception as e:
        print(f"Error guardando perfil: {e}")

def obtener_perfil(usuario_id: str = "default") -> dict:
    """Obtener perfil (legacy)."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return {}
    try:
        doc = db.collection("perfiles").document(str(usuario_id)).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        print(f"Error obteniendo perfil: {e}")
    return {}


# ==================== PRÉSTAMOS (KEBO) ====================

def registrar_prestamo(usuario_id, persona, monto, fecha=None, nota=""):
    """Registra un préstamo (dinero que diste y esperas recuperar).

    Los préstamos NO se cuentan como gasto del mes: son un activo
    (por cobrar). El balance los considera hasta que se pagan.

    Args:
        usuario_id: ID del usuario
        persona: A quién le prestaste (ej: "Juan Pérez")
        monto: Cuánto le prestaste
        fecha: Fecha del préstamo (YYYY-MM-DD). Default: hoy
        nota: Nota opcional (motivo, plazo, etc.)

    Returns:
        ID del préstamo creado, o None si falla
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        if not fecha:
            fecha = datetime.now().strftime("%Y-%m-%d")
        doc_ref = user_ref.collection("loans").document()
        doc_ref.set({
            "persona": persona,
            "monto_original": float(monto),
            "monto_pagado": 0.0,
            "monto_pendiente": float(monto),
            "fecha": fecha,
            "nota": nota,
            "status": "pendiente",   # pendiente | pagado | parcial
            "pagos": [],             # lista de {monto, fecha}
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error registrando préstamo: {e}")
        return None


def registrar_pago_prestamo(usuario_id, prestamo_id, monto_pago, fecha=None):
    """Registra un pago (parcial o total) de un préstamo.

    Si el pago completa el monto pendiente, marca el préstamo como 'pagado'.

    Returns:
        dict con info del préstamo actualizado, o None si falla
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        if not fecha:
            fecha = datetime.now().strftime("%Y-%m-%d")
        prestamo_ref = user_ref.collection("loans").document(prestamo_id)
        doc = prestamo_ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        nuevo_pagado = float(data.get("monto_pagado", 0)) + float(monto_pago)
        pendiente_original = float(data.get("monto_original", 0))
        nuevo_pendiente = max(0.0, pendiente_original - nuevo_pagado)
        nuevo_status = "pagado" if nuevo_pendiente <= 0.01 else "parcial"

        pagos = list(data.get("pagos", []))
        pagos.append({"monto": float(monto_pago), "fecha": fecha})

        prestamo_ref.update({
            "monto_pagado": nuevo_pagado,
            "monto_pendiente": nuevo_pendiente,
            "status": nuevo_status,
            "pagos": pagos,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        return {
            "id": prestamo_id,
            "monto_pagado": nuevo_pagado,
            "monto_pendiente": nuevo_pendiente,
            "status": nuevo_status,
        }
    except Exception as e:
        print(f"Error registrando pago: {e}")
        return None


def listar_prestamos(usuario_id="default", solo_pendientes=False):
    """Lista préstamos. Por defecto todos; con solo_pendientes=True, solo los no pagados.

    Returns:
        Lista de dicts con info del préstamo + campo '_id'
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("loans").stream()
        result = []
        for d in docs:
            data = d.to_dict()
            if solo_pendientes and data.get("status") == "pagado":
                continue
            data["_id"] = d.id
            result.append(data)
        # Más recientes primero
        result.sort(key=lambda x: x.get("fecha", ""), reverse=True)
        return result
    except Exception as e:
        print(f"Error listando préstamos: {e}")
        return []


def obtener_total_por_cobrar(usuario_id="default"):
    """Suma de todo lo pendiente por cobrar.

    Returns:
        float con el total pendiente
    """
    prestamos = listar_prestamos(usuario_id, solo_pendientes=True)
    total = sum(float(p.get("monto_pendiente", 0)) for p in prestamos)
    return total


def eliminar_prestamo(usuario_id, prestamo_id):
    """Elimina un préstamo (y su historial de pagos)."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        user_ref.collection("loans").document(prestamo_id).delete()
        return True
    except Exception as e:
        print(f"Error eliminando préstamo: {e}")
        return False

