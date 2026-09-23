"""Firebase client shared by all domain modules."""
import json
import os
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore, initialize_app

db = None
USUARIO_PRINCIPAL = "1536228767180136498"


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
                print("Firebase inicializado con éxito creando archivo de credenciales desde la variable de entorno de Render.")
            except Exception as e:
                print(f"Error crítico procesando credenciales desde la variable de entorno: {e}")
                try:
                    cred_dict = json.loads(firebase_json_str)
                    cred = credentials.Certificate(cred_dict)
                    initialize_app(cred)
                    print("Firebase inicializado con éxito desde diccionario JSON directo.")
                except Exception as e2:
                    print(f"Error secundario al inicializar con diccionario: {e2}")

        if not firebase_admin._apps:
            if os.path.exists(cred_path):
                try:
                    cred = credentials.Certificate(cred_path)
                    initialize_app(cred)
                    print(f"Firebase inicializado desde archivo local '{cred_path}'.")
                except Exception as e:
                    print(f"Error cargando archivo local '{cred_path}': {e}")
            else:
                print("ADVERTENCIA CRÍTICA: No se encontró la variable de entorno FIREBASE_CREDENTIALS ni el archivo de credenciales en Render.")

    if firebase_admin._apps:
        db = firestore.client()
    return db


def get_db():
    """Always reads the live client (avoids stale imported bindings)."""
    global db
    if not db:
        inicializar_firebase()
    return db


def _get_user_ref(usuario_id="default"):
    """Obtiene referencia al documento del usuario (estructura Kebo)."""
    database = get_db()
    if not database:
        return None, None
    if not usuario_id or str(usuario_id) in ("default", "iphone_user", "None", ""):
        usuario_id = USUARIO_PRINCIPAL
    return database, database.collection("users").document(str(usuario_id))


def serialize_data(data):
    if isinstance(data, datetime):
        return data.isoformat()
    raise TypeError(f"Type {type(data)} not serializable")
