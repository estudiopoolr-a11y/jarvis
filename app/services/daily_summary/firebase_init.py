"""app/services/daily_summary/firebase_init.py - Inicialización de Firebase para el resumen diario."""
import os
import firebase_admin
from firebase_admin import credentials, initialize_app, firestore

db = None

def inicializar_firebase():
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
            firebase_json_str = firebase_json_str.strip()
            if (firebase_json_str.startswith("'") and firebase_json_str.endswith("'")) or \
               (firebase_json_str.startswith('"') and firebase_json_str.endswith('"')):
                firebase_json_str = firebase_json_str[1:-1].strip()
            with open(cred_path, "w", encoding="utf-8") as f:
                f.write(firebase_json_str)
            cred = credentials.Certificate(cred_path)
            initialize_app(cred)

        if not firebase_admin._apps and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            initialize_app(cred)

    if firebase_admin._apps:
        db = firestore.client()
    return db

def get_db():
    global db
    if not db:
        db = inicializar_firebase()
    return db
