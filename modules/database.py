import os
import json
import firebase_admin
from firebase_admin import credentials, initialize_app, firestore

db = None

def inicializar_firebase():
    """Inicializa Firebase Firestore soportando variables de entorno o archivo local."""
    global db
    if not firebase_admin._apps:
        firebase_json_str = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if firebase_json_str:
            try:
                cred_dict = json.loads(firebase_json_str)
                cred = credentials.Certificate(cred_dict)
                initialize_app(cred)
            except Exception as e:
                print(f"Error cargando credenciales de variable de entorno: {e}")
        else:
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                initialize_app(cred)
            else:
                print("⚠️ Advertencia: No se encontró archivo de credenciales de Firebase ni variable de entorno.")
    
    if firebase_admin._apps:
        db = firestore.client()
    return db

def obtener_balance_financiero(usuario_id: str = "default"):
    global db
    if not db: db = inicializar_firebase()
    if not db: return 0.0, 0.0, 0.0, []

    try:
        docs = db.collection("finanzas").where("usuario_id", "==", str(usuario_id)).stream()
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
        p_docs = db.collection("presupuestos").where("usuario_id", "==", str(usuario_id)).stream()
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
        docs = db.collection("tareas").where("usuario_id", "==", str(usuario_id)).where("completada", "==", False).stream()
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
        docs = db.collection("tareas").where("usuario_id", "==", str(usuario_id)).where("completada", "==", False).stream()
        for doc in docs:
            data = doc.to_dict()
            if texto_busqueda.lower() in data.get("tarea", "").lower():
                doc.reference.update({"completada": True})
                return data.get("tarea")
    except Exception as e:
        print(f"Error completando tarea: {e}")
    return None

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
        
        # Verificar presupuestos si es gasto
        if tipo.lower() == "gasto":
            presupuestos = obtener_resumen_presupuestos(usuario_id)
            limite = presupuestos.get(categoria.capitalize(), 0)
            if limite > 0:
                _, _, total_gastado_cat, _ = obtener_balance_financiero(usuario_id)
                # Alerta si supera el 80% o el 100%
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
    """Limpia la base de datos y carga masivamente los presupuestos y transacciones indicados por prompt."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return "Error de conexión a Firebase"

    try:
        # 1. Borrar colecciones antiguas
        for col_name in ["finanzas", "presupuestos", "tareas"]:
            docs = db.collection(col_name).stream()
            for doc in docs:
                doc.reference.delete()

        # 2. Cargar Presupuestos
        for cat, limite in presupuestos.items():
            db.collection("presupuestos").document(f"{usuario_id}_{cat.lower()}").set({
                "usuario_id": str(usuario_id),
                "categoria": cat.capitalize(),
                "limite": float(limite)
            })

        # 3. Cargar Transacciones
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