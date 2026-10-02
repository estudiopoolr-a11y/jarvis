#!/usr/bin/env python3
"""
Script para probar el endpoint /api/widget/dashboard
"""
import sys
import os

# Añadir el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from fastapi.testclient import TestClient

def test_widget_endpoint():
    """Probar el endpoint del widget"""
    client = TestClient(app)
    
    # Probar sin usuario_id (debe usar default)
    response = client.get("/api/widget/dashboard")
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Probar con usuario_id específico
    response = client.get("/api/widget/dashboard?usuario_id=test_user")
    print(f"\nStatus code with user_id: {response.status_code}")
    print(f"Response with user_id: {response.json()}")
    
    # Verificar que la respuesta tenga la estructura esperada
    data = response.json()
    if "error" not in data:
        required_fields = ["total_balance_cuentas", "cuentas", "mes", "total_ingresos", "total_gastos", "presupuestos"]
        for field in required_fields:
            if field not in data:
                print(f"ERROR: Campo requerido '{field}' no encontrado en la respuesta")
                return False
        
        # Verificar que cuentas sea una lista
        if not isinstance(data["cuentas"], list):
            print("ERROR: 'cuentas' no es una lista")
            return False
            
        # Verificar que cada cuenta tenga nombre y disponible
        for cuenta in data["cuentas"]:
            if "nombre" not in cuenta or "disponible" not in cuenta:
                print("ERROR: Cuenta missing 'nombre' or 'disponible'")
                return False
                
        print("\n✅ Todas las verificaciones pasaron!")
        return True
    else:
        print(f"ERROR en la respuesta: {data['error']}")
        return False

if __name__ == "__main__":
    success = test_widget_endpoint()
    sys.exit(0 if success else 1)