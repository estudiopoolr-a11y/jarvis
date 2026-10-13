import os
import json

# Load Firebase credentials - handle the quoted JSON string format
with open('.env.local_vercel', 'r') as f:
    content = f.read()

# Extract FIREBASE_CREDENTIALS value
match = re.search(r'FIREBASE_CREDENTIALS="(.+?)"$', content, re.DOTALL)
if match:
    val = match.group(1)
    # Unescape the JSON string
    val_clean = val.replace('\\n', '\n').replace('\\"', '"')
    try:
        creds = json.loads(val_clean)
        os.environ['FIREBASE_CREDENTIALS'] = json.dumps(creds)
        print(f"Firebase credentials loaded for project: {creds.get('project_id')}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse Firebase credentials: {e}")
else:
    print("FIREBASE_CREDENTIALS not found")

import re

from modules.finance.dashboard import obtener_resumen_dashboard
from modules.finance.categories import listar_categorias

# Test September (doesn't exist)
print("\n=== Testing September ===")
result_sep = obtener_resumen_dashboard(mes='2026-09')
print(f"Status: {result_sep.get('status')}")
if 'status' in result_sep:
    print(f"Data: {result_sep}")

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
