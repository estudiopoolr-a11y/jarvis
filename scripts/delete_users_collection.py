"""
Elimina recursivamente toda la colección /users y sus subcolecciones en Firestore.
ADVERTENCIA: Esta operación es irreversible. Úsalo solo si ya migraste todos los datos.
"""
import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore

def inicializar():
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
    if not firebase_admin._apps:
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            print("Error: No se encontró serviceAccountKey.json")
            sys.exit(1)
    return firestore.client()

def borrar_recursivo(ref):
    if hasattr(ref, "collections"):
        for subcoll in ref.collections():
            borrar_recursivo(subcoll)
        ref.delete()
    elif hasattr(ref, "stream"):
        for doc in ref.stream():
            for subcoll in doc.reference.collections():
                borrar_recursivo(subcoll)
            doc.reference.delete()

def main():
    db = inicializar()
    users_ref = db.collection("users")
    print("Eliminando todos los documentos y subcolecciones de /users ...")
    borrar_recursivo(users_ref)
    print("Colección /users eliminada por completo.")

if __name__ == "__main__":
    main()
