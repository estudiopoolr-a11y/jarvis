import os
import json
import firebase_admin
from firebase_admin import credentials, initialize_app, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

db = None

def inicializar_firebase():
    """Inicializa Firebase Firestore soportando variables de entorno, creación automática de archivo temporal o archivo local."""
    global db
    if not firebase_admin._apps:
        # Buscar en múltiples nombres posibles de variables de entorno en Render (incluyendo FIREBASE_CREDENTIALS)
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
                
                # Escribir el JSON de la variable de entorno directamente al archivo de credenciales
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

def obtener_balance_financiero(usuario_id: str = "default"):
    global db
    if not db: db = inicializar_firebase()
    if not db: return 0.0, 0.0, 0.0, []

    try:
        docs = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
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
        balance_neto = ingresos - gastos
        return balance_neto, ingresos, gastos, transacciones
    except Exception as e:
        print(f"Error obteniendo balance: {e}")
        return 0.0, 0.0, 0.0, []

def obtener_resumen_presupuestos(usuario_id: str = "default"):
    global db
    if not db: db = inicializar_firebase()
    if not db: return {}

    try:
        p_docs = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        presupuestos = {}
        for doc in p_docs:
            d = doc.to_dict()
            presupuestos[d.get("categoria")] = float(d.get("limite", 0))
        return presupuestos
    except Exception as e:
        print(f"Error obteniendo presupuestos: {e}")
        return {}

def obtener_tareas_pendientes(usuario_id: str = "default"):
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

