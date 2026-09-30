import sys
import os
from datetime import datetime

# Forzar UTF-8 en la salida estándar
sys.stdout.reconfigure(encoding="utf-8")

# Asegurar que el directorio base del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from modules.firestore.client import inicializar_firebase, USUARIO_PRINCIPAL

def check_budgets():
    db = inicializar_firebase()
    try:
        user_ref = db.collection('users').document(USUARIO_PRINCIPAL)
        budgets_ref = user_ref.collection('budgets')
        
        print("=== Verificando colecciones de budgets ===")
        subcollections = budgets_ref.list_documents()
        
        for doc_snapshot in subcollections:
            period = doc_snapshot.id  # YYYY-MM
            print(f"\nPeriodo encontrado: {period}")
            
            if period == '2026-09':
                items_ref = doc_snapshot.collection('items')
                items = items_ref.stream()
                
                for item_doc in items:
                    data = item_doc.to_dict()
                    print(f"  - Categoría: {data.get('category_name')}, Límite: {data.get('amount')}")
        
    except Exception as e:
        print("Error al obtener presupuestos:", e)

if __name__ == "__main__":
    check_budgets()
