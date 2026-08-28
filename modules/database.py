# ... existing code ...
def limpiar_y_cargar_datos_dinamicos(usuario_id: str, presupuestos: dict, transacciones: list):
    """Limpia la base de datos y carga masivamente los presupuestos y transacciones indicados por prompt."""
    global db
    if not db: db = inicializar_firebase()
    if not db: return "Error de conexión a Firebase"

    try:
        # 1. Borrar colecciones antiguas
        for col_name in ["finanzas", "presupuestos", "tareas"]:
            docs = db.collection(col_name).stream()
            for doc in docs:
                doc.reference.delete()

        # 2. Cargar Presupuestos
        for cat, limite in presupuestos.items():
            db.collection("presupuestos").document(f"{usuario_id}_{cat.lower()}").set({
                "usuario_id": str(usuario_id),
                "categoria": cat.capitalize(),
                "limite": float(limite)
            })

        # 3. Cargar Transacciones
        for t in transacciones:
            db.collection("finanzas").add({
                "usuario_id": str(usuario_id),
                "tipo": t.get("tipo", "gasto").lower(),
                "monto": float(t.get("monto", 0)),
                "categoria": t.get("categoria", "General").capitalize(),
                "descripcion": t.get("descripcion", "Movimiento registrado"),
                "timestamp": firestore.SERVER_TIMESTAMP
            })

        return f"✅ Base de datos reestructurada. {len(presupuestos)} presupuestos y {len(transacciones)} transacciones cargadas correctamente."
    except Exception as e:
        return f"❌ Error reestructurando base de datos: {e}"
# ... existing code ...