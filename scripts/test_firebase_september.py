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
        
        # Listar todos los periodos encontrados
        print(f"\n=== Total de transacciones en todos los periodos: {len(all_transactions)} ===")
        
        # Agrupar por periodo
        from collections import defaultdict
        by_period = defaultdict(list)
        for t in all_transactions:
            by_period[t.get('_period')].append(t)
            
        for period, trans in by_period.items():
            print(f"\nPeriodo: {period}, Transacciones: {len(trans)}")
            for t in trans[:5]: # Mostrar primeras 5
                print(f"  - {t.get('description', 'Sin descripción')}: ${t.get('amount', 0)} ({t.get('type', 'N/A')})")
        
        return {
            'all_periods': all_transactions,
            'by_period': dict(by_period)
        }

    except Exception as e:
        print("Error al obtener datos de Firebase:", e)
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    get_september_data()