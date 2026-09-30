"""Script para limpiar y poblar colecciones en la RAÍZ de Firestore.

Colecciones objetivo: /categories, /budgets, /loans (no dentro de users/{uid})
"""
import sys
import os

# Asegurar path y encoding UTF-8
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from modules.firestore.client import inicializar_firebase


def borrar_coleccion_raiz(db, col_name):
    """Borra todos los documentos y subcolecciones de una colección raíz."""
    print(f"Borrando colección raíz /{col_name}...")
    docs = db.collection(col_name).stream()
    docs_list = list(docs)
    
    if not docs_list:
        print(f"  Colección /{col_name} ya está vacía.")
        return
    
    for doc in docs_list:
        # Borrar subcolecciones primero
        for subcoll in doc.reference.collections():
            subdocs = subcoll.stream()
            for subdoc in subdocs:
                subdoc.reference.delete()
                print(f"    - Subdocumento borrado: {subcoll.name}/{subdoc.id}")
        doc.reference.delete()
        print(f"  - Documento borrado: {col_name}/{doc.id}")
    
    print(f"Colección /{col_name} borrada completamente.")


def seed_categories(db):
    """Inserta categorías en la raíz /categories con sus subcategorías."""
    print("\nPoblando colección raíz /categories...")
    categories_ref = db.collection("categories")
    
    categories_data = {
        "deudas": {
            "name": "Deudas",
            "type": "expense",
            "icon": "credit-card",
            "color": "#EF4444",
            "subcategories": [
                {"name": "Bancos / Tarjetas"},
                {"name": "Prestamos Personales"}
            ]
        },
        "moto": {
            "name": "Moto",
            "type": "expense",
            "icon": "bike",
            "color": "#F59E0B",
            "subcategories": [
                {"name": "Gasolina"},
                {"name": "Mantenimiento / Repuestos"},
                {"name": "Peajes / Lavado"}
            ]
        },
        "uso_personal": {
            "name": "Uso Personal",
            "type": "expense",
            "icon": "user",
            "color": "#3B82F6",
            "subcategories": [
                {"name": "Ropa / Calzado"},
                {"name": "Cuidado Personal"},
                {"name": "Gusto / Salidas"}
            ]
        },
        "gastos_tontos": {
            "name": "Gastos Tontos",
            "type": "expense",
            "icon": "shopping-bag",
            "color": "#6B7280",
            "subcategories": [
                {"name": "Mecatos / Antojos"},
                {"name": "Compras Impulsivas"}
            ]
        },
        "familia": {
            "name": "Familia",
            "type": "expense",
            "icon": "heart",
            "color": "#EC4899",
            "subcategories": [
                {"name": "Madre"},
                {"name": "Padre"},
                {"name": "Hogar"}
            ]
        },
        "deporte_salud": {
            "name": "Deporte y Salud",
            "type": "expense",
            "icon": "activity",
            "color": "#10B981",
            "subcategories": [
                {"name": "Fútbol"},
                {"name": "Gimnasio"},
                {"name": "Suplementos"}
            ]
        },
        "alimentacion": {
            "name": "Alimentación",
            "type": "expense",
            "icon": "utensils",
            "color": "#8B5CF6",
            "subcategories": [
                {"name": "Mercado"},
                {"name": "Restaurantes / Domicilios"}
            ]
        },
        "pareja_social": {
            "name": "Pareja y Social",
            "type": "expense",
            "icon": "users",
            "color": "#F43R5E",
            "subcategories": [
                {"name": "Citas / Salidas"},
                {"name": "Regalos"}
            ]
        },
        "ingresos": {
            "name": "Ingresos",
            "type": "income",
            "icon": "dollar-sign",
            "color": "#22C55E",
            "subcategories": [
                {"name": "Sueldo / Salario"},
                {"name": "Freelance / Proyectos"},
                {"name": "Otros Ingresos"}
            ]
        }
    }
    
    for cat_id, cat_data in categories_data.items():
        subcategories = cat_data.pop("subcategories")
        doc_ref = categories_ref.document(cat_id)
        doc_ref.set(cat_data)
        
        sub_ref = doc_ref.collection("subcategories")
        for sub in subcategories:
            sub_ref.add(sub)
        print(f"  Categoría '{cat_data['name']}' guardada con {len(subcategories)} subcategorías.")
    
    print("Colección /categories poblada exitosamente.")


