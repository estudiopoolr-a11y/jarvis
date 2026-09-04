"""
Script de backup de datos antes de la migración.
Exporta todas las colecciones a un archivo JSON.
"""
import json
from datetime import datetime
from modules.database import inicializar_firebase
from google.cloud.firestore_v1.base_query import FieldFilter

def backup_todo(usuario_id="default"):
    db = inicializar_firebase()
    if not db:
        print("❌ No se pudo inicializar Firebase")
        return

    backup = {
        "fecha": datetime.now().isoformat(),
        "usuario_id": usuario_id,
        "colecciones": {}
    }

    # Backup de finanzas
    print("📥 Respaldando finanzas...")
    docs = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
    backup["colecciones"]["finanzas"] = [{**d.to_dict(), "_id": d.id} for d in docs]
    print(f"   ✅ {len(backup['colecciones']['finanzas'])} transacciones")

    # Backup de presupuestos
    print("📥 Respaldando presupuestos...")
    docs = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
    backup["colecciones"]["presupuestos"] = [{**d.to_dict(), "_id": d.id} for d in docs]
    print(f"   ✅ {len(backup['colecciones']['presupuestos'])} presupuestos")

    # Backup de tareas
    print("📥 Respaldando tareas...")
    docs = db.collection("tareas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
    backup["colecciones"]["tareas"] = [{**d.to_dict(), "_id": d.id} for d in docs]
    print(f"   ✅ {len(backup['colecciones']['tareas'])} tareas")

    # Backup de metas
    try:
        docs = db.collection("metas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        backup["colecciones"]["metas"] = [{**d.to_dict(), "_id": d.id} for d in docs]
        print(f"   ✅ {len(backup['colecciones']['metas'])} metas")
    except Exception as e:
        print(f"   ⚠️ No se pudo respaldar metas: {e}")

    # Guardar archivo
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n✅ Backup completo guardado en: {filename}")
    print(f"   Total transacciones: {len(backup['colecciones']['finanzas'])}")
    print(f"   Total presupuestos: {len(backup['colecciones']['presupuestos'])}")
    print(f"   Total tareas: {len(backup['colecciones']['tareas'])}")

    return filename

if __name__ == "__main__":
    backup_todo("default")
