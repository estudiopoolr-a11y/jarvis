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
    balance_neto, ingresos, gastos, transacciones = obtener_balance_financiero(usuario_id)
    presupuestos = obtener_resumen_presupuestos(usuario_id)
    tareas = obtener_tareas_pendientes(usuario_id)
    
    return f"""
    [ESTADO ACTUAL DE LA BASE DE DATOS DE FIREBASE PARA EL USUARIO {usuario_id}]
    - Ingresos totales: ${ingresos:,.2f}
    - Gastos totales: ${gastos:,.2f}
    - Balance neto: ${balance_neto:,.2f}
    - Presupuestos establecidos por categoría: {json.dumps(presupuestos, ensure_ascii=False)}
    - Transacciones recientes: {json.dumps(transacciones[-10:], ensure_ascii=False)}
    - Tareas pendientes: {json.dumps(tareas, ensure_ascii=False)}
    """

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