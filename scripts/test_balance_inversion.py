#!/usr/bin/env python3
"""
Script de prueba para validar las herramientas de balance consolidado y recomendaciones de inversión.
"""

import sys
import os
from unittest.mock import patch, MagicMock

# Añadir el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_obtener_balance_consolidado():
    """Prueba la función _obtener_balance_consolidado con datos simulados."""
    print("[TEST] Probando _obtener_balance_consolidado...")
    
    # Mock de la función listar_cuentas para devolver datos de ejemplo
    mock_cuentas = [
        {"nombre": "Nu", "type": "cash", "balance": 1500000},
        {"nombre": "Nequi", "type": "cash", "balance": 800000},
        {"nombre": "Efectivo", "type": "cash", "balance": 200000},
        {"nombre": "Ahorros", "type": "savings", "balance": 500000}  # Esta no debería contar
    ]
    
    with patch('modules.finance.accounts.listar_cuentas', return_value=mock_cuentas):
        from src.agent.tools import _obtener_balance_consolidado
        
        resultado = _obtener_balance_consolidado("test_user")
        print(f"[RESULT] Resultado: {resultado}")
        
        # Verificaciones
        assert "Balance consolidado" in resultado
        assert "$2,500,000 COP" in resultado  # 1.5M + 0.8M + 0.2M
        assert "Nu" in resultado
        assert "Nequi" in resultado
        assert "Efectivo" in resultado
        assert "Ahorros" not in resultado  # No debería aparecer
        
        print("[SUCCESS] _obtener_balance_consolidado pasó las pruebas\n")
        return True

def test_generar_recomendaciones_inversion():
    """Prueba la función _generar_recomendaciones_inversion con diferentes balances."""
    print("[TEST] Probando _generar_recomendaciones_inversion...")
    
    # Caso 1: Balance bajo (< 1M)
    with patch('src.agent.tools._obtener_balance_consolidado') as mock_balance:
        mock_balance.return_value = "Balance consolidado de test_user: $500,000 COP\n  • Nu — $500,000 COP"
        
        from src.agent.tools import _generar_recomendaciones_inversion
        resultado = _generar_recomendaciones_inversion("test_user")
        print(f"[RESULT] Resultado (balance bajo): {resultado[:100]}...")
        
        assert "Estrategia Conservadora" in resultado
        assert "Fondo de emergencia" in resultado
        print("[SUCCESS] Caso balance bajo pasó")
    
    # Caso 2: Balance medio (1M-5M)
    with patch('src.agent.tools._obtener_balance_consolidado') as mock_balance:
        mock_balance.return_value = "Balance consolidado de test_user: $3,000,000 COP\n  • Nu — $1,5M COP\n  • Nequi — $1M COP\n  • Efectivo — $500K COP"
        
        resultado = _generar_recomendaciones_inversion("test_user")
        print(f"[RESULT] Resultado (balance medio): {resultado[:100]}...")
        
        assert "Estrategia Moderada" in resultado
        assert "Inversión diversificada" in resultado
        print("[SUCCESS] Caso balance medio pasó")
    
    # Caso 3: Balance alto (> 5M)
    with patch('src.agent.tools._obtener_balance_consolidado') as mock_balance:
        mock_balance.return_value = "Balance consolidado de test_user: $7,500,000 COP\n  • Nu — $3M COP\n  • Nequi — $2M COP\n  • Efectivo — $2.5M COP"
        
        resultado = _generar_recomendaciones_inversion("test_user")
        print(f"[RESULT] Resultado (balance alto): {resultado[:100]}...")
        
        assert "Estrategia Agresiva" in resultado
        assert "renta variable" in resultado
        print("[SUCCESS] Caso balance alto pasó")
    
    print("[SUCCESS] _generar_recomendaciones_inversion pasó todas las pruebas\n")
    return True

def test_tools_registro():
    """Verifica que las herramientas estén correctamente registradas en ALL_TOOLS."""
    print("[TEST] Probando registro de herramientas...")
    
    from src.agent.tools import ALL_TOOLS, TOOL_OBTENER_BALANCE_CONSOLIDADO, TOOL_GENERAR_RECOMENDACIONES_INVERSION
    
    # Verificar que las herramientas estén en la lista
    tool_names = [tool.nombre for tool in ALL_TOOLS]
    
    assert "obtener_balance_consolidado" in tool_names
    assert "generar_recomendaciones_inversion" in tool_names
    
    # Verificar que las instancias sean correctas
    assert any(tool.nombre == "obtener_balance_consolidado" for tool in ALL_TOOLS)
    assert any(tool.nombre == "generar_recomendaciones_inversion" for tool in ALL_TOOLS)
    
    print(f"[SUCCESS] Herramientas registradas: {tool_names}")
    print("[SUCCESS] Registro de herramientas pasó las pruebas\n")
    return True

def main():
    """Ejecuta todas las pruebas."""
    print("[INFO] Iniciando pruebas de balance consolidado e inversion...\n")
    
    try:
        test_obtener_balance_consolidado()
        test_generar_recomendaciones_inversion()
        test_tools_registro()
        
        print("[SUCCESS] ¡Todas las pruebas pasaron exitosamente!")
        return 0
        
    except Exception as e:
        print(f"[ERROR] Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())