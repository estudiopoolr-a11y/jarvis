#!/usr/bin/env python3
"""
Script para poblar la colección raíz `accounts` con las tres cuentas iniciales:
- Nu (tipo: bank)
- Nequi (tipo: wallet) 
- Efectivo (tipo: cash)
"""

import sys
import os

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.firestore.client import inicializar_firebase
from modules.finance.accounts import crear_cuenta

def main():
    print("Inicializando Firebase...")
    inicializar_firebase()
    
    print("Creando cuentas iniciales en la colección raíz 'accounts'...")
    
    # Crear cuenta Nu (bank)
    nu_id = crear_cuenta(
        usuario_id="default",
        nombre="Nu",
        tipo="bank",
        balance=0.0,
        icono="💳",
        color="#7C4DFF",  # Morado
        institution="NuBank",
        bank_last4="0000"
    )
    if nu_id:
        print(f"[OK] Cuenta Nu creada con ID: {nu_id}")
    else:
        print("[ERROR] Error al crear cuenta Nu")
        return False
    
    # Crear cuenta Nequi (wallet)
    nequi_id = crear_cuenta(
        usuario_id="default",
        nombre="Nequi",
        tipo="wallet",
        balance=0.0,
        icono="💰",
        color="#00C853",  # Verde
        institution="Nequi",
        bank_last4="1111"
    )
    if nequi_id:
        print(f"[OK] Cuenta Nequi creada con ID: {nequi_id}")
    else:
        print("[ERROR] Error al crear cuenta Nequi")
        return False
    
    # Crear cuenta Efectivo (cash)
    efectivo_id = crear_cuenta(
        usuario_id="default",
        nombre="Efectivo",
        tipo="cash",
        balance=0.0,
        icono="💵",
        color="#FF6B00",  # Naranja
        institution="",
        bank_last4=""
    )
    if efectivo_id:
        print(f"[OK] Cuenta Efectivo creada con ID: {efectivo_id}")
    else:
        print("[ERROR] Error al crear cuenta Efectivo")
        return False
        
    print("\n[SUCCESS] Todas las cuentas han sido creadas exitosamente!")
    print(f"   - Nu (bank): {nu_id}")
    print(f"   - Nequi (wallet): {nequi_id}")
    print(f"   - Efectivo (cash): {efectivo_id}")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)