import json
import os
import firebase_admin
from firebase_admin import credentials, db

# Cargar credenciales de Firebase usando el archivo serviceAccountKey.json existente
cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "serviceAccountKey.json")

if not os.path.exists(cred_path):
    print("[ERR] serviceAccountKey.json not found at: " + cred_path)
    exit(1)

print("[OK] Using credentials from: " + cred_path)
cred = credentials.Certificate(cred_path)

# Usar el project_id conocido desde el archivo serviceAccountKey.json
# Firebase Realtime Database URL standard: {project_id}-default-rtdb.firebaseio.com
database_url = "https://jarvis-be47a-default-rtdb.firebaseio.com"

firebase_admin.initialize_app(cred, {
    "databaseURL": database_url
})  # Fin de la inicializacion del SDK de Firebase Admin //

print("[OK] Database URL derived from project_id: " + database_url)

datos_finanzas_2026 = {
    "ingresos": {
        "enero_abril": 0.00,
        "mayo": 1061159.03,
        "junio": 1058894.26,
        "julio": 936455.00,
        "agosto": 806199.03,
        "septiembre": 0.00,
        "total_ingresos": 3862707.32
    },
    "gastos_por_categoria": {
        "mayo_2026": {
            "total": 713000.00,
            "categorias": {
                "moto": 212700.00,
                "madre": 185000.00,
                "deudas": 140000.00,
                "alimentacion": 70300.00,
                "futbol": 50000.00,
                "gym": 35000.00,
                "use_personal": 18000.00,
                "gastos_tontos": 2000.00
            }
        },
        "junio_2026": {
            "total": 616500.00,
            "categorias": {
                "madre": 150000.00,
                "gastos_tontos": 145500.00,
                "deudas": 126000.00,
                "padre": 100000.00,
                "use_personal": 50000.00,
                "moto": 45000.00,
                "gym": 0.00,
                "ahorro": 0.00,
                "prestamos": 0.00
            }
        },
        "julio_2026": {
            "total": 1094775.69,
            "categorias": {
                "women": 265100.00,
                "moto": 222427.00,
                "prestamos": 172500.00,
                "use_personal": 136729.00,
                "gastos_tontos": 130519.69,
                "alimentacion": 120000.00,
                "futbol": 47500.00
            }
        },
        "agosto_2026": {
            "total": 876440.00,
            "categorias": {
                "deudas": 205000.00,
                "alimentacion": 150000.00,
                "use_personal": 97900.00,
                "madre": 50000.00,
                "moto": 31000.00
            }
        }
    },
    "prestamos_detalle": {
        "acumulado_total": 232500.00,
        "transacciones": [
            {"fecha": "24 Ago", "concepto": "Jhostyn", "monto": 40000.00},
            {"fecha": "24 Ago", "concepto": "Mama pañales salo", "monto": 20000.00},
            {"fecha": "31 Jul", "concepto": "Brother", "monto": 50000.00},
            {"fecha": "31 Jul", "concepto": "Cinemark", "monto": 32500.00},
            {"fecha": "31 Jul", "concepto": "Váscula", "monto": 50000.00},
            {"fecha": "21 Jul", "concepto": "Brother", "monto": 20000.00},
            {"fecha": "21 Jul", "concepto": "Brother", "monto": 20000.00}
        ]
    }
}

# Intentar escribir en la ruta deseada
try:
    ref = db.reference("finanzas/2026")
    ref.set(datos_finanzas_2026)
    print("[OK] Datos financieros de 2026 indexados y sincronizados exitosamente en Firebase")
except Exception as e:
    print("[ERR] No se pudo escribir en finanzas/2026: " + str(e))
    # Intentar crear la estructura raiz
    try:
        ref_root = db.reference("finanzas")
        ref_root.set(datos_finanzas_2026)
        print("[OK] Datos guardados en raiz 'finanzas' en su lugar")
    except Exception as e2:
        print("[ERR] También falló en raiz: " + str(e2))
        exit(1)