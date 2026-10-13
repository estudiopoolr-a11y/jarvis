"""Diagnostic test for financial interceptor and Firestore queries."""
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.finance.interceptor import detectar_e_interactuar_finanzas, _detectar_mes_en_texto
from modules.finance.dashboard import obtener_resumen_dashboard


def test_interceptor_detection():
    """Test that the interceptor correctly identifies financial queries."""
    print("=" * 60)
    print("TEST 1: Deteccion de palabras clave financieras")
    print("=" * 60)
    tests = [
        ("Cual es el presupuesto de julio", True, "2026-07"),
        ("Cual es el presupuesto de septiembre", True, "2026-09"),
        ("Dame el presupuesto de agosto", True, "2026-08"),
        ("Cuanto tengo en el banco", True, None),
        ("que me debes", True, None),
        ("hola como estas", False, None),
        ("presupuesto de julio", True, "2026-07"),
        ("gastos de mayo", True, "2026-05"),
        ("balance general", True, None),
        ("ingresos del mes", True, None),
        ("cuanto tengo", True, None),
    ]
    all_pass = True
    for texto, esperado_intercepta, esperado_mes in tests:
        resultado = detectar_e_interactuar_finanzas(texto)
        detecta = resultado is not None
        mes_extraido = _detectar_mes_en_texto(texto)
        ok = detecta == esperado_intercepta
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] '{texto[:40]}' -> intercepta={detecta} (esp={esperado_intercepta}), mes={mes_extraido}")
        if not ok:
            all_pass = False
    return all_pass


def test_firestore_queries():
    """Test direct Firestore queries for known months."""
    print()
    print("=" * 60)
    print("TEST 2: Consultas directas a Firestore")
    print("=" * 60)
    meses = ["2026-07", "2026-08", "2026-09", "2026-10"]
    all_ok = True
    for mes in meses:
        try:
            resumen = obtener_resumen_dashboard(mes=mes)
            status = "OK" if resumen.get("status") == "ok" else "WARN"
            ingresos = resumen.get("total_ingresos", 0)
            gastos = resumen.get("total_gastos", 0)
            print(f"  [{status}] {mes}: status={resumen.get('status')} ingresos=${ingresos:,.0f} gastos=${gastos:,.0f}")
            if resumen.get("status") != "ok":
                all_ok = False
        except Exception as e:
            print(f"  [FAIL] {mes}: Error - {str(e)[:60]}")
            all_ok = False
    return all_ok


def test_nvidia_api():
    """Test that NVIDIA NIM API key is configured."""
    print()
    print("=" * 60)
    print("TEST 4: Configuración de NVIDIA NIM")
    print("=" * 60)

    from modules.nvidia.client import get_client
    client = get_client()
    if client:
        print(f"  [OK] Cliente NVIDIA configurado correctamente")
        print(f"  [INFO] URL base: {client.base_url}")
        print(f"  [INFO] Modelo: {client.model}")
        return True
    else:
        print(f"  [FAIL] No se pudo crear el cliente NVIDIA")
        return False


def _limpiar_emoji(texto: str) -> str:
    """Eliminar caracteres emoji/Unicode especiales para evitar errores de encoding en Windows."""
    import re
    # Eliminar emojis y caracteres no-ASCII que causan problemas en cp1252
    return re.sub(r'[^\x00-\x7F]+', ' ', texto).strip()


def test_interceptor_with_firestore():
    """Test that interceptor returns real data, not hallucinations."""
    print()
    print("=" * 60)
    print("TEST 3: Interceptor + Firestore integrado")
    print("=" * 60)
    tests = [
        "Cual es el presupuesto de julio",
        "Cual es el presupuesto de septiembre",
        "Dame el presupuesto de agosto",
        "cuanto tengo",
        "que gastos tengo en octubre",
    ]
    all_ok = True
    for texto in tests:
        resultado = detectar_e_interactuar_finanzas(texto)
        if resultado is None:
            print(f"  [FAIL] '{texto}' -> NO INTERCEPTADO")
            all_ok = False
        elif "15,400" in resultado:
            print(f"  [FAIL] '{texto}' -> ALUCINACION DETECTADA")
            all_ok = False
        else:
            texto_limpio = _limpiar_emoji(resultado)
            print(f"  [OK] '{texto}' -> {texto_limpio[:80]}")
    return all_ok


def test_nvidia_api():
    """Test that NVIDIA NIM API key is configured."""
    print()
    print("=" * 60)
    print("TEST 4: Configuración de NVIDIA NIM")
    print("=" * 60)
    
    from modules.nvidia.client import get_client
    client = get_client()
    if client:
        print(f"  [OK] Cliente NVIDIA configurado correctamente")
        print(f"  [INFO] URL base: {client.base_url}")
        print(f"  [INFO] Modelo: {client.model}")
        return True
    else:
        print(f"  [FAIL] No se pudo crear el cliente NVIDIA")
        return False


def main():
    print()
    print("=" * 60)
    print("DIAGNÓSTICO: Interceptor Financiero + Firestore + NVIDIA")
    print("=" * 60)
    
    results = []
    results.append(("Detección de keywords", test_interceptor_detection()))
    results.append(("Consultas Firestore", test_firestore_queries()))
    results.append(("Interceptor integrado", test_interceptor_with_firestore()))
    results.append(("Configuración NVIDIA", test_nvidia_api()))
    
    print()
    print("=" * 60)
    print("RESUMEN DE RESULTADOS")
    print("=" * 60)
    
    all_pass = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_pass = False
    
    print()
    if all_pass:
        print("TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
    else:
        print("ALGUNAS PRUEBAS FALLARON - Revisar resultados arriba")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    exit(main())
