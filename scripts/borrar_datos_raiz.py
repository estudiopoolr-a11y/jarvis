import sys
import os

# Asegurar path y encoding UTF-8
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.firestore.client import inicializar_firebase

def borrar_datos_raiz():
    db = inicializar_firebase()
    if not db:
        print("Error: No se pudo conectar a Firestore.")
        return

    colecciones = ["categories", "budgets", "loans"]
    for col in colecciones:
        print(f"Borrando colección raíz /{col}...")
        docs = db.collection(col).stream()
        for doc in docs:
            # Borrar subcolecciones
            for subcoll in doc.reference.collections():
                for subdoc in subcoll.stream():
                    subdoc.reference.delete()
            doc.reference.delete()
        print(f"Colección /{col} borrada.")

if __name__ == "__main__":
    borrar_datos_raiz()
