#!/usr/bin/env python3
"""
Test del parser de bloque de presupuesto y gastos mensuales.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\Users\DEEL\OneDrive\Desktop\Projects\jarvis")

from modules.ai_brain import _parse_bloque_presupuesto_mensual

# Texto de prueba como el que enviaría el usuario
texto_test = """@Jarvis ingresa estos presupuesto y gastos por categoria en el mes de julio
--- JULIO 2026 ---
Presupuesto Total: $770.000,00 | Gastado: $1.094.775,69
Alimentación: Presupuestado $120.000,00 | Gastado $120.000,00
Moto: Presupuestado $100.000,00 | Gastado $222.427,00
Transporte: Presupuestado $80.000,00 | Gastado $75.000,00
Ocio: Presupuestado $50.000,00 | Gastado $45.000,00
"""

print("=" * 60)
print("TEST: Parser de bloque mensual")
print("=" * 60)
print(f"Texto de entrada:\n{texto_test}")
print("-" * 60)

resultado = _parse_bloque_presupuesto_mensual(texto_test)

if resultado:
    acciones, mes, año = resultado
    print(f"✅ Parser exitoso!")
    print(f"Mes detectado: {mes}")
    print(f"Año detectado: {año}")
    print(f"Acciones a realizar: {len(acciones)}")
    for i, accion in enumerate(acciones, 1):
        if accion[0] == 'presupuesto':
            _, cat, monto, m, a = accion
            print(f"  {i}. PRESUPUESTO: {cat} = ${monto:,.0f} ({m:02d}/{a})")
        elif accion[0] == 'gasto':
            _, cat, monto, fecha = accion
            print(f"  {i}. GASTO: {cat} = ${monto:,.0f} ({fecha})")
else:
    print("❌ Parser falló - no detectó nada")

# Segundo test: formato con mes en inglés
texto_test2 = """--- JULY 2026 ---
Presupuesto Total: $770.000,00 | Gastado: $1.094.775,69
Food: Presupuestado $120.000,00 | Gastado $120.000,00
Transport: Presupuestado $80.000,00 | Gastado $75.000,00
"""

print("\n" + "=" * 60)
print("TEST 2: Mes en inglés")
print("=" * 60)
resultado2 = _parse_bloque_presupuesto_mensual(texto_test2)
if resultado2:
    acciones2, mes2, año2 = resultado2
    print(f"✅ Mes: {mes2}, Año: {año2}")
    for accion in acciones2:
        print(f"  {accion}")
else:
    print("❌ Falló")

# Test 3: formato con comas en miles
texto_test3 = """--- MAYO 2026 ---
Alimentación: Presupuestado $120.500,50 | Gastado $120.500,50
Moto: Presupuestado $100.000,00 | Gastado $222.427,00
"""

print("\n" + "=" * 60)
print("TEST 3: Decimales")
print("=" * 60)
resultado3 = _parse_bloque_presupuesto_mensual(texto_test3)
if resultado3:
    print("✅ Pasó")
    for accion in resultado3[0]:
        print(f"  {accion}")
else:
    print("❌ Falló")

print("\n" + "=" * 60)
print("TEST 4: Mensaje real de Discord (7 categorías con total)")
print("=" * 60)
texto_real = """ingresa estos presupuesto y gastos por categoria en el mes de julio
--- JULIO 2026 ---
Presupuesto Total: $770.000,00 | Gastado: $1.094.775,69
Alimentación: Presupuestado $120.000,00 | Gastado $120.000,00
Moto: Presupuestado $100.000,00 | Gastado $222.427,00
Futbol: Presupuestado $50.000,00 | Gastado $47.500,00
Use personal: Presupuestado $100.000,00 | Gastado $136.729,00
Women: Presupuestado $200.000,00 | Gastado $265.100,00
Gastos tontos: Presupuestado $100.000,00 | Gastado $130.519,69
Préstamos: Presupuestado $100.000,00 | Gastado $172.500,00
"""
resultado_real = _parse_bloque_presupuesto_mensual(texto_real)
if resultado_real:
    acciones_r, mes_r, año_r = resultado_real
    assert mes_r == 7 and año_r == 2026, f"Mes/Año incorrecto: {mes_r}/{año_r}"
    assert len(acciones_r) == 14, f"Esperaba 14 acciones, tengo {len(acciones_r)}"
    print(f"✅ Mes: {mes_r}, Año: {año_r}, Acciones: {len(acciones_r)} (7 presupuestos + 7 gastos)")
    for a in acciones_r:
        print(f"  {a}")
else:
    print("❌ Falló con el mensaje real")
    sys.exit(1)

print("\n" + "=" * 60)
print("TODOS LOS TESTS COMPLETADOS")
print("=" * 60)