import sys
import os

# Forzar UTF-8 en la salida estándar
sys.stdout.reconfigure(encoding="utf-8")

# Asegurar que el directorio base del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))

from modules.firestore.client import inicializar_firebase, USUARIO_PRINCIPAL

def check_accounts():
    db = inicializar_firebase()
    try:
        user_ref = db.collection('users').document(USUARIO_PRINCIPAL)
        accounts_ref = user_ref.collection('accounts')
        
        print("=== Verificando colecciones de accounts ===")
        accounts = accounts_ref.stream()
        
        for acc in accounts:
            data = acc.to_dict()
            print(f"  - Cuenta: {data.get('nombre')}, Balance: {data.get('balance')}")
        
    except Exception as e:
        print("Error al obtener cuentas:", e)

if __name__ == "__main__":
    check_accounts()
