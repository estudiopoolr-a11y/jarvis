import os
import sys
from pathlib import Path

from fastapi import File, Form, UploadFile
from fastapi.responses import HTMLResponse

from app.api import USUARIO_PRINCIPAL, ComandoPayload, app
from modules.ai import pensar_respuesta, pensar_respuesta_imagen, procesar_intencion_natural
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos, obtener_tareas_pendientes

@app.post("/api/comando")
def ejecutar_comando_shortcut(payload: ComandoPayload):
    respuesta = procesar_intencion_natural(payload.texto, payload.usuario_id)
    if not respuesta:
        respuesta = pensar_respuesta(payload.texto)
    return {"status": "ok", "respuesta": respuesta}

@app.get("/api/finanzas/resumen")
def api_finanzas_resumen(usuario_id: str = "default"):
    """API para widget iPhone Scriptable: resumen financiero.

    Lee de la estructura LEGACY top-level ('presupuestos' y 'finanzas') que es
    donde están los datos reales del usuario. Si no encuentra nada ahí, intenta
    con la estructura Kebo nueva (users/{userId}/budgets y /transactions).
    """
    import traceback
    from datetime import datetime
    from google.cloud.firestore_v1.base_query import FieldFilter

    try:
        from modules.db import inicializar_firebase
        db = inicializar_firebase()
        if not db:
            return {"error": True, "message": "DB no inicializada"}

        ahora = datetime.now()
        mes_actual = ahora.strftime("%Y-%m")

        # ============ ESTRATEGIA 1: Colecciones legacy top-level ============
        presupuestos = {}
        ingresos = 0.0
        gastos = 0.0
        gastos_por_categoria = {}

        try:
            # Mapeo de usuario_id: el widget usa 'iphone_user' pero los datos
            # estan guardados con el ID real de Discord ('1536228767180136498').
            # Si el parametro es 'iphone_user' o 'default', buscamos TODOS los
            # datos legacy (porque solo hay un usuario).
            usar_todos = usuario_id in ("iphone_user", "default", None, "")

            if usar_todos:
                docs_pres = db.collection("presupuestos").stream()
                docs_fin = db.collection("finanzas").stream()
            else:
                docs_pres = db.collection("presupuestos").where(
                    filter=FieldFilter("usuario_id", "==", str(usuario_id))
                ).stream()
                docs_fin = db.collection("finanzas").where(
                    filter=FieldFilter("usuario_id", "==", str(usuario_id))
                ).stream()

            for doc in docs_pres:
                d = doc.to_dict()
                cat = d.get("categoria")
                if cat:
                    presupuestos[cat] = float(d.get("limite", 0))

            for t in docs_fin:
                d = t.to_dict()
                monto = float(d.get("monto", 0))
                tipo = d.get("tipo", "gasto")
                cat = d.get("categoria", "General")
                if tipo == "ingreso":
                    ingresos += monto
                else:
                    gastos += monto
                    gastos_por_categoria[cat] = gastos_por_categoria.get(cat, 0) + monto
        except Exception as legacy_err:
            print(f"[resumen] Error leyendo legacy: {legacy_err}", flush=True)

        # ============ ESTRATEGIA 2: Estructura Kebo nueva (si legacy vacío) ============
        if ingresos == 0 and gastos == 0:
            try:
                user_ref = db.collection("users").document(usuario_id)
                cat_map = {}
                for c in user_ref.collection("categories").stream():
                    cdata = c.to_dict()
                    cat_map[c.id] = cdata.get("nombre", "?")

                # Presupuestos Kebo
                for year_doc in user_ref.collection("budgets").list_documents():
                    for month_doc in year_doc.list_documents():
                        for p in month_doc.collection("items").stream():
                            pdata = p.to_dict()
                            cat_name = pdata.get("category_name") or cat_map.get(pdata.get("category_id"), "?")
                            presupuestos[cat_name] = float(pdata.get("amount", 0))

                # Tx Kebo
                for year_doc in user_ref.collection("transactions").list_documents():
                    year_id = year_doc.id
                    for month_doc in year_doc.list_documents():
                        month_id = month_doc.id
                        for t in user_ref.collection("transactions").document(year_id).document(month_id).collection("items").stream():
                            tdata = t.to_dict()
                            monto = float(tdata.get("amount", 0))
                            tipo = tdata.get("type", "expense")
                            cat_id = tdata.get("category_id")
                            cat_name = cat_map.get(cat_id, "Sin categoría")
                            if tipo == "income":
                                ingresos += monto
                            else:
                                gastos += monto
                                gastos_por_categoria[cat_name] = gastos_por_categoria.get(cat_name, 0) + monto
                print(f"[resumen] Kebo ingresos={ingresos}, gastos={gastos}", flush=True)
            except Exception as kebo_err:
                print(f"[resumen] Error leyendo Kebo: {kebo_err}", flush=True)

        balance = ingresos - gastos

        # ============ Construir respuesta ============
        datos_por_categoria = []
        total_limite = 0
        total_gastado = 0
        total_libre = 0

        for categoria, limite in sorted(presupuestos.items()):
            gastado = gastos_por_categoria.get(categoria, 0)
            libre = limite - gastado
            excedido = libre < 0
            total_limite += limite
            total_gastado += gastado
            total_libre += libre

            datos_por_categoria.append({
                "categoria": categoria,
                "limite": round(limite),
                "gastado": round(gastado),
                "libre": round(libre),
                "excedido": excedido
            })

        return {
            "mes": mes_actual,
            "balance": round(balance),
            "ingresos": round(ingresos),
            "gastos": round(gastos),
            "total_limite": round(total_limite),
            "total_gastado": round(total_gastado),
            "total_libre": round(total_libre),
            "porcentaje_uso": round((total_gastado / max(total_limite, 1)) * 100),
            "datos_por_categoria": datos_por_categoria
        }
    except Exception as e:
        return {
            "error": True,
            "tipo_error": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()[:1000]
        }

