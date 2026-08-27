import os
import glob
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# --- INICIALIZACIÓN FLEXIBLE DE FIREBASE ---
if not firebase_admin._apps:
    cred = None
    firebase_env = os.getenv("FIREBASE_CREDENTIALS")

    # 1. Intentar cargar desde variable de entorno (JSON directo o ruta)
    if firebase_env:
        try:
            firebase_env_str = firebase_env.strip()
            if firebase_env_str.startswith("{"):
                # Es un string JSON (Render / Producción)
                cred_dict = json.loads(firebase_env_str)
                cred = credentials.Certificate(cred_dict)
            elif os.path.exists(firebase_env_str):
                # Es una ruta de archivo existente
                cred = credentials.Certificate(firebase_env_str)
        except Exception as e:
            print(f"⚠️ Error parseando FIREBASE_CREDENTIALS de entorno: {e}")

    # 2. Si no hay variable de entorno válida, buscar archivos .json en el entorno local
    if not cred:
        cred_path = None
        json_files = glob.glob("jarvis*.json") + glob.glob("*.json")
        for f in json_files:
            if "firebase" in f.lower() or "adminsdk" in f.lower():
                cred_path = f
                break
        
        if not cred_path and os.path.exists("jarvis-be47a-firebase-adminsdk.json"):
            cred_path = "jarvis-be47a-firebase-adminsdk.json"

        if cred_path and os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
            except Exception as e:
                print(f"⚠️ Error cargando archivo de credenciales local: {e}")

    # 3. Inicializar app en Firebase
    if cred:
        try:
            firebase_admin.initialize_app(cred)
            print("✅ Firebase inicializado correctamente.")
        except Exception as e:
            print(f"⚠️ Error al inicializar Firebase App: {e}")
    else:
        print("❌ Error: No se encontraron credenciales válidas de Firebase.")

db = firestore.client() if firebase_admin._apps else None


def guardar_mensaje(usuario: str, usuario_id: str, mensaje: str, respuesta: str, tiene_audio: bool = False):
    if not db: return
    try:
        db.collection("historial_chat").document().set({
            "usuario": usuario, "usuario_id": str(usuario_id),
            "mensaje": mensaje, "respuesta_ia": respuesta,
            "tiene_audio": tiene_audio, "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error al guardar mensaje: {e}")

# --- GESTIÓN DE TAREAS AVANZADA ---
def guardar_tarea(usuario_id: str, tarea: str, prioridad: str = "Media", fecha_limite: str = "Pronto"):
    if not db: return
    try:
        db.collection("tareas").add({
            "usuario_id": str(usuario_id),
            "tarea": tarea,
            "prioridad": prioridad.capitalize(),
            "fecha_limite": fecha_limite,
            "completada": False,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error al guardar tarea: {e}")

def obtener_tareas_pendientes(usuario_id: str):
    if not db: return []
    docs = db.collection("tareas").where("usuario_id", "==", str(usuario_id)).where("completada", "==", False).stream()
    tareas = []
    for doc in docs:
        data = doc.to_dict()
        tareas.append({
            "id": doc.id,
            "tarea": data.get("tarea"),
            "prioridad": data.get("prioridad", "Media"),
            "fecha_limite": data.get("fecha_limite", "Pronto")
        })
    return tareas

def marcar_tarea_completada(usuario_id: str, texto_parcial: str):
    if not db: return False
    docs = db.collection("tareas").where("usuario_id", "==", str(usuario_id)).where("completada", "==", False).stream()
    for doc in docs:
        data = doc.to_dict()
        if texto_parcial.lower() in data.get("tarea", "").lower():
            doc.reference.update({"completada": True})
            return data.get("tarea")
    return None

# --- GESTIÓN FINANCIERA Y PRESUPUESTOS ---
def establecer_presupuesto(usuario_id: str, categoria: str, limite: float):
    if not db: return
    db.collection("presupuestos").document(f"{usuario_id}_{categoria.lower()}").set({
        "usuario_id": str(usuario_id),
        "categoria": categoria.capitalize(),
        "limite": float(limite)
    })

def registrar_transaccion(usuario_id: str, tipo: str, monto: float, categoria: str, descripcion: str):
    """tipo: 'gasto' o 'ingreso'"""
    if not db: return ""
    db.collection("finanzas").add({
        "usuario_id": str(usuario_id),
        "tipo": tipo.lower(),
        "monto": float(monto),
        "categoria": categoria.capitalize(),
        "descripcion": descripcion,
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    
    alerta_presupuesto = ""
    if tipo.lower() == "gasto":
        docs = db.collection("finanzas").where("usuario_id", "==", str(usuario_id)).where("tipo", "==", "gasto").where("categoria", "==", categoria.capitalize()).stream()
        total_cat = sum([d.to_dict().get("monto", 0) for d in docs])
        
        presup_doc = db.collection("presupuestos").document(f"{usuario_id}_{categoria.lower()}").get()
        if presup_doc.exists:
            limite = presup_doc.to_dict().get("limite", 0)
            if total_cat > limite:
                alerta_presupuesto = f"\n⚠️ **¡ALERTA DE PRESUPUESTO!** Has superado el límite de ${limite:,.0f} en *{categoria}* (Gastado: ${total_cat:,.0f})."

    return alerta_presupuesto

def obtener_balance_financiero(usuario_id: str):
    if not db: return 0, 0, 0, []
    docs = db.collection("finanzas").where("usuario_id", "==", str(usuario_id)).stream()
    total_ingresos = 0
    total_gastos = 0
    movimientos = []
    
    for doc in docs:
        data = doc.to_dict()
        monto = data.get("monto", 0)
        tipo = data.get("tipo", "gasto")
        cat = data.get("categoria", "General")
        desc = data.get("descripcion", "")
        
        if tipo == "ingreso":
            total_ingresos += monto
            movimientos.append(f"🟢 +${monto:,.0f} [{cat}]: {desc}")
        else:
            total_gastos += monto
            movimientos.append(f"🔴 -${monto:,.0f} [{cat}]: {desc}")
            
    balance_neto = total_ingresos - total_gastos
    return balance_neto, total_ingresos, total_gastos, movimientos