import sys
import os
from datetime import datetime

# Forzar UTF-8 en la salida estándar
sys.stdout.reconfigure(encoding="utf-8")

# Asegurar que el directorio base del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from modules.firestore.client import inicializar_firebase, USUARIO_PRINCIPAL

def seed_september_mock():
    db = inicializar_firebase()

    try:
        user_ref = db.collection('users').document(USUARIO_PRINCIPAL)
        transactions_ref = user_ref.collection('transactions').document('2026-09').collection('items')

        # Datos mock para Septiembre 2026
        mock_data = [
            {
                'description': 'Sueldo mensual',
                'amount': 5000000,
                'type': 'ingreso',
                'category': 'Ingresos',
                'subcategory': 'Salario',
                'date': '2026-09-01',
                'created_at': datetime.utcnow().isoformat()
            },
            {
                'description': 'Arriendo apartamento',
                'amount': 1200000,
                'type': 'gasto',
                'category': 'Vivienda',
                'subcategory': 'Arriendo',
                'date': '2026-09-05',
                'created_at': datetime.utcnow().isoformat()
            },
            {
                'description': 'Mercado semana 1',
                'amount': 350000,
                'type': 'gasto',
                'category': 'Alimentación',
                'subcategory': 'Supermercado',
                'date': '2026-09-10',
                'created_at': datetime.utcnow().isoformat()
            }
        ]

        print("=== Inyectando datos mock para Septiembre 2026 ===")
        for i, data in enumerate(mock_data, 1):
            doc_ref = transactions_ref.add(data)
            print(f"  {i}. {data['description']}: ${data['amount']} ({data['type']})")

        print(f"\n✅ {len(mock_data)} transacciones mock inyectadas exitosamente.")
        return True

    except Exception as e:
        print("Error al inyectar datos mock:", e)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    seed_september_mock()