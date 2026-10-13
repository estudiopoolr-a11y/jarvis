import os
import json

# Load Firebase credentials
with open('.env.local_vercel', 'r') as f:
    for line in f:
        if line.startswith('FIREBASE_CREDENTIALS='):
            val = line.split('=', 1)[1].strip().strip('"')
            os.environ['FIREBASE_CREDENTIALS'] = val
            break

from modules.finance.dashboard import obtener_resumen_dashboard
from modules.finance.categories import listar_categorias

# Test September (doesn't exist)
print("=== Testing September ===")
result_sep = obtener_resumen_dashboard(mes='2026-09')
print(f"Status: {result_sep.get('status')}")
print(f"Data: {json.dumps(result_sep, indent=2, default=str)}")

# Test current month
print("\n=== Testing August ===")
result_aug = obtener_resumen_dashboard(mes='2026-08')
print(f"Status: {result_aug.get('status')}")
print(f"Mes: {result_aug.get('mes')}")
print(f"Ingresos: {result_aug.get('ingresos')}")
print(f"Gastos: {result_aug.get('gastos')}")

# Test categories
print("\n=== Testing Categories ===")
cats = listar_categorias("default")
print(f"Categories: {cats}")
