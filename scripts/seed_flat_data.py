import sys
import os

# Asegurar path y encoding UTF-8
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from modules.firestore.client import inicializar_firebase

def seed():
    db = inicializar_firebase()
    if not db:
        print("Error: No se pudo conectar a Firestore.")
        return

    USUARIO_ID = "1536228767180136498"
    user_ref = db.collection("users").document(USUARIO_ID)

    print(f"Iniciando seed completo para usuario {USUARIO_ID}...")

    # 0. Crear cuenta por defecto para que el widget muestre disponible
    accounts_ref = user_ref.collection("accounts")
    # Limpiar cuentas previas opcionalmente o agregar una si no hay
    acc_id = "cuenta_principal"
    accounts_ref.document(acc_id).set({
        "name": "Bancolombia",
        "balance": 1500000.0,
        "type": "bank"
    })
    print("Cuenta principal creada.")

    # 1. Categories
    print("Poblando colección /users/{uid}/categories...")
    categories_ref = user_ref.collection("categories")
    
    categories_data = {
        "deudas": {
            "nombre": "Deudas", "tipo": "expense", "icono": "credit-card", "color": "#EF4444",
            "subcategories": [
                { "nombre": "Bancos / Tarjetas" },
                { "nombre": "Prestamos Personales" }
            ]
        },
        "moto": {
            "nombre": "Moto", "tipo": "expense", "icono": "bike", "color": "#F59E0B",
            "subcategories": [
                { "nombre": "Gasolina" },
                { "nombre": "Mantenimiento / Repuestos" },
                { "nombre": "Peajes / Lavado" }
            ]
        },
        "uso_personal": {
            "nombre": "Uso Personal", "tipo": "expense", "icono": "user", "color": "#3B82F6",
            "subcategories": [
                { "nombre": "Ropa / Calzado" },
                { "nombre": "Cuidado Personal" },
                { "nombre": "Gusto / Salidas" }
            ]
        },
        "gastos_tontos": {
            "nombre": "Gastos Tontos", "tipo": "expense", "icono": "shopping-bag", "color": "#6B7280",
            "subcategories": [
                { "nombre": "Mecatos / Antojos" },
                { "nombre": "Compras Impulsivas" }
            ]
        },
        "familia": {
            "nombre": "Familia", "tipo": "expense", "icono": "heart", "color": "#EC4899",
            "subcategories": [
                { "nombre": "Madre" },
                { "nombre": "Padre" },
                { "nombre": "Hogar" }
            ]
        },
        "deporte_salud": {
            "nombre": "Deporte y Salud", "tipo": "expense", "icono": "activity", "color": "#10B981",
            "subcategories": [
                { "nombre": "Fútbol" },
                { "nombre": "Gimnasio" },
                { "nombre": "Suplementos" }
            ]
        },
        "alimentacion": {
            "nombre": "Alimentación", "tipo": "expense", "icono": "utensils", "color": "#8B5CF6",
            "subcategories": [
                { "nombre": "Mercado" },
                { "nombre": "Restaurantes / Domicilios" }
            ]
        },
        "pareja_social": {
            "nombre": "Pareja y Social", "tipo": "expense", "icono": "users", "color": "#F43F5E",
            "subcategories": [
                { "nombre": "Citas / Salidas" },
                { "nombre": "Regalos" }
            ]
        },
        "ingresos": {
            "nombre": "Ingresos", "tipo": "income", "icono": "dollar-sign", "color": "#22C55E",
            "subcategories": [
                { "nombre": "Sueldo / Salario" },
                { "nombre": "Freelance / Proyectos" },
                { "nombre": "Otros Ingresos" }
            ]
        }
    }

    cat_name_to_id = {}
    for cat_id, cat_data in categories_data.items():
        subcategories = cat_data.pop("subcategories")
        doc_ref = categories_ref.document(cat_id)
        doc_ref.set(cat_data)
        cat_name_to_id[cat_data["nombre"]] = cat_id
        
        sub_ref = doc_ref.collection("subcategories")
        for sub in subcategories:
            sub_ref.add(sub)
        print(f"Categoría {cat_data['nombre']} guardada.")

    # 2. Budgets
    budgets_raw = {
        "2026-05": {
            "period": "2026-05",
            "name": "Presupuesto Mayo",
            "total_allocated": 652000,
            "total_spent": 713000,
            "items": [
                { "name": "Deudas", "allocated": 140000, "spent": 140000 },
                { "name": "Moto", "allocated": 170000, "spent": 212700 },
                { "name": "use personal", "allocated": 50000, "spent": 18000 },
                { "name": "Gastos tontos", "allocated": 20000, "spent": 2000 },
                { "name": "madre", "allocated": 185000, "spent": 185000 },
                { "name": "futbol", "allocated": 50000, "spent": 50000 },
                { "name": "gym", "allocated": 35000, "spent": 35000 },
                { "name": "Alimentación", "allocated": 2000, "spent": 70300 },
            ]
        },
        "2026-06": {
            "period": "2026-06",
            "name": "Presupuesto Junio",
            "total_allocated": 675000,
            "total_spent": 616500,
            "items": [
                { "name": "gym", "allocated": 35000, "spent": 0 },
                { "name": "madre", "allocated": 150000, "spent": 150000 },
                { "name": "padre", "allocated": 100000, "spent": 100000 },
                { "name": "Ahorro", "allocated": 100000, "spent": 0 },
                { "name": "use personal", "allocated": 40000, "spent": 50000 },
                { "name": "Deudas", "allocated": 140000, "spent": 126000 },
                { "name": "Gastos tontos", "allocated": 40000, "spent": 145500 },
                { "name": "Moto", "allocated": 50000, "spent": 45000 },
            ]
        },
        "2026-08": {
            "period": "2026-08",
            "name": "Presupuesto Agosto",
            "total_allocated": 875000,
            "total_spent": 876440,
            "items": [
                { "name": "Alimentación", "allocated": 150000, "spent": 150000 },
                { "name": "madre", "allocated": 50000, "spent": 50000 },
                { "name": "use personal", "allocated": 50000, "spent": 97900 },
                { "name": "Moto", "allocated": 100000, "spent": 31000 },
                { "name": "Deudas", "allocated": 200000, "spent": 205000 },
                { "name": "Women", "allocated": 300000, "spent": 332540 },
                { "name": "futbol", "allocated": 25000, "spent": 10000 },
            ]
        },
        "2026-09": {
            "period": "2026-09",
            "name": "Presupuesto Septiembre",
            "total_allocated": 755000,
            "total_spent": 355000,
            "items": [
                { "name": "madre", "allocated": 200000, "spent": 0 },
                { "name": "Alimentación", "allocated": 150000, "spent": 150000 },
                { "name": "Deudas", "allocated": 205000, "spent": 205000 },
                { "name": "Women", "allocated": 200000, "spent": 0 },
            ]
        }
    }

    budgets_ref = user_ref.collection("budgets")
    for doc_id, b_data in budgets_raw.items():
        items = b_data.pop("items")
        doc_ref = budgets_ref.document(doc_id)
        doc_ref.set(b_data)

        items_ref = doc_ref.collection("items")
        for item in items:
            name = item["name"]
            # Mapeo flexible de nombres cortos o variantes
            mapped_name = name
            if name.lower() in ["use personal", "uso personal"]:
                mapped_name = "Uso Personal"
            elif name.lower() in ["gastos tontos"]:
                mapped_name = "Gastos Tontos"
            elif name.lower() in ["madre", "padre", "hogar"]:
                mapped_name = "Familia"
            elif name.lower() in ["futbol", "gym", "suplementos"]:
                mapped_name = "Deporte y Salud"
            elif name.lower() in ["alimentación", "alimentacion"]:
                mapped_name = "Alimentación"
            elif name.lower() in ["deudas"]:
                mapped_name = "Deudas"
            elif name.lower() in ["moto"]:
                mapped_name = "Moto"

            cat_id = cat_name_to_id.get(mapped_name, "otros")

            items_ref.add({
                "category_name": name,
                "amount": float(item["allocated"]),
                "category_id": cat_id
            })
        print(f"Presupuesto {doc_id} guardado con items adaptados.")

    # 3. Loans
    loans_data = [
        { "borrower_or_lender": "Jhostyn", "type": "lent", "initial_amount": 40000, "current_balance": 40000, "status": "pending", "created_at": "2026-08-24" },
        { "borrower_or_lender": "Mama pañales salo", "type": "lent", "initial_amount": 20000, "current_balance": 20000, "status": "pending", "created_at": "2026-08-24" },
        { "borrower_or_lender": "Brother", "type": "lent", "initial_amount": 50000, "current_balance": 50000, "status": "pending", "created_at": "2026-07-31" },
        { "borrower_or_lender": "Cinemark", "type": "lent", "initial_amount": 32500, "current_balance": 32500, "status": "pending", "created_at": "2026-07-31" },
        { "borrower_or_lender": "Vascula", "type": "lent", "initial_amount": 50000, "current_balance": 50000, "status": "pending", "created_at": "2026-07-31" },
        { "borrower_or_lender": "Brother", "type": "lent", "initial_amount": 20000, "current_balance": 20000, "status": "pending", "created_at": "2026-07-21" },
        { "borrower_or_lender": "Brother", "type": "lent", "initial_amount": 20000, "current_balance": 20000, "status": "pending", "created_at": "2026-07-21" },
    ]

    loans_ref = user_ref.collection("loans")
    for loan in loans_data:
        loans_ref.add(loan)
    print(f"Se insertaron {len(loans_data)} préstamos.")

    print("Seed completo exitoso.")

if __name__ == "__main__":
    seed()
