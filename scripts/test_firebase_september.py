import sys
import os
from datetime import datetime

# Forzar UTF-8 en la salida estándar
sys.stdout.reconfigure(encoding="utf-8")

# Asegurar que el directorio base del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from modules.firestore.client import inicializar_firebase, USUARIO_PRINCIPAL

def get_september_data():
    db = inicializar_firebase()

    try:
        # Obtener referencia al usuario principal
        user_ref = db.collection('users').document(USUARIO_PRINCIPAL)
        
        # Obtener todas las subcolecciones de transactions (formato YYYY-MM)
        transactions_parent_ref = user_ref.collection('transactions')
        
        print("=== Verificando subcolecciones de transactions ===")
        subcollections = transactions_parent_ref.list_documents()
        
        all_transactions = []
        for doc_snapshot in subcollections:
            period = doc_snapshot.id  # YYYY-MM
            print(f"\nPeriodo encontrado: {period}")
            
            # Obtener items dentro de cada periodo
            items_ref = doc_snapshot.collection('items')
            items = items_ref.stream()
            
            for item_doc in items:
                data = item_doc.to_dict()
                data['_period'] = period
                data['_id'] = item_doc.id
                all_transactions.append(data)
        
        # Filtrar solo Septiembre 2026
        september_transactions = [t for t in all_transactions if t.get('_period') == '2026-09']
        
        print(f"\n=== Total de transacciones en todos los periodos: {len(all_transactions)} ===")
        print(f"=== Transacciones en Septiembre 2026: {len(september_transactions)} ===")
        
        if september_transactions:
            print("\n=== Datos de Septiembre 2026 ===")
            for t in september_transactions:
                print(f"  - {t.get('description', 'Sin descripción')}: ${t.get('amount', 0)} ({t.get('type', 'N/A')})")
        
        return {
            'all_periods': all_transactions,
            'september': september_transactions
        }

    except Exception as e:
        print("Error al obtener datos de Firebase:", e)
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    get_september_data()