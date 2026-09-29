"""
Script de migración recursiva y aplanamiento de Firestore para JARVIS.
Mueve todas las subcolecciones de users/1536228767180136498 a la raíz de Firestore,
cuenta y verifica la migración, y realiza el borrado seguro solo si coincide 100%.
"""
import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore

OLD_USER_ID = "1536228767180136498"

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

def contar_recursivo(ref):
    """Cuenta documentos en una referencia (colección o documento con subcolecciones)."""
    count = 0
    if hasattr(ref, "collections"):
        # Es un DocumentReference
        for subcoll in ref.collections():
            count += contar_recursivo(subcoll)
    elif hasattr(ref, "stream"):
        # Es un CollectionReference
        for doc in ref.stream():
            count += 1
            for subcoll in doc.reference.collections():
                count += contar_recursivo(subcoll)
    return count

def migrar_recursivo(source_ref, dest_ref):
    """Copia documentos de forma recursiva de source_ref a dest_ref."""
    migrados = 0
    for doc in source_ref.stream():
        data = doc.to_dict()
        dest_doc_ref = dest_ref.document(doc.id)
        dest_doc_ref.set(data, merge=True)
        migrados += 1
        
        # Procesar subcolecciones del documento
        for subcoll in doc.reference.collections():
            dest_subcoll_ref = dest_doc_ref.collection(subcoll.id)
            migrados += migrar_recursivo(subcoll, dest_subcoll_ref)
    return migrados

def borrar_recursivo(ref):
    """Elimina documentos y subcolecciones recursivamente."""
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
    user_ref = db.collection("users").document(OLD_USER_ID)
    user_doc = user_ref.get()

    if not user_doc.exists:
        print(f"El usuario {OLD_USER_ID} no existe o ya fue aplanado.")
        return

    print("=== INICIANDO MIGRACIÓN RECURSIVA A RAÍZ ===")
    
    # 1. Contar documentos en origen
    total_origen = contar_recursivo(user_ref)
    print(f"Total de documentos en origen (users/{OLD_USER_ID}): {total_origen}")

    # 2. Migrar cada colección de nivel superior a la raíz
    total_migrados = 0
    for subcoll in user_ref.collections():
        coll_name = subcoll.id
        print(f"Migrando colección raíz '{coll_name}'...")
        dest_coll_ref = db.collection(coll_name)
        total_migrados += migrar_recursivo(subcoll, dest_coll_ref)

    # Migrar config si existe
    user_data = user_doc.to_dict() or {}
    if "config" in user_data:
        db.collection("config").document("app_settings").set(user_data["config"], merge=True)
        print("Configuración global migrada a /config/app_settings")

    # 3. Contar documentos en destino
    # Contamos las colecciones de primer nivel que tenía el usuario
    total_destino = 0
    for subcoll in user_ref.collections():
        dest_coll_ref = db.collection(subcoll.id)
        total_destino += contar_recursivo(dest_coll_ref)
    
    print(f"Total de documentos migrados a destino: {total_destino}")

    # 4. Verificación y borrado seguro
    if total_origen == total_destino:
        print("✅ ¡Verificación exitosa! Los conteos coinciden al 100%.")
        print("Realizando borrado seguro de la ruta antigua...")
        borrar_recursivo(user_ref)
        print("✅ Colección /users eliminada con éxito.")
    else:
        print(f"❌ ADVERTENCIA: Discrepancia en conteos (Origen: {total_origen}, Destino: {total_destino}). No se borrará el origen.")

if __name__ == "__main__":
    main()