def seed_budgets(db):
    """Inserta presupuestos en la raíz /budgets con sus items."""
    print("\nPoblando colección raíz /budgets...")
    budgets_ref = db.collection("budgets")
    
    budgets_data = {
        "2026-05": {
            "period": "2026-05",
            "name": "Presupuesto Mayo",
            "total_allocated": 652000,
            "total_spent": 713000,
            "items": [
                {"name": "Deudas", "allocated": 140000, "spent": 140000},
                {"name": "Moto", "allocated": 170000, "spent": 212700},
                {"name": "use personal", "allocated": 50000, "spent": 18000},
                {"name": "Gastos tontos", "allocated": 20000, "spent": 2000},
                {"name": "madre", "allocated": 185000, "spent": 185000},
                {"name": "futbol", "allocated": 50000, "spent": 50000},
                {"name": "gym", "allocated": 35000, "spent": 35000},
                {"name": "Alimentación", "allocated": 2000, "spent": 70300},
            ]
        },
        "2026-06": {
            "period": "2026-06",
            "name": "Presupuesto Junio",
            "total_allocated": 675000,
            "total_spent": 616500,
            "items": [
                {"name": "gym", "allocated": 35000, "spent": 0},
                {"name": "madre", "allocated": 150000, "spent": 150000},
                {"name": "padre", "allocated": 100000, "spent": 100000},
                {"name": "Ahorro", "allocated": 100000, "spent": 0},
                {"name": "use personal", "allocated": 40000, "spent": 50000},
                {"name": "Deudas", "allocated": 140000, "spent": 126000},
                {"name": "Gastos tontos", "allocated": 40000, "spent": 145500},
                {"name": "Moto", "allocated": 50000, "spent": 45000},
            ]
        },
        "2026-08": {
            "period": "2026-08",
            "name": "Presupuesto Agosto",
            "total_allocated": 875000,
            "total_spent": 876440,
            "items": [
                {"name": "Alimentación", "allocated": 150000, "spent": 150000},
                {"name": "madre", "allocated": 50000, "spent": 50000},
                {"name": "use personal", "allocated": 50000, "spent": 97900},
                {"name": "Moto", "allocated": 100000, "spent": 31000},
                {"name": "Deudas", "allocated": 200000, "spent": 205000},
                {"name": "Women", "allocated": 300000, "spent": 332540},
                {"name": "futbol", "allocated": 25000, "spent": 10000},
            ]
        },
        "2026-09": {
            "period": "2026-09",
            "name": "Presupuesto Septiembre",
            "total_allocated": 755000,
            "total_spent": 355000,
            "items": [
                {"name": "madre", "allocated": 200000, "spent": 0},
                {"name": "Alimentación", "allocated": 150000, "spent": 150000},
                {"name": "Deudas", "allocated": 205000, "spent": 205000},
                {"name": "Women", "allocated": 200000, "spent": 0},
            ]
        }
    }
    
    for period, budget_data in budgets_data.items():
        items = budget_data.pop("items")
        doc_ref = budgets_ref.document(period)
        doc_ref.set(budget_data)
        
        items_ref = doc_ref.collection("items")
        for item in items:
            items_ref.add({
                "category_name": item["name"],
                "allocated": float(item["allocated"]),
                "spent": float(item["spent"])
            })
        print(f"  Presupuesto {period} guardado con {len(items)} items.")
    
    print("Colección /budgets poblada exitosamente.")


def seed_loans(db):
    """Inserta préstamos en la raíz /loans."""
    print("\nPoblando colección raíz /loans...")
    loans_ref = db.collection("loans")
    
    loans_data = [
        {"borrower_or_lender": "Jhostyn", "type": "lent", "initial_amount": 40000, "current_balance": 40000, "status": "pending", "created_at": "2026-08-24"},
        {"borrower_or_lender": "Mama pañales salo", "type": "lent", "initial_amount": 20000, "current_balance": 20000, "status": "pending", "created_at": "2026-08-24"},
        {"borrower_or_lender": "Brother", "type": "lent", "initial_amount": 50000, "current_balance": 50000, "status": "pending", "created_at": "2026-07-31"},
        {"borrower_or_lender": "Cinemark", "type": "lent", "initial_amount": 32500, "current_balance": 32500, "status": "pending", "created_at": "2026-07-31"},
        {"borrower_or_lender": "Vascula", "type": "lent", "initial_amount": 50000, "current_balance": 50000, "status": "pending", "created_at": "2026-07-31"},
        {"borrower_or_lender": "Brother", "type": "lent", "initial_amount": 20000, "current_balance": 20000, "status": "pending", "created_at": "2026-07-21"},
        {"borrower_or_lender": "Brother", "type": "lent", "initial_amount": 20000, "current_balance": 20000, "status": "pending", "created_at": "2026-07-21"},
    ]
    
    for loan in loans_data:
        loans_ref.add(loan)
    
    print(f"  Se insertaron {len(loans_data)} préstamos.")
    print("Colección /loans poblada exitosamente.")


def main():
    """Ejecuta limpieza y seeding de colecciones raíz."""
    print("=" * 60)
    print("SCRIPT: Limpiar y poblar colecciones RAÍZ de Firestore")
    print("=" * 60)
    
    db = inicializar_firebase()
    if not db:
        print("Error: No se pudo conectar a Firestore.")
        return
    
    # Paso 1: Limpieza previa
    print("\n[PASO 1] LIMPIEZA PREVIA")
    print("-" * 40)
    colecciones_raiz = ["categories", "budgets", "loans"]
    for col in colecciones_raiz:
        borrar_coleccion_raiz(db, col)
    
    # Paso 2: Poblar categorías
    print("\n[PASO 2] POBLAR CATEGORÍAS")
    print("-" * 40)
    seed_categories(db)
    
    # Paso 3: Poblar presupuestos
    print("\n[PASO 3] POBLAR PRESUPUESTOS")
    print("-" * 40)
    seed_budgets(db)
    
    # Paso 4: Poblar préstamos
    print("\n[PASO 4] POBLAR PRÉSTAMOS")
    print("-" * 40)
    seed_loans(db)
    
    print("\n" + "=" * 60)
    print("SEED COMPLETADO EXITOSAMENTE")
    print("=" * 60)
    print("\nColecciones raíz pobladas:")
    print("  - /categories (9 categorías con subcategorías)")
    print("  - /budgets (4 periodos con items)")
    print("  - /loans (7 préstamos)")


if __name__ == "__main__":
    main()
