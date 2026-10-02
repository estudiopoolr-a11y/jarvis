#!/usr/bin/env python3
"""
Script para verificar si existe una cuenta llamada 'cuenta_principal' en la colección raíz 'accounts'.
"""

import sys
import os

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.firestore.client import inicializar_firebase, get_db
from modules.finance.accounts import listar_cuentas

def main():
    print("Inicializando Firebase...")
    inicializar_firebase()
    
    print("Listando todas las cuentas en la colección raíz 'accounts'...")
    cuentas = listar_cuentas(usuario_id="default")
    
    if not cuentas:
        print("No se encontraron cuentas.")
        return False
    
    print(f"Se encontraron {len(cuentas)} cuentas:")
    found = False
    for cuenta in cuentas:
        print(f"  - ID: {cuenta['_id']}, Nombre: {cuenta['nombre']}, Tipo: {cuenta['type']}")
        if cuenta['nombre'].lower() == 'cuenta_principal':
            print(f"    [!] Se encontró una cuenta con nombre 'cuenta_principal'!")
            found = True
    
    if not found:
        print("\n[OK] No se encontró ninguna cuenta llamada 'cuenta_principal'.")
        return True
    else:
        print("\n[ADVERTENCIA] Se encontró al menos una cuenta llamada 'cuenta_principal'.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)