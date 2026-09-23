import os
import sys
from pathlib import Path

from fastapi import File, Form, UploadFile
from fastapi.responses import HTMLResponse

from app.api import USUARIO_PRINCIPAL, ComandoPayload, app
from modules.ai import pensar_respuesta, pensar_respuesta_imagen, procesar_intencion_natural
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos, obtener_tareas_pendientes

# ==================== HISTÓRICO KEBO ====================

@app.post("/api/kebo/load-historico")
def api_kebo_load_historico(payload: dict = None):
    """Carga presupuestos de meses anteriores (mayo, junio, julio 2026) y
    registra los préstamos históricos de Kebo.

    Body opcional: {"meses": ["mayo", "junio", "julio"], "prestamos": true}
    Si no se envía, carga todo.
    """
    try:
        from modules.db import (
            crear_categoria, establecer_presupuesto_mes, registrar_prestamo, ensure_user
        )
        payload = payload or {}
        usuario_id = payload.get("usuario_id", "iphone_user")
        meses = payload.get("meses", ["mayo", "junio", "julio"])
        cargar_prestamos = payload.get("prestamos", True)

        ensure_user(usuario_id, "Pool")

        # Categorías (idempotente, crear_categoria lo maneja)
        cats = [
            "Ahorro", "madre", "padre", "Deudas", "gym", "estudio", "Casa",
            "Alimentación", "Transporte", "Servicios", "Arriendo", "Entretenimiento",
            "Salud", "Educación", "Ropa", "Hogar", "Mascotas", "Celular", "Internet",
            "Inversión", "Otros", "Women", "Moto", "use personal", "Prestamos",
            "Préstamo", "futbol", "Gastos tontos", "Salario",
        ]
        for c in cats:
            crear_categoria(usuario_id, c)

        # Presupuestos por mes (formato: mes -> [(categoria, monto)])
        presupuestos = {
            "mayo": {
                "year": "2026", "month": "05",
                "cats": [
                    ("Deudas", 140000), ("Moto", 170000), ("use personal", 50000),
                    ("Gastos tontos", 20000), ("madre", 185000), ("futbol", 50000),
                    ("gym", 35000), ("Alimentación", 2000),
                ],
            },
            "junio": {
                "year": "2026", "month": "06",
                "cats": [
                    ("gym", 35000), ("madre", 150000), ("padre", 100000),
                    ("Ahorro", 100000), ("use personal", 40000), ("Deudas", 140000),
                    ("Gastos tontos", 40000), ("Prestamos", 20000), ("Moto", 50000),
                ],
            },
            "julio": {
                "year": "2026", "month": "07",
                "cats": [
                    ("Alimentación", 120000), ("Moto", 100000), ("futbol", 50000),
                    ("use personal", 100000), ("Women", 200000), ("Gastos tontos", 100000),
                    ("Prestamos", 100000),
                ],
            },
        }

        resultados = {}
        for mes in meses:
            if mes not in presupuestos:
                continue
            p = presupuestos[mes]
            for cat, monto in p["cats"]:
                establecer_presupuesto_mes(usuario_id, cat, monto, p["year"], p["month"])
            resultados[mes] = {
                "presupuestos_cargados": len(p["cats"]),
                "year": p["year"], "month": p["month"],
            }

        # Préstamos históricos
        prestamos_cargados = 0
        if cargar_prestamos:
            prestamos_historico = [
                # (persona, monto, fecha, nota)
                ("Jhostyn", 40000, "2026-08-24", "Préstamo"),
                ("Mama pañales salo", 20000, "2026-08-24", "Préstamo"),
                ("Brother", 50000, "2026-07-31", "Préstamo"),
                ("Cinemark", 32500, "2026-07-31", "Préstamo"),
                ("Vascula", 50000, "2026-07-31", "Préstamo"),
                ("Brother", 20000, "2026-07-21", "Préstamo"),
                ("Brother", 20000, "2026-07-21", "Préstamo"),
            ]
            for persona, monto, fecha, nota in prestamos_historico:
                pid = registrar_prestamo(usuario_id, persona, monto, fecha, nota)
                if pid:
                    prestamos_cargados += 1

        return {
            "status": "ok",
            "presupuestos": resultados,
            "prestamos_cargados": prestamos_cargados,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": True, "message": str(e)}


@app.get("/api/admin/debug-finanzas")
def api_admin_debug_finanzas(usuario_id: str = "iphone_user"):
    """Debug: ver qué hay en finanzas sin filtros."""
    try:
        from modules.db import inicializar_firebase
        db = inicializar_firebase()
        if not db:
            return {"error": "Firebase no disponible"}

        # Leer TODO finanzas sin filtro
        docs = list(db.collection("finanzas").limit(15).stream())
        results = []
        for d in docs:
            results.append({**d.to_dict(), "_id": d.id})

        return {
            "total": len(results),
            "sample": results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@app.get("/api/admin/audit")
def api_admin_audit(usuario_id: str = "iphone_user"):
    """Escanea toda la base de datos Firebase y devuelve un reporte completo."""
    import traceback
    try:
        from modules.db import inicializar_firebase
        from modules.migration import auditar_firebase
        db = inicializar_firebase()
        if not db:
            return {"error": "Firebase no disponible"}
        return auditar_firebase(db, usuario_id)
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }


@app.get("/api/admin/debug-tx-migration")
def api_admin_debug_tx(usuario_id: str = "iphone_user"):
    """Debug paso a paso de migrar_transacciones_legacy."""
    import traceback
    resultados = {}
    try:
        from modules.db import inicializar_firebase, _get_user_ref
        from modules.migration import _buscar_categoria_id
        db = inicializar_firebase()
        resultados["1_firebase"] = "ok" if db else "FAILED"
        if not db:
            return resultados

        resultados["2_db_type"] = type(db).__name__
        resultados["3_finanzas_count"] = len(list(db.collection("finanzas").stream()))

        # Step: user_ref
        try:
            user_ref = db.collection("users").document(usuario_id)
            resultados["4_user_ref_type"] = type(user_ref).__name__
            resultados["5_user_ref_id"] = user_ref.id
        except Exception as e:
            resultados["4_user_ref"] = f"ERROR: {e}"
            return resultados

        # Step: transactions collection
        try:
            tx_col = user_ref.collection("transactions")
            resultados["6_tx_col_type"] = type(tx_col).__name__
        except Exception as e:
            resultados["6_tx_col"] = f"ERROR: {e}"
            return resultados

        # Step: year document
        try:
            year_doc = tx_col.document("2026")
            resultados["7_year_doc_type"] = type(year_doc).__name__
        except Exception as e:
            resultados["7_year_doc"] = f"ERROR: {e}"
            return resultados

        # Step: periodo document (2026-09) - nueva estructura plana
        try:
            periodo = "2026-09"
            periodo_doc = tx_col.document(periodo)
            resultados["8_periodo_doc_type"] = type(periodo_doc).__name__
            resultados["8_periodo_id"] = periodo_doc.id
        except Exception as e:
            resultados["8_periodo"] = f"ERROR: {e}"
            return resultados

        # Step: items collection (periodo_doc.collection('items') → CollectionReference)
        try:
            items_col = periodo_doc.collection("items")
            resultados["9_items_col_type"] = type(items_col).__name__
        except Exception as e:
            resultados["9_items_col"] = f"ERROR: {e}"
            return resultados

        # Step: create doc
        try:
            new_doc = items_col.document()
            resultados["10_new_doc_type"] = type(new_doc).__name__
            resultados["11_new_doc_id"] = new_doc.id
        except Exception as e:
            resultados["10_new_doc"] = f"ERROR: {e}"
            return resultados

        # Step: set data
        try:
            new_doc.set({
                "type": "income",
                "amount": 1000.0,
                "description": "test debug",
                "legacy_id": "debug_test",
            })
            resultados["12_set"] = "ok"
        except Exception as e:
            resultados["12_set"] = f"ERROR: {e}"

        return resultados
    except Exception as e:
        return {"error_global": str(e), "tb": traceback.format_exc()}


@app.get("/api/admin/debug-migration")
def api_admin_debug_migration(usuario_id: str = "iphone_user"):
    """Debug: prueba cada llamada a Firestore individualmente."""
    import traceback
    resultados = {}

    try:
        from modules.db import inicializar_firebase, _get_user_ref
        db = inicializar_firebase()
        resultados["firebase_init"] = "ok" if db else "FAILED"
        if not db:
            return resultados

        # Test 1: Obtener user_ref
        try:
            db2, user_ref = _get_user_ref(usuario_id)
            resultados["user_ref"] = f"ok - id={user_ref.id if user_ref else 'None'}"
        except Exception as e:
            resultados["user_ref"] = f"ERROR: {traceback.format_exc()}"
            return resultados

        # Test 2: Listar accounts
        try:
            count = sum(1 for _ in user_ref.collection("accounts").stream())
            resultados["accounts"] = f"ok count={count}"
        except Exception as e:
            resultados["accounts"] = f"ERROR: {traceback.format_exc()}"

        # Test 3: Listar categories
        try:
            count = sum(1 for _ in user_ref.collection("categories").stream())
            resultados["categories"] = f"ok count={count}"
        except Exception as e:
            resultados["categories"] = f"ERROR: {traceback.format_exc()}"

        # Test 4: Listar transactions (estructura vieja)
        try:
            all_docs = list(user_ref.collection("transactions").get())
            resultados["transactions_docs"] = f"ok count={len(all_docs)}"
            for d in all_docs:
                resultados[f"tx_{d.id}"] = "exists"
        except Exception as e:
            resultados["transactions_docs"] = f"ERROR: {traceback.format_exc()}"

        # Test 5: Intentar crear transacción
        try:
            from datetime import datetime
            now = datetime.now()
            periodo = f"{now.year}-{now.month:02d}"
            ref = user_ref.collection("transactions").document(periodo).collection("items").document()
            resultados["tx_create_ref"] = f"ok - ref={ref.id}"
        except Exception as e:
            resultados["tx_create_ref"] = f"ERROR: {traceback.format_exc()}"

        return resultados
    except Exception as e:
        return {"error_global": str(e), "tb": traceback.format_exc()}


@app.get("/api/admin/list-tx-paths")
def api_admin_list_tx_paths(usuario_id: str = "iphone_user"):
    """Lista todos los paths en transactions para debug."""
    try:
        from modules.db import inicializar_firebase, _get_user_ref
        db = inicializar_firebase()
        if not db:
            return {"error": "Firebase no disponible"}
        _, user_ref = _get_user_ref(usuario_id)

        # Test idempotency check path directly
        items_ref = user_ref.collection("transactions").document("2026-09").collection("items")
        existing = list(items_ref.limit(10).stream())

        all_tx_docs = list(user_ref.collection("transactions").get())

        return {
            "db_type": type(db).__name__,
            "user_ref_id": user_ref.id,
            "items_ref_id": str(items_ref),
            "existing_count": len(existing),
            "existing_ids": [{"id": e.id, "legacy_id": e.to_dict().get("legacy_id")} for e in existing],
            "tx_collection_docs": [d.id for d in all_tx_docs],
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "tb": traceback.format_exc()}


@app.post("/api/admin/clean-user-data")
def api_admin_clean_user_data(usuario_id: str = Form("iphone_user")):
    """Borra TODOS los datos del usuario para empezar desde cero con estructura limpia.
    IMPORTANTE: Borra tanto documentos como sub-colecciones."""
    try:
        from modules.db import inicializar_firebase
        db = inicializar_firebase()
        if not db:
            return {"error": "Firebase no disponible"}
        user_ref = db.collection("users").document(usuario_id)

        cleaned = {}
        collections_to_clean = ["transactions", "budgets", "categories", "accounts", "goals", "loans", "recurring", "reminders", "exchange_rates"]

        for col_name in collections_to_clean:
            count = 0
            try:
                col = user_ref.collection(col_name)
                # PASO 1: Iterar todos los documentos usando un stream normal
                # Esto captura tanto los docs padre como sus sub-colecciones
                # Estrategia: usar recursive_delete del admin SDK
                from firebase_admin import firestore
                docs = list(col.list_documents())
                for doc in docs:
                    # recursive_delete elimina el doc y todas sus sub-collections
                    try:
                        firestore.client().recursive_delete(doc)
                        count += 1
                    except Exception as e:
                        # Fallback: delete manual
                        try:
                            # Intentar listar sub-docs y eliminarlos
                            for sub_doc in doc.list_documents():
                                try:
                                    for sub_sub in sub_doc.list_documents():
                                        sub_sub.delete()
                                        count += 1
                                except Exception:
                                    pass
                                sub_doc.delete()
                                count += 1
                        except Exception:
                            pass
                        doc.delete()
                        count += 1

                # PASO 2: Buscar sub-colecciones huerfanas (sin doc padre)
                # Esto es cuando un doc padre fue borrado pero su sub-col quedo
                # Como list_documents() no las ve, las buscamos via items directos
                for periodo in ["2026-09", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-10", "2026-11", "2026-12"]:
                    try:
                        items_in_orphaned = list(col.document(periodo).collection("items").list_documents())
                        for it in items_in_orphaned:
                            it.delete()
                            count += 1
                    except Exception:
                        pass
            except Exception as e:
                pass
            cleaned[col_name] = count

        return {"status": "ok", "message": "Todos los datos borrados (incluyendo sub-colecciones)", "cleaned": cleaned}
    except Exception as e:
        import traceback
        return {"error": str(e), "tb": traceback.format_exc()}


@app.post("/api/admin/migrate-all")
def api_admin_migrate_all(usuario_id: str = Form("iphone_user")):
    """Ejecuta la migración completa de datos legacy a estructura users/iphone_user/."""
    import traceback
    import sys
    steps = {}
    try:
        # Step 1: Inicializar Firebase
        from modules.db import inicializar_firebase, ensure_user, crear_categoria
        db = inicializar_firebase()
        if not db:
            return {"error": "Firebase no disponible"}
        steps["1_firebase"] = "ok"

        # Step 2: Ensure user
        ensure_user(usuario_id, "Pool")
        steps["2_ensure_user"] = "ok"

        # Step 3: Importar funciones de migración
        from modules.migration import migrar_transacciones_legacy, migrar_presupuestos_legacy
        from modules.migration import migrar_prestamos_legacy, migrar_metas_legacy
        from modules.migration import migrar_pagos_fijos_legacy, migrar_tareas_legacy
        steps["3_import"] = "ok"

        # Step 4: Categorías base
        cats_base = [
            "Alimentación", "Transporte", "Servicios", "Arriendo", "Entretenimiento",
            "Salud", "Educación", "Ropa", "Hogar", "Mascotas", "Celular", "Internet",
            "Deudas", "Ahorro", "Inversión", "Otros",
            "Women", "madre", "Moto", "use personal", "futbol", "gym",
            "estudio", "padre", "Casa", "Préstamo", "Prestamos",
            "Salario", "General",
        ]
        cats_creadas = 0
        for cat in cats_base:
            if crear_categoria(usuario_id, cat, 0):
                cats_creadas += 1
        steps["4_categorias"] = f"{cats_creadas} creadas"

        # Step 5: Migrar transacciones
        try:
            from modules.migration import migrar_transacciones_legacy as mig_tx
            tx_result = mig_tx(db, usuario_id)
            steps["5_transacciones"] = tx_result
        except Exception as ex:
            steps["5_transacciones"] = f"ERROR: {ex}"

        # Step 6: Migrar presupuestos
        try:
            from modules.migration import migrar_presupuestos_legacy as mig_pres
            pres_result = mig_pres(db, usuario_id)
            steps["6_presupuestos"] = pres_result
        except Exception as ex:
            steps["6_presupuestos"] = f"ERROR: {ex}"

        # Step 7: Préstamos, metas, pagos, tareas
        try:
            from modules.migration import migrar_prestamos_legacy as mig_pr
            steps["7_prestamos"] = mig_pr(db, usuario_id)
        except Exception as ex:
            steps["7_prestamos"] = f"ERROR: {ex}"

        try:
            from modules.migration import migrar_metas_legacy as mig_m
            steps["8_metas"] = mig_m(db, usuario_id)
        except Exception as ex:
            steps["8_metas"] = f"ERROR: {ex}"

        try:
            from modules.migration import migrar_pagos_fijos_legacy as mig_pf
            steps["9_pagos"] = mig_pf(db, usuario_id)
        except Exception as ex:
            steps["9_pagos"] = f"ERROR: {ex}"

        try:
            from modules.migration import migrar_tareas_legacy as mig_t
            steps["10_tareas"] = mig_t(db, usuario_id)
        except Exception as ex:
            steps["10_tareas"] = f"ERROR: {ex}"

        return {"status": "ok", "steps": steps}

    except Exception as e:
        exc_info = sys.exc_info()
        tb_lines = traceback.format_exception(*exc_info)
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "steps_completed": steps,
            "full_traceback": "".join(tb_lines)
        }


@app.get("/api/admin/presupuestos-tabla")
def api_admin_presupuestos_tabla(usuario_id: str = "iphone_user"):
    """Devuelve tabla de presupuestos: categoría, presupuestado, gastado, disponible.
    Formato listo para el widget rediseñado."""
    try:
        from modules.db import (
            inicializar_firebase, listar_categorias, obtener_presupuestos_v2
        )
        from datetime import datetime

        db = inicializar_firebase()
        if not db:
            return {"error": "Firebase no disponible"}

        # Obtener presupuestos del mes actual con gastado
        mes = datetime.now().strftime("%Y-%m")
        presupuestos = obtener_presupuestos_v2(usuario_id, mes)

        # Obtener todas las categorías (incluso sin presupuesto)
        categorias = listar_categorias(usuario_id)

        # Construir tabla completa
        filas = []
        for cat_nombre, datos in sorted(presupuestos.items()):
            limite = datos.get("limite", 0)
            gastado = datos.get("gastado", 0)
            libre = datos.get("libre", 0)
            excedido = datos.get("excedido", libre < 0)

            filas.append({
                "categoria": cat_nombre,
                "presupuestado": limite,
                "gastado": gastado,
                "disponible": libre,
                "excedido": excedido,
                "porcentaje": round((gastado / max(limite, 1)) * 100, 1) if limite > 0 else 0
            })

        # Totales
        total_presupuestado = sum(f["presupuestado"] for f in filas)
        total_gastado = sum(f["gastado"] for f in filas)
        total_disponible = total_presupuestado - total_gastado
        excedidos_count = sum(1 for f in filas if f["excedido"])

        return {
            "mes": mes,
            "filas": filas,
            "totales": {
                "presupuestado": total_presupuestado,
                "gastado": total_gastado,
                "disponible": total_disponible,
                "excedidos_count": excedidos_count
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# ============================================================
# 🆕 ADMIN: RESET + INICIALIZAR BD DESDE CERO
# ============================================================

@app.post("/api/admin/reset-and-init")
def api_admin_reset_and_init(usuario_id: str = Form("iphone_user")):
    """BORRA TODO en users/iphone_user/* y reinicializa desde cero.

    - Borra: accounts, categories, transactions, budgets, loans, goals, recurring, reminders
    - Crea categorías Kebo (todas)
    - Crea cuentas default (Efectivo, Nequi, Crédito)
    - Migra datos legacy: finanzas → transactions, presupuestos → budgets
    """
    import traceback
    steps = {}
    try:
        from modules.db import (
            inicializar_firebase, _get_user_ref, ensure_user,
            crear_cuenta, listar_cuentas
        )
        from firebase_admin import firestore

        db = inicializar_firebase()
        if not db:
            return {"error": "Firebase no disponible"}

        user_ref = db.collection("users").document(usuario_id)

        # Step 1: Ensure user
        ensure_user(usuario_id, "Pool")
        steps["1_user"] = "ok"

        # Step 2: BORRAR todas las sub-colecciones
        sub_collections = [
            "accounts", "categories", "transactions", "budgets",
            "loans", "goals", "recurring", "reminders", "exchange_rates"
        ]
        deleted = {}
        for col_name in sub_collections:
            try:
                docs = list(user_ref.collection(col_name).list_documents())
                count = 0
                for d in docs:
                    # Borrar recursivamente (incluye sub-collections como items/)
                    def recursive_delete(doc_ref, depth=0):
                        nonlocal count
                        if depth > 5:  # Límite de seguridad
                            return
                        # Borrar sub-collections
                        for sub_col in doc_ref.collections():
                            for sub_doc in sub_col.list_documents():
                                recursive_delete(sub_doc, depth + 1)
                        doc_ref.delete()
                        count += 1
                    recursive_delete(d)
                deleted[col_name] = count
            except Exception as e:
                deleted[col_name] = f"ERROR: {e}"
        steps["2_delete"] = deleted

        # Step 3: Crear cuentas default
        cuentas_default = [
            {"nombre": "Efectivo", "tipo": "cash", "balance": 200000},
            {"nombre": "Tarjeta", "tipo": "debit", "balance": 150000},
            {"nombre": "Crédito", "tipo": "credit", "balance": 0},
        ]
        cuentas_creadas = 0
        for c in cuentas_default:
            from modules.db import crear_cuenta
            crear_cuenta(usuario_id, c["nombre"], c["tipo"], c["balance"])
            cuentas_creadas += 1
        steps["3_cuentas"] = f"{cuentas_creadas} cuentas"

        # Step 4: Crear categorías Kebo
        cats_kebo = [
            # Base
            ("Alimentación", 150000), ("Transporte", 100000), ("Servicios", 80000),
            ("Arriendo", 0), ("Entretenimiento", 50000), ("Salud", 30000),
            ("Educación", 50000), ("Ropa", 40000), ("Hogar", 50000),
            ("Mascotas", 20000), ("Celular", 30000), ("Internet", 40000),
            ("Deudas", 200000), ("Ahorro", 0), ("Inversión", 0), ("Otros", 0),
            # Personalizadas Pool
            ("Women", 300000), ("madre", 50000), ("Moto", 100000),
            ("use personal", 50000), ("futbol", 25000), ("gym", 0),
            ("estudio", 0), ("padre", 0), ("Casa", 0),
            ("Préstamo", 0), ("Prestamos", 0), ("Salario", 0), ("General", 0),
        ]
        cats_creadas = 0
        for cat_nombre, cat_budget in cats_kebo:
            from modules.db import crear_categoria
            if crear_categoria(usuario_id, cat_nombre, cat_budget):
                cats_creadas += 1
        steps["4_categorias"] = f"{cats_creadas} categorías creadas"

        # Step 5: Migrar finanzas legacy → transactions
        try:
            from modules.migration import migrar_transacciones_legacy, migrar_presupuestos_legacy
            tx_result = migrar_transacciones_legacy(db, usuario_id)
            steps["5_transacciones"] = tx_result
        except Exception as ex:
            steps["5_transacciones"] = f"ERROR: {ex}"

        # Step 6: Migrar presupuestos legacy → budgets
        try:
            from modules.migration import migrar_presupuestos_legacy
            pres_result = migrar_presupuestos_legacy(db, usuario_id)
            steps["6_presupuestos"] = pres_result
        except Exception as ex:
            steps["6_presupuestos"] = f"ERROR: {ex}"

        # Step 7: Préstamos desde finanzas (categoría Préstamo/Prestamos)
        try:
            from modules.migration import migrar_prestamos_legacy
            pr_result = migrar_prestamos_legacy(db, usuario_id)
            steps["7_prestamos"] = pr_result
        except Exception as ex:
            steps["7_prestamos"] = f"ERROR: {ex}"

        return {"status": "ok", "steps": steps}
    except Exception as e:
        import traceback
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()[-500:]}
