"""Kebo HTTP routes: export."""
from app.api import app

@app.get("/api/backup/export")
def api_backup_export(usuario_id: str = "default"):
    """Endpoint para hacer backup de TODOS los datos. Útil para migración."""
    import json
    from datetime import datetime
    from google.cloud.firestore_v1.base_query import FieldFilter
    try:
        from modules.db import inicializar_firebase
        db = inicializar_firebase()
        if not db:
            return {"error": "DB no inicializada"}

        backup = {
            "fecha": datetime.now().isoformat(),
            "usuario_id": usuario_id,
            "colecciones": {}
        }

        # finanzas
        docs = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        backup["colecciones"]["finanzas"] = [{**d.to_dict(), "_id": d.id} for d in docs]

        # presupuestos
        docs = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        backup["colecciones"]["presupuestos"] = [{**d.to_dict(), "_id": d.id} for d in docs]

        # tareas
        docs = db.collection("tareas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        backup["colecciones"]["tareas"] = [{**d.to_dict(), "_id": d.id} for d in docs]

        # metas
        try:
            docs = db.collection("metas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
            backup["colecciones"]["metas"] = [{**d.to_dict(), "_id": d.id} for d in docs]
        except:
            backup["colecciones"]["metas"] = []

        return backup
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/backup/migrate")
def api_backup_migrate(usuario_id: str = "default"):
    """Migra los datos de estructura vieja a nueva estructura Kebo."""
    import json
    from datetime import datetime
    from google.cloud.firestore_v1.base_query import FieldFilter
    from modules.db import (
        ensure_user, crear_cuenta, crear_categoria, registrar_transaccion_v2
    )

    try:
        from modules.db import inicializar_firebase
        db = inicializar_firebase()
        if not db:
            return {"error": "DB no inicializada"}

        stats = {"cuentas_creadas": 0, "categorias_migradas": 0, "transacciones_migradas": 0}

        # 1. Crear usuario y cuentas por defecto
        ensure_user(usuario_id, "Pool")

        # Crear cuentas si no existen
        cuentas_default = [
            {"nombre": "Efectivo", "tipo": "cash", "balance": 0},
            {"nombre": "Tarjeta", "tipo": "debit", "balance": 0},
            {"nombre": "Crédito", "tipo": "credit", "balance": 0},
        ]
        for c in cuentas_default:
            crear_cuenta(usuario_id, c["nombre"], c["tipo"], c["balance"])
            stats["cuentas_creadas"] += 1

        # 2. Migrar presupuestos → categorías
        docs_p = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        categorias_mapeadas = {}
        for doc in docs_p:
            d = doc.to_dict()
            cat_nombre = d.get("categoria", "General")
            limite = float(d.get("limite", 0))
            cat_id = crear_categoria(usuario_id, cat_nombre, limite)
            categorias_mapeadas[cat_nombre] = cat_id
            stats["categorias_migradas"] += 1

        # 3. Migrar transacciones
        docs_t = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        for doc in docs_t:
            d = doc.to_dict()
            monto = float(d.get("monto", 0))
            cat = d.get("categoria", "General")
            tipo_db = "expense" if d.get("tipo") == "gasto" else "income"
            registrar_transaccion_v2(usuario_id, tipo_db, monto, cat, d.get("descripcion", ""), "Efectivo")
            stats["transacciones_migradas"] += 1

        return {"status": "ok", "stats": stats}
    except Exception as e:
        return {"error": True, "message": str(e)}
@app.get("/api/kebo/export")
def api_kebo_export(usuario_id: str = "default"):
    """Descarga JSON completo de todos los datos del usuario."""
    try:
        from modules.db import exportar_json_completo
        import json
        data = exportar_json_completo(usuario_id)
        if not data:
            return {"error": "No se pudo exportar"}
        from fastapi.responses import Response
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=jarvis_export_{usuario_id}.json"
            }
        )
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/export-csv")
def api_kebo_export_csv(usuario_id: str = "default", mes: str = None):
    """Descarga CSV de transacciones del mes."""
    try:
        from modules.db import exportar_csv
        csv_data, filename = exportar_csv(usuario_id, mes)
        if not csv_data:
            return {"error": "No se pudo exportar"}
        from fastapi.responses import Response
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        return {"error": True, "message": str(e)}
