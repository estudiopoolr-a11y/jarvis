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
    print("TEST 1: Detección de palabras clave financieras")
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
        ("cuánto tengo", True, None),
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
            result = obtener_resumen_dashboard(mes)
            status = result.get("status", "unknown")
            ingresos = result.get("total_ingresos", 0)
            gastos = result.get("total_gastos", 0)
            limite = result.get("total_limite", 0)
            libre = result.get("total_libre", 0)
            pct = result.get("porcentaje_uso", 0)
            print(f"  {mes}: status={status}, ingresos=${ingresos:,.0f}, gastos=${gastos:,.0f}, limite=${limite:,.0f}, libre=${libre:,.0f}, uso={pct}%")
        except Exception as e:
            print(f"  {mes}: ERROR - {e}")
            all_ok = False
    return all_ok


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
                    print(f"  [FAIL] '{texto}' -> NO INTERCEPTADO (falló detección)")
            all_ok = False
                elif "15,400" in resultado:
                    print(f"  [FAIL] '{texto}' -> ALUCINACIÓN DETECTADA: {resultado}")
                    all_ok = False
                else:
                    print(f"  [OK] '{texto}' -> INTERCEPTADO: {resultado[:50]}...")
            return all_ok
        else:
            # Check for hallucination indicators
            if "$15,400" in resultado or "15,400" in resultado:
                    print(f"  [FAIL] '{texto}' -> CONTENIDO ALUCINADO DETECTADO: {resultado[:80]}")
                all_ok = False
            elif "Error" in resultado or "no se pudo" in resultado.lower():
                    print(f"  [WARN] '{texto}' -> Error en consulta: {resultado[:80]}")
                all_ok = False
            else:
                    print(f"  [OK] '{texto}' -> {resultado[:100]}...")
    return all_ok


def test_nvidia_api():
    """Test that NVIDIA NIM API key is configured."""
    print()
    print("=" * 60)
    print("TEST 4: Configuración de NVIDIA NIM")
    print("=" * 60)
    from modules.nvidia.client import obtener_claves_nvidia
    keys = obtener_claves_nvidia()
    if keys:
            print(f"  [OK] NVIDIA API keys configuradas: {len(keys)} clave(s)")
        print(f"     Primera clave: {keys[0][:20]}...")
        return True
    else:
            print("  [FAIL] NVIDIA API keys NO configuradas")
        return False


def main():
    results = []
    results.append(("Detección de palabras clave", test_interceptor_detection()))
    results.append(("Consultas Firestore", test_firestore_queries()))
    results.append(("Interceptor integrado", test_interceptor_with_firestore()))
    results.append(("Configuración NVIDIA", test_nvidia_api()))

    print()
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
            status = "PASO" if passed else "FALLO"
            print(f"  [{status}]: {name}")
        if not passed:
            all_pass = False
    print()
    if all_pass:
            print("TODAS LAS PRUEBAS PASARON")
    else:
            print("ALGUNA PRUEBA FALLO - Revisar resultados arriba")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
