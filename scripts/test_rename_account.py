"""Script de prueba para listar cuentas, crear/seleccionar una y renombrarla."""
import sys
import os

# Asegurar que el path incluya el directorio raíz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configurar la salida estándar para UTF-8 en Windows
sys.stdout.reconfigure(encoding='utf-8')

from modules.firestore.client import inicializar_firebase, USUARIO_PRINCIPAL, _get_user_ref
from modules.finance.accounts import listar_cuentas, crear_cuenta

def renombrar_cuenta(usuario_id, cuenta_id, nuevo_nombre):
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        print("Error: No se pudo obtener la referencia del usuario.")
        return False
    try:
        user_ref.collection("accounts").document(cuenta_id).update({
            "nombre": nuevo_nombre
        })
        print(f"Cuenta {cuenta_id} renombrada exitosamente a '{nuevo_nombre}'.")
        return True
    except Exception as e:
        print(f"Error al renombrar cuenta: {e}")
        return False

if __name__ == "__main__":
    print("Inicializando Firebase...")
    inicializar_firebase()
    
    usuario_id = USUARIO_PRINCIPAL
    print(f"Usando usuario principal: {usuario_id}")
    
    print("\n1. Listando cuentas existentes:")
    cuentas = listar_cuentas(usuario_id)
    for c in cuentas:
        print(f" - ID: {c['_id']}, Nombre: {c['nombre']}, Balance: {c['balance']}")
        
    cuenta_id_objetivo = None
    if not cuentas:
        print("\nNo hay cuentas. Creando una cuenta de prueba...")
        nueva_id = crear_cuenta(usuario_id, nombre="Cuenta Original Test", balance=1000)
        print(f"Creada cuenta con ID: {nueva_id}")
        cuenta_id_objetivo = nueva_id
    else:
        cuenta_id_objetivo = cuentas[0]["_id"]
        
    print(f"\n2. Renombrando la cuenta ID: {cuenta_id_objetivo}...")
    nuevo_nombre_test = "Cuenta Renombrada Test"
    renombrar_cuenta(usuario_id, cuenta_id_objetivo, nuevo_nombre_test)
    
    print("\n3. Verificando el cambio listando nuevamente:")
    cuentas_post = listar_cuentas(usuario_id)
    encontrada = False
    for c in cuentas_post:
        if c["_id"] == cuenta_id_objetivo:
            encontrada = True
            print(f" Verificación exitosa -> ID: {c['_id']}, Nombre actual: {c['nombre']}")
    
    if not encontrada:
        print("Advertencia: No se encontró la cuenta objetivo en la verificación.")
