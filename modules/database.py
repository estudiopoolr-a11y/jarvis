"""
database.py - JARVIS Database Module
====================================

Este archivo maneja TODA la interacción con Firestore:
- Estructura nueva (Kebo): users/{userId}/accounts, categories, transactions, goals, recurring
- Funciones legacy: tareas, perfil, pagos_fijos (para compatibilidad)

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
    """Lista todas las cuentas del usuario."""
    _, user_ref = _get_user_ref(usuario_id)
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
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        doc_ref = user_ref.collection("accounts").document()
        doc_ref.set({
            "nombre": nombre,
            "tipo": tipo,
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

def actualizar_presupuesto_categoria(usuario_id, nombre, nuevo_budget):
    """Actualiza el presupuesto de una categoría por nombre."""
    _, user_ref = _get_user_ref(usuario_id)
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


# ==================== TRANSACCIONES (KEBO) ====================

def registrar_transaccion_v2(usuario_id, tipo, monto, categoria_nombre, descripcion="", cuenta_nombre="Efectivo"):
    """Registra transacción en nueva estructura Kebo."""
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

        tx_ref = user_ref.collection("transactions").document(year).document(month).collection("items").document()
        tx_ref.set({
            "tipo": tipo,
            "monto": float(monto),
            "account_id": cuenta_id,
            "category_id": cat_id,
            "descripcion": descripcion,
            "fecha": fecha,
            "tags": [],
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # Actualizar balance
        if tipo == "expense":
            actualizar_balance_cuenta(usuario_id, cuenta_id, -float(monto))
        else:
            actualizar_balance_cuenta(usuario_id, cuenta_id, float(monto))

        return tx_ref.id
    except Exception as e:
        print(f"Error registrando transacción v2: {e}")
        return None

def registrar_transferencia(usuario_id, cuenta_origen, cuenta_destino, monto, descripcion=""):
    """Registra transferencia entre dos cuentas."""
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

        # Actualizar balances
        user_ref.collection("accounts").document(origen_id).update({"balance": firestore.Increment(-float(monto))})
        user_ref.collection("accounts").document(destino_id).update({"balance": firestore.Increment(float(monto))})

        # Registrar transacción
        ahora = datetime.now()
        year = str(ahora.year)
        month = f"{ahora.month:02d}"
        fecha = ahora.strftime("%Y-%m-%d")

        tx_ref = user_ref.collection("transactions").document(year).document(month).collection("items").document()
        tx_ref.set({
            "tipo": "transfer",
            "monto": float(monto),
            "account_id": origen_id,
            "to_account_id": destino_id,
            "descripcion": descripcion or f"Transferencia {cuenta_origen} → {cuenta_destino}",
            "fecha": fecha,
            "tags": [],
            "created_at": firestore.SERVER_TIMESTAMP
        })

        return tx_ref.id, f"Transferencia de ${float(monto):,.0f} de {cuenta_origen} → {cuenta_destino} completada"
    except Exception as e:
        return None, f"Error: {e}"

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
                docs = user_ref.collection("transactions").document(year).document(month).collection("items").stream()
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

def obtener_balance_v2(usuario_id="default", mes=None):
    """Obtiene balance del mes actual o especificado."""
    _, user_ref = _get_user_ref(usuario_id)
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
            elif tipo == "expense":
                gastos += monto
        return ingresos - gastos, ingresos, gastos, transacciones
    except Exception as e:
        print(f"Error obteniendo balance v2: {e}")
        return 0.0, 0.0, 0.0, []

def obtener_presupuestos_v2(usuario_id="default", mes=None):
    """Obtiene presupuestos con gastado del mes."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return {}

    if not mes:
        mes = datetime.now().strftime("%Y-%m")
    year, month = mes.split("-")

    try:
        cats = listar_categorias(usuario_id)
        presupuestos = {}

        docs = user_ref.collection("transactions").document(year).document(month).collection("items").stream()
        gastos_por_cat = {}
        for d in docs:
            t = d.to_dict()
            if t.get("tipo") == "expense":
                cat_id = t.get("category_id")
                monto = float(t.get("monto", 0))
                gastos_por_cat[cat_id] = gastos_por_cat.get(cat_id, 0) + monto

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

                tx_ref = user_ref.collection("transactions").document(year).document(month).collection("items").document()
                tx_ref.set({
                    "tipo": "expense",
                    "monto": monto,
                    "account_id": cuenta_id,
                    "descripcion": f"🔁 {nombre} (recurrente)",
                    "fecha": fecha,
                    "tags": ["recurrente"],
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

        docs = user_ref.collection("transactions").document(year).document(month).collection("items").stream()
        gastos_por_cat = {}
        for d in docs:
            t = d.to_dict()
            if t.get("tipo") == "expense":
                cat_id = t.get("category_id")
                monto = float(t.get("monto", 0))
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
                docs = user_ref.collection("transactions").document(year).document(month).collection("items").stream()
                ingresos_mes = 0.0
                gastos_mes = 0.0

                for d in docs:
                    t = d.to_dict()
                    monto = float(t.get("monto", 0))
                    tipo = t.get("tipo", "expense")

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
                docs = user_ref.collection("transactions").document(year).document(month).collection("items").stream()
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
        docs = user_ref.collection("transactions").document(year).document(month).collection("items").stream()
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
