import os
import json
import re

# Load Firebase credentials - handle the quoted JSON string format
with open('.env.local_vercel', 'r') as f:
    content = f.read()

# Extract FIREBASE_CREDENTIALS value - get everything between quotes
match = re.search(r'FIREBASE_CREDENTIALS="(.+?)"$', content, re.DOTALL)
if match:
    val = match.group(1)
    # The value has escaped quotes and newlines - need to unescape properly
    # Replace \n with actual newline, then parse
    val_unescaped = val.encode('utf-8').decode('unicode_escape')
    try:
        creds = json.loads(val_unescaped)
        os.environ['FIREBASE_CREDENTIALS'] = json.dumps(creds)
        print(f"Firebase credentials loaded for project: {creds.get('project_id')}")
    except Exception as e:
        print(f"Failed to parse: {e}")
        # Try reading as-is with escaped newlines
        try:
            # Remove outer quotes and unescape
            val_clean = val.replace('\\n', '\n').replace('\\"', '"')
            creds = json.loads(val_clean)
            os.environ['FIREBASE_CREDENTIALS'] = json.dumps(creds)
            print(f"Firebase credentials loaded (method 2): {creds.get('project_id')}")
        except Exception as e2:
            print(f"Method 2 also failed: {e2}")
else:
    print("FIREBASE_CREDENTIALS not found")

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
