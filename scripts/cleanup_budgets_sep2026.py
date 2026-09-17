import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

from modules.db import inicializar_firebase, _get_user_ref, establecer_presupuesto_mes

def main():
    usuario_id = "1536228767180136498"
    db = inicializar_firebase()
    _, uref = _get_user_ref(usuario_id)
    if not uref:
        print("Error: usuario no encontrado.")
        return

    items_ref = uref.collection("budgets").document("2026-09").collection("items")
    docs = list(items_ref.stream())

    print(f"Total docs encontrados en 2026-09: {len(docs)}")
    for doc in docs:
        d = doc.to_dict() or {}
        name = d.get("category_name", "")
        amt = d.get("amount", 0)
        print(f"Evaluando doc {doc.id}: '{name}' (${amt:,.0f})")
        if name.strip().lower() in ["mamá", "mama"]:
            print(f" -> Mantener {name}")
        else:
            print(f" -> Eliminando doc corrupto/obsoleto {name} ({doc.id})")
            doc.reference.delete()

    # Asegurar que existan Mamá ($150,000) y Deudas ($205,000)
    establecer_presupuesto_mes(usuario_id, "Mamá", 150000, "2026", "09")
    establecer_presupuesto_mes(usuario_id, "Deudas", 205000, "2026", "09")

    # Limpiar categorías corruptas en /categories si no tienen uso
    cats_ref = uref.collection("categories")
    for cdoc in cats_ref.stream():
        cd = cdoc.to_dict() or {}
        cname = cd.get("nombre", "")
        if any(cname.startswith(p) for p in ["Son 205", "Septiembre.", "Hola, Yerbis", "Necesito Q Edites", "Mamá Deudas,"]):
            print(f"Eliminando categoría corrupta: {cname} ({cdoc.id})")
            cdoc.reference.delete()

    print("\n--- Estado final de presupuestos Septiembre 2026 ---")
    final_items = list(items_ref.stream())
    for fdoc in final_items:
        fd = fdoc.to_dict() or {}
        print(f"• {fd.get('category_name')}: ${fd.get('amount', 0):,.0f}")

if __name__ == "__main__":
    main()
