"""Kebo HTTP routes: transactions."""
from app.api import app

@app.get("/api/kebo/transacciones")
def api_kebo_transacciones(usuario_id: str = "default", limite: int = 20):
    """API para widget: últimas transacciones."""
    try:
        from modules.db import listar_transacciones_recientes
        transacciones = listar_transacciones_recientes(usuario_id, limite)
        return {"transacciones": transacciones}
    except Exception as e:
        return {"error": True, "message": str(e)}

@app.get("/api/kebo/buscar")
def api_kebo_buscar(usuario_id: str = "default", texto: str = "", categoria: str = "",
                    cuenta: str = "", status: str = "", fecha_desde: str = "",
                    fecha_hasta: str = "", tipo: str = ""):
    """Búsqueda avanzada de transacciones."""
    try:
        from modules.db import buscar_transacciones
        resultados = buscar_transacciones(
            usuario_id,
            texto=texto, categoria=categoria, cuenta=cuenta,
            status=status, fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta, tipo=tipo
        )
        return {"total": len(resultados), "transacciones": resultados}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/futuras")
def api_kebo_futuras(usuario_id: str = "default"):
    """Lista transacciones programadas (futuras)."""
    try:
        from modules.db import listar_transacciones_futuras, ejecutar_transacciones_futuras
        # Ejecutar las que ya tocaron
        ejecutadas = ejecutar_transacciones_futuras(usuario_id)
        futuras = listar_transacciones_futuras(usuario_id)
        return {"ejecutadas": ejecutadas, "pendientes": futuras}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/sugerencias")
def api_kebo_sugerencias(usuario_id: str = "default", prefijo: str = ""):
    """Sugerencias de payee y categoría basadas en historial."""
    try:
        from modules.db import obtener_sugerencias_payee, obtener_sugerencias_categoria
        return {
            "payees": obtener_sugerencias_payee(usuario_id, prefijo) if prefijo else [],
            "categorias": obtener_sugerencias_categoria(usuario_id, prefijo) if prefijo else []
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


# Alias para compatibilidad


@app.get("/api/finanzas/debug")
def api_finanzas_debug(usuario_id: str = "default"):
    """Endpoint debug: muestra 1 muestra de cada coleccion."""
    try:
        from modules.db import inicializar_firebase
        from google.cloud.firestore_v1.base_query import FieldFilter
        db = inicializar_firebase()
        if not db:
            return {"error": "DB no inicializada"}

        # 1 presupuesto
        docs_p = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", usuario_id)).limit(2).stream()
        presupuesto_sample = [d.to_dict() for d in docs_p]

        # 2 finanzas
        docs_f = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).limit(3).stream()
        finanzas_sample = [d.to_dict() for d in docs_f]

        return {
            "presupuesto_sample": presupuesto_sample,
            "finanzas_sample": finanzas_sample,
            "num_presupuestos": len(presupuesto_sample),
            "num_finanzas": len(finanzas_sample)
        }
    except Exception as e:
        return {"error": str(e)}