def limpiar_datos_usuario(usuario_id: str):
    """Elimina todas las transacciones, presupuestos y tareas de un usuario."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return {"transacciones": 0, "presupuestos": 0, "tareas": 0}

    resultado = {"transacciones": 0, "presupuestos": 0, "tareas": 0}

    try:
        # Eliminar transacciones
        docs = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        for doc in docs:
            doc.reference.delete()
            resultado["transacciones"] += 1

        # Eliminar presupuestos
        docs = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        for doc in docs:
            doc.reference.delete()
            resultado["presupuestos"] += 1

        # Eliminar tareas
        docs = db.collection("tareas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        for doc in docs:
            doc.reference.delete()
            resultado["tareas"] += 1

    except Exception as e:
        print(f"Error limpiando datos: {e}")

    return resultado

def registrar_transaccion(usuario_id: str, tipo: str, monto: float, categoria: str, descripcion: str):
    global db
    if not db: db = inicializar_firebase()
    if not db: return ""
    try:
        db.collection("finanzas").add({
            "usuario_id": str(usuario_id),
            "tipo": tipo.lower(),
            "monto": float(monto),
            "categoria": categoria.capitalize(),
            "descripcion": descripcion,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        
        if tipo.lower() == "gasto":
            presupuestos = obtener_resumen_presupuestos(usuario_id)
            limite = presupuestos.get(categoria.capitalize(), 0)
            if limite > 0:
                _, _, total_gastado_cat, _ = obtener_balance_financiero(usuario_id)
                if total_gastado_cat >= limite:
                    return f" 🚨 ¡ALERTA CRÍTICA! Has superado el presupuesto para '{categoria}' (${limite:,.0f}). ¡Deja de gastar!"
    except Exception as e:
        print(f"Error registrando transacción: {e}")
    return ""

def establecer_presupuesto(usuario_id: str, categoria: str, limite: float):
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

def limpiar_y_cargar_datos_dinamicos(usuario_id: str, presupuestos: dict, transacciones: list):
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
    """OPTIMIZADO: Contexto ultra-compacto para reducir tokens."""
    balance_neto, ingresos, gastos, transacciones = obtener_balance_financiero(usuario_id)
    presupuestos = obtener_resumen_presupuestos(usuario_id)
    tareas = obtener_tareas_pendientes(usuario_id)

    # Compactar presupuestos solo si existen
    pres_str = str(presupuestos) if presupuestos else "{}"

    # Compactar últimas 3 transacciones (reducido de 5 a 3)
    ultimas = []
    for t in transacciones[-3:]:
        ultimas.append(f"{t.get('tipo','?')[:1].upper()}:{t.get('monto',0):,.0f}@{t.get('categoria','?')[:4]}")

    # Compactar tareas solo si hay pendientes
    tareas_str = f"{len(tareas)} tareas" if tareas else "sin tareas"

    return f"""[JARVIS] Balance=${balance_neto:,.0f} Ing=${ingresos:,.0f} Gas=${gastos:,.0f} | Pres:{pres_str} | Mov:{ultimas} | {tareas_str}"""

def guardar_mensaje(usuario_id: str, remitente: str, mensaje: str):
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


# ============== METAS FINANCIERAS ==============

def guardar_meta(usuario_id: str, nombre: str, monto_objetivo: float, fecha_limite: str = "", categoria: str = "General"):
    """Crea una nueva meta financiera."""
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
    """Obtiene todas las metas del usuario."""
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
    """Actualiza el progreso de una meta."""
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
    """Elimina una meta por nombre."""
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
    """Calcula proyección de una meta."""
    from datetime import datetime
    objetivo = float(meta.get("monto_objetivo", 0))
    actual = float(meta.get("monto_actual", 0))
    falta = max(0, objetivo - actual)

    # Calcular meses hasta fecha límite
    meses_restantes = 12  # default
    fecha_limite_str = meta.get("fecha_limite", "")
    if fecha_limite_str:
        try:
            fecha_limite = datetime.strptime(fecha_limite_str, "%Y-%m-%d")
            hoy = datetime.now()
            meses_restantes = max(1, (fecha_limite - hoy).days // 30)
        except (ValueError, TypeError):
            meses_restantes = 12

    # Ahorro mensual necesario
    ahorro_necesario = falta / meses_restantes if meses_restantes > 0 else falta

    # Tiempo proyectado según capacidad actual
    if capacidad_ahorro_mensual > 0:
        meses_proyectados = falta / capacidad_ahorro_mensual
    else:
        meses_proyectados = float('inf')

    # ¿Va atrasado?
    atrasado = meses_proyectados > meses_restantes

    return {
        "objetivo": objetivo,
        "actual": actual,
        "falta": falta,
        "porcentaje": min(100, (actual / objetivo * 100)) if objetivo > 0 else 0,
        "meses_restantes": meses_restantes,
        "ahorro_necesario": ahorro_necesario,
        "ahorro_capacidad": capacidad_ahorro_mensual,
        "meses_proyectados": meses_proyectados,
        "atrasado": atrasado
    }


# ============== MODIFICAR PRESUPUESTOS ==============

def modificar_presupuesto(usuario_id: str, categoria: str, nuevo_limite: float):
    """Modifica o crea un presupuesto."""
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


# ============== PAGOS FIJOS MENSUALES ==============

def guardar_pago_fijo(usuario_id: str, nombre: str, monto: float, dia_mes: int, categoria: str = "General"):
    """Guarda un pago fijo mensual."""
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
    """Obtiene todos los pagos fijos del usuario."""
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
    """Elimina un pago fijo por nombre."""
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


def obtener_pagos_del_dia(usuario_id: str, dia: int):
    """Obtiene pagos fijos que vencen un día específico."""
    pagos = obtener_pagos_fijos(usuario_id)
    return [p for p in pagos if p.get("dia_mes") == dia and p.get("activo")]


# ============== PERFIL DE USUARIO ==============

def guardar_perfil(usuario_id: str, **datos):
    """Guarda o actualiza datos del perfil del usuario."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return
    try:
        db.collection("perfiles").document(str(usuario_id)).set(datos, merge=True)
    except Exception as e:
        print(f"Error guardando perfil: {e}")


def obtener_perfil(usuario_id: str = "default") -> dict:
    """Obtiene el perfil del usuario."""
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