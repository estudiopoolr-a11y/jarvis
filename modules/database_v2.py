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
from datetime import datetime, timedelta
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

        # Buscar cuenta por nombre para guardar su ID
        cuenta_id = None
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        if cuenta_list:
            cuenta_id = cuenta_list[0].id

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
    """Lista todas las metas del usuario."""
    db, user_ref = _get_user_ref(usuario_id)
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
    """Agrega un aporte a una meta existente."""
    db, user_ref = _get_user_ref(usuario_id)
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

        # Registrar aporte en subcol
        aporte_ref = meta_ref.collection("aportes").document()
        aporte_ref.set({
            "monto": float(monto),
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # Actualizar current_amount
        meta_ref.update({
            "current_amount": nuevo_current,
            "completada": completada
        })

        pct = round((nuevo_current / max(objetivo, 1)) * 100, 1)
        return True, f"Aporte de ${float(monto):,.0f} registrado. Progreso: {pct}% (${nuevo_current:,.0f} / ${objetivo:,.0f})"
    except Exception as e:
        return False, f"Error: {e}"

# ==================== TRANSFERENCIAS ====================

def registrar_transferencia(usuario_id, cuenta_origen, cuenta_destino, monto, descripcion=""):
    """Registra transferencia entre dos cuentas (restar de origen, sumar a destino)."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None, "DB no disponible"
    try:
        ensure_user(usuario_id)

        # Buscar cuenta origen
        origen_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_origen).limit(1).stream()
        origen_list = list(origen_ref)
        if not origen_list:
            return None, f"No existe la cuenta origen '{cuenta_origen}'"
        origen_id = origen_list[0].id

        # Buscar cuenta destino
        destino_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_destino).limit(1).stream()
        destino_list = list(destino_ref)
        if not destino_list:
            return None, f"No existe la cuenta destino '{cuenta_destino}'"
        destino_id = destino_list[0].id

        if origen_id == destino_id:
            return None, "Origen y destino son la misma cuenta"

        # Actualizar balances
        user_ref.collection("accounts").document(origen_id).update({
            "balance": firestore.Increment(-float(monto))
        })
        user_ref.collection("accounts").document(destino_id).update({
            "balance": firestore.Increment(float(monto))
        })

        # Registrar como transacción tipo "transfer"
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

# ==================== RECURRENTES ====================

def guardar_recurrente(usuario_id, nombre, monto, frecuencia, dia, cuenta_nombre="Efectivo", categoria_nombre="General"):
    """Crea un gasto/ingreso recurrente."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)

        # Buscar cuenta y categoría
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        cuenta_id = cuenta_list[0].id if cuenta_list else None

        cat_id = crear_categoria(usuario_id, categoria_nombre)

        doc_ref = user_ref.collection("recurring").document()
        doc_ref.set({
            "nombre": nombre,
            "monto": float(monto),
            "frecuencia": frecuencia,  # "monthly", "biweekly", "weekly"
            "dia": int(dia),  # día del mes (1-31) o de la semana
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
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("recurring").where("activo", "==", True).stream()
        return [{**d.to_dict(), "_id": d.id} for d in docs]
    except Exception as e:
        print(f"Error listando recurrentes: {e}")
        return []

def ejecutar_recurrentes(usuario_id="default"):
    """Ejecuta los recurrentes que tocan hoy (para usar en cron diario)."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        hoy = datetime.now()
        dia_hoy = hoy.day
        dia_semana = hoy.weekday()  # 0=lunes, 6=domingo

        recurrentes = listar_recurrentes(usuario_id)
        ejecutados = []

        for rec in recurrentes:
            frecuencia = rec.get("frecuencia", "monthly")
            dia_rec = int(rec.get("dia", 1))
            cuenta_id = rec.get("account_id")
            cat_id = rec.get("category_id")
            nombre = rec.get("nombre")
            monto = float(rec.get("monto", 0))
            ultima = rec.get("ultima_ejecucion")

            # Verificar si toca hoy
            toca = False
            if frecuencia == "monthly" and dia_hoy == dia_rec:
                toca = True
            elif frecuencia == "biweekly":
                # Cada 14 días desde ultima_ejecucion
                if not ultima:
                    toca = dia_hoy == dia_rec
                else:
                    pass  # Lógica compleja, simplificar
            elif frecuencia == "weekly" and dia_semana == dia_rec:
                toca = True

            if toca and cuenta_id:
                # Registrar transacción
                year = str(hoy.year)
                month = f"{hoy.month:02d}"
                fecha = hoy.strftime("%Y-%m-%d")

                tx_ref = user_ref.collection("transactions").document(year).document(month).collection("items").document()
                tx_ref.set({
                    "tipo": "expense",
                    "monto": monto,
                    "account_id": cuenta_id,
                    "category_id": cat_id,
                    "descripcion": f"🔁 {nombre} (recurrente)",
                    "fecha": fecha,
                    "tags": ["recurrente"],
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "recurring_id": rec["_id"]
                })

                # Restar del balance
                user_ref.collection("accounts").document(cuenta_id).update({
                    "balance": firestore.Increment(-monto)
                })

                # Marcar como ejecutado
                user_ref.collection("recurring").document(rec["_id"]).update({
                    "ultima_ejecucion": firestore.SERVER_TIMESTAMP
                })

                ejecutados.append(nombre)

        return ejecutados
    except Exception as e:
        print(f"Error ejecutando recurrentes: {e}")
        return []

# ==================== ALERTAS ====================

def obtener_alertas_presupuesto(usuario_id="default"):
    """Genera alertas cuando el gasto de una categoría supera el 80% del presupuesto."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        mes = datetime.now().strftime("%Y-%m")
        year, month = mes.split("-")

        # Obtener categorías con budget
        cats = listar_categorias(usuario_id)
        alertas = []

        # Obtener gastos del mes por categoría
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

# ==================== CATEGORÍAS PREDEFINIDAS ====================

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

def crear_categorias_predefinidas(usuario_id="default"):
    """Crea todas las categorías predefinidas para un usuario."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return 0
    try:
        ensure_user(usuario_id)
        count = 0
        for cat in CATEGORIAS_PREDEFINIDAS:
            # Verificar si ya existe
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

# ==================== ESTADÍSTICAS ====================

def obtener_estadisticas(usuario_id="default", meses=6):
    """Obtiene estadísticas de gastos por categoría y tendencia."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return {}
    try:
        stats = {
            "por_categoria": {},
            "por_mes": {},
            "tendencia": []
        }

        ahora = datetime.now()
        meses_data = {}

        # Obtener transacciones de los últimos N meses
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
                        # Por categoría
                        cat_id = t.get("category_id")
                        if cat_id not in stats["por_categoria"]:
                            stats["por_categoria"][cat_id] = {"total": 0, "nombre": cat_id}
                        stats["por_categoria"][cat_id]["total"] += monto

                meses_data[mes_key] = {
                    "ingresos": ingresos_mes,
                    "gastos": gastos_mes,
                    "balance": ingresos_mes - gastos_mes
                }
            except Exception:
                pass

        stats["por_mes"] = meses_data

        # Tendencia mensual (últimos 6 meses)
        for mes_key in sorted(meses_data.keys()):
            stats["tendencia"].append({
                "mes": mes_key,
                **meses_data[mes_key]
            })

        # Obtener nombres de categorías
        cats = listar_categorias(usuario_id)
        cat_nombres = {c["_id"]: c.get("nombre", "Desconocida") for c in cats}

        for cat_id in stats["por_categoria"]:
            if cat_id in cat_nombres:
                stats["por_categoria"][cat_id]["nombre"] = cat_nombres[cat_id]

        return stats
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        return {}

# ==================== EXPORTAR ====================

def exportar_csv(usuario_id="default", mes=None):
    """Exporta transacciones del mes a CSV."""
    if not mes:
        mes = datetime.now().strftime("%Y-%m")

    year, month = mes.split("-")
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None, "DB no disponible"

    try:
        docs = user_ref.collection("transactions").document(year).document(month).collection("items").stream()
        lineas = ["Fecha,Tipo,Monto,Categoría,Descripción"]

        cats = listar_cuentas(usuario_id)  # Reuse para algo?

        for d in docs:
            t = d.to_dict()
            fecha = t.get("fecha", "")
            tipo = t.get("tipo", "")
            monto = t.get("monto", 0)
            desc = t.get("descripcion", "").replace(",", ";").replace("\n", " ")
            linea = f"{fecha},{tipo},{monto},,{desc}"
            lineas.append(linea)

        csv = "\n".join(lineas)
        return csv, f"export_{mes}.csv"
    except Exception as e:
        return None, f"Error: {e}"

def exportar_json_completo(usuario_id="default"):
    """Exporta todos los datos del usuario a JSON."""
    db, user_ref = _get_user_ref(usuario_id)
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

        # Exportar transacciones por mes
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

# ==================== NOTAS Y ADJUNTOS ====================

def agregar_nota_transaccion(usuario_id, tx_id, mes, nota):
    """Agrega una nota a una transacción existente."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        year, month = mes.split("-")
        tx_ref = user_ref.collection("transactions").document(year).document(month).collection("items").document(tx_id)
        tx_ref.update({"notas": nota})
        return True
    except Exception as e:
        print(f"Error agregando nota: {e}")
        return False

def listar_transacciones_recientes(usuario_id="default", limite=20):
    """Lista las últimas N transacciones del usuario."""
    db, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        ahora = datetime.now()
        transacciones = []

        # Buscar en los últimos 3 meses
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

        # Ordenar por created_at desc
        transacciones.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return transacciones[:limite]
    except Exception as e:
        print(f"Error listando transacciones recientes: {e}")
        return []
