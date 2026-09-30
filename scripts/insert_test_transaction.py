import sys
import os
from datetime import datetime

# Forzar UTF-8 en la salida estándar
sys.stdout.reconfigure(encoding="utf-8")

# Asegurar que el directorio base del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))

from modules.firestore.client import inicializar_firebase, USUARIO_PRINCIPAL

def insert_test_transaction():
    db = inicializar_firebase()
    try:
        user_ref = db.collection('users').document(USUARIO_PRINCIPAL)
        # Buscar cuenta válida
        accounts_ref = user_ref.collection('accounts')
        accounts = list(accounts_ref.stream())
        if not accounts:
            print('No hay cuentas registradas.')
            return
        acc_doc = accounts[0]
        acc_data = acc_doc.to_dict()
        account_id = acc_doc.id
        account_name = acc_data.get('nombre', 'SinNombre')
        print(f"Usando cuenta: {account_name} (ID: {account_id})")

        # Buscar categoría Alimentación
        categories_ref = user_ref.collection('categories')
        cat_id = None
        for cat_doc in categories_ref.stream():
            cat_data = cat_doc.to_dict()
            if cat_data.get('nombre', '').lower() == 'alimentación':
                cat_id = cat_doc.id
                break
        if not cat_id:
            print('No se encontró la categoría Alimentación.')
            return
        print(f"Usando categoría Alimentación (ID: {cat_id})")

        # Insertar transacción
        period = '2026-09'
        tx_ref = user_ref.collection('transactions').document(period).collection('items')
        tx_data = {
            'amount': 150000,
            'category_id': cat_id,
            'category_name': 'Alimentación',
            'account_id': account_id,
            'type': 'expense',
            'description': 'Compra de alimentos',
            'date': datetime(2026, 9, 15).isoformat(),
        }
        tx_ref.add(tx_data)
        print('Transacción de prueba insertada correctamente.')
    except Exception as e:
        print('Error al insertar transacción:', e)

if __name__ == "__main__":
    insert_test_transaction()
