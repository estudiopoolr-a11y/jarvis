"""
migration.py - JARVIS Migration Module
=====================================

Migre datos de estructura legacy (top-level) a la estructura Kebo
(users/{userId}/...). Idempotente: seguro ejecutar varias veces.

Estructura legacy:
  - finanzas/        → transactions/{year}/{month}/items/
  - presupuestos/    → budgets/{year}/{month}/items/
  - metas/          → goals/
  - tareas/         → reminders/
  - pagos_fijos/    → recurring/

Estructura nueva:
  users/{userId}/
    ├── accounts/
    ├── categories/
    ├── transactions/{year}/{month}/items/
    ├── budgets/{year}/{month}/items/
    ├── goals/
    ├── loans/
    ├── recurring/
    └── reminders/

Autor: JARVIS AI Assistant
"""

from datetime import datetime


def auditar_firebase(db, usuario_id="default"):
    """Escanea TODA la base de datos y devuelve un reporte."""
    resultado = {
        "legacy": {},
        "nuevo": {},
        "usuarios_en_legacy": [],
        "resumen": {}
    }

    # ===== LEGACY: finanzas =====
    try:
        docs_f = db.collection("finanzas").stream()
        docs_f_list = list(docs_f)
        meses = set()
        total_ingresos = 0
        total_gastos = 0
        for d in docs_f_list:
            data = d.to_dict()
            t = data.get("tipo", "gasto")
            m = float(data.get("monto", 0))
            if t == "ingreso":
                total_ingresos += m
            else:
                total_gastos += m
            # Extraer mes del timestamp
            ts = data.get("timestamp")
            if ts:
                if hasattr(ts, 'strftime'):
                    meses.add(ts.strftime("%Y-%m"))
            # Extraer de campo mes si existe
            mes_field = data.get("mes", "")
            if mes_field:
                meses.add(mes_field)
        resultado["legacy"]["finanzas"] = {
            "count": len(docs_f_list),
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "months": sorted(meses)
        }
    except Exception as e:
        resultado["legacy"]["finanzas"] = {"error": str(e)}

    # ===== LEGACY: presupuestos =====
    try:
        docs_p = list(db.collection("presupuestos").stream())
        cats = {}
        for d in docs_p:
            data = d.to_dict()
            cat = data.get("categoria", "General")
            cats[cat] = float(data.get("limite", 0))
        resultado["legacy"]["presupuestos"] = {
            "count": len(docs_p),
            "categorias": cats,
            "total_limite": sum(cats.values())
        }
    except Exception as e:
        resultado["legacy"]["presupuestos"] = {"error": str(e)}

    # ===== LEGACY: metas =====
    try:
        docs_m = list(db.collection("metas").stream())
        resultado["legacy"]["metas"] = {
            "count": len(docs_m),
            "sample": [d.to_dict().get("nombre", "?") for d in docs_m[:3]]
        }
    except Exception as e:
        resultado["legacy"]["metas"] = {"error": str(e)}

    # ===== LEGACY: tareas =====
    try:
        docs_t = list(db.collection("tareas").stream())
        resultado["legacy"]["tareas"] = {
            "count": len(docs_t)
        }
    except Exception as e:
        resultado["legacy"]["tareas"] = {"error": str(e)}

    # ===== LEGACY: pagos_fijos =====
    try:
        docs_pf = list(db.collection("pagos_fijos").stream())
        resultado["legacy"]["pagos_fijos"] = {
            "count": len(docs_pf)
        }
    except Exception as e:
        resultado["legacy"]["pagos_fijos"] = {"error": str(e)}

    # ===== NUEVO: users/{userId} =====
    user_ref = db.collection("users").document(usuario_id)
    try:
        user_doc = user_ref.get()
        resultado["nuevo"]["user_exists"] = user_doc.exists
    except:
        resultado["nuevo"]["user_exists"] = False

    # Accounts
    try:
        resultado["nuevo"]["accounts"] = {"count": sum(1 for _ in user_ref.collection("accounts").stream())}
    except:
        resultado["nuevo"]["accounts"] = {"count": 0}

    # Categories
    try:
        resultado["nuevo"]["categories"] = {"count": sum(1 for _ in user_ref.collection("categories").stream())}
    except:
        resultado["nuevo"]["categories"] = {"count": 0}

    # Transactions (todos los meses)
    try:
        total_tx = 0
        years = list(user_ref.collection("transactions").list_documents())
        months_per_year = {}
        for year_doc in years:
            year_id = year_doc.id
            months = list(year_doc.list_documents())
            months_per_year[year_id] = [m.id for m in months]
            for month_doc in months:
                total_tx += sum(1 for _ in month_doc.collection("items").stream())
        resultado["nuevo"]["transactions"] = {
            "count": total_tx,
            "years_months": months_per_year
        }
    except Exception as e:
        resultado["nuevo"]["transactions"] = {"count": 0, "error": str(e)}

    # Budgets
    try:
        total_budgets = 0
        years_b = list(user_ref.collection("budgets").list_documents())
        for year_doc in years_b:
            for month_doc in year_doc.list_documents():
                total_budgets += sum(1 for _ in month_doc.collection("items").stream())
        resultado["nuevo"]["budgets"] = {"count": total_budgets}
    except:
        resultado["nuevo"]["budgets"] = {"count": 0}

    # Loans
    try:
        resultado["nuevo"]["loans"] = {"count": sum(1 for _ in user_ref.collection("loans").stream())}
    except:
        resultado["nuevo"]["loans"] = {"count": 0}

    # Goals
    try:
        resultado["nuevo"]["goals"] = {"count": sum(1 for _ in user_ref.collection("goals").stream())}
    except:
        resultado["nuevo"]["goals"] = {"count": 0}

    # Recurring
    try:
        resultado["nuevo"]["recurring"] = {"count": sum(1 for _ in user_ref.collection("recurring").stream())}
    except:
        resultado["nuevo"]["recurring"] = {"count": 0}

    # Resumen
    total_legacy = sum(
        (v.get("count", 0) if isinstance(v, dict) else 0)
        for v in resultado["legacy"].values()
    )
    total_nuevo = sum(
        (v.get("count", 0) if isinstance(v, dict) else 0)
        for v in resultado["nuevo"].values()
        if isinstance(v, dict) and "count" in v
    )
    resultado["resumen"] = {
        "legacy_docs": total_legacy,
        "nuevo_docs": total_nuevo,
        "needs_migration": total_legacy > 0 and resultado["nuevo"]["transactions"].get("count", 0) == 0
    }

    return resultado


def migrar_transacciones_legacy(db, usuario_id="default"):
    """Migra documentos de 'finanzas' a 'transactions/{year}/{month}/items/'."""
    stats = {"leidas": 0, "migradas": 0, "saltadas_prestamo": 0, "errores": 0}
    categoria_prestamos = ["préstamo", "prestamo", "prestamos"]

    # Primero, asegurar que todas las categorías existan
    user_ref = db.collection("users").document(usuario_id)
    # Sin filtro de usuario_id porque las finanzas legacy no tienen ese campo
    # (solo hay un usuario en la BD)
    docs = list(db.collection("finanzas").stream())

    # Crear mapa de categorías
    cat_map = {}
    for d in docs:
        data = d.to_dict()
        cat_nombre = data.get("categoria", "General")
        if cat_nombre and cat_nombre not in cat_map:
            # Buscar o crear categoría
            existing = list(user_ref.collection("categories").where("nombre", "==", cat_nombre).limit(1).stream())
            if existing:
                cat_map[cat_nombre] = existing[0].id
            else:
                new_cat = user_ref.collection("categories").document()
                new_cat.set({
                    "nombre": cat_nombre,
                    "budget": 0,
                    "tipo": "variable",
                    "icono": "📊",
                    "color": "#6b7280",
                })
                cat_map[cat_nombre] = new_cat.id

    for d in docs:
        data = d.to_dict()
        stats["leidas"] += 1

        # Saltar préstamos (no son gastos)
        cat = data.get("categoria", "").lower()
        if cat in categoria_prestamos:
            stats["saltadas_prestamo"] += 1
            continue

        # Extraer fecha
        ts = data.get("timestamp")
        if ts and hasattr(ts, 'strftime'):
            fecha = ts.strftime("%Y-%m-%d")
            year = ts.strftime("%Y")
            month = ts.strftime("%m")
        else:
            # Usar campo 'mes' o fecha actual
            mes_field = data.get("mes", "")
            if mes_field and "-" in mes_field:
                year, month = mes_field.split("-")
                fecha = f"{year}-{month}-01"
            else:
                ahora = datetime.now()
                year = str(ahora.year)
                month = f"{ahora.month:02d}"
                fecha = ahora.strftime("%Y-%m-%d")

        # Verificar si ya existe (idempotencia)
        existing = list(
            user_ref.collection("transactions").document(year).collection(month).collection("items")
            .where("legacy_id", "==", d.id).limit(1).stream()
        )
        if existing:
            continue

        # Mapear tipo
        tipo_db = data.get("tipo", "gasto")
        if tipo_db == "ingreso":
            tipo_kebo = "income"
        else:
            tipo_kebo = "expense"

        # Obtener category_id
        cat_nombre = data.get("categoria", "General")
        cat_id = cat_map.get(cat_nombre)

        # Crear transacción
        try:
            tx_ref = user_ref.collection("transactions").document(year).collection(month).collection("items").document()
            tx_ref.set({
                "type": tipo_kebo,
                "amount": float(data.get("monto", 0)),
                "category_id": cat_id,
                "description": data.get("descripcion", ""),
                "payee": "",
                "status": "cleared",
                "tags": ["legacy"],
                "date": fecha,
                "legacy_id": d.id,  # Para idempotencia
                "created_at": ts if ts else None
            })
            stats["migradas"] += 1
        except Exception as e:
            stats["errores"] += 1
            print(f"[migrar_transacciones] Error: {e}")

    return stats


def migrar_presupuestos_legacy(db, usuario_id="default"):
    """Migra documentos de 'presupuestos' a 'budgets/{year}/{month}/items/'."""
    stats = {"leidos": 0, "migrados": 0, "errores": 0}

    # Sin filtro: presupuestos legacy no tienen usuario_id
    docs = list(db.collection("presupuestos").stream())

    user_ref = db.collection("users").document(usuario_id)
    ahora = datetime.now()
    year = str(ahora.year)
    month = f"{ahora.month:02d}"

    for d in docs:
        data = d.to_dict()
        stats["leidos"] += 1

        cat_nombre = data.get("categoria", "General")
        limite = float(data.get("limite", 0))

        # Buscar category_id
        existing = list(user_ref.collection("categories").where("nombre", "==", cat_nombre).limit(1).stream())
        cat_id = existing[0].id if existing else None

        # Verificar si ya existe
        existing_budget = None
        if cat_id:
            existing_budget = list(
                user_ref.collection("budgets").document(year).collection(month).collection("items")
                .where("category_id", "==", cat_id).limit(1).stream()
            )

        if existing_budget:
            # Actualizar si el nuevo límite es diferente
            existing_budget[0].reference.update({"amount": limite})
            stats["migrados"] += 1
        else:
            try:
                user_ref.collection("budgets").document(year).collection(month).collection("items").document().set({
                    "category_id": cat_id,
                    "category_name": cat_nombre,
                    "amount": limite,
                    "year": year,
                    "month": month,
                    "legacy_id": d.id,
                })
                stats["migrados"] += 1
            except Exception as e:
                stats["errores"] += 1

    return stats


def migrar_prestamos_legacy(db, usuario_id="default"):
    """Migra transacciones legacy con categoría 'Préstamo'/'Prestamos' a la colección loans/."""
    stats = {"encontrados": 0, "migrados": 0, "errores": 0}

    # Sin filtro: finanzas legacy no tienen usuario_id
    docs = list(db.collection("finanzas").stream())

    user_ref = db.collection("users").document(usuario_id)
    categoria_prestamos = ["préstamo", "prestamo", "prestamos"]

    for d in docs:
        data = d.to_dict()
        cat = data.get("categoria", "").lower()

        if cat not in categoria_prestamos:
            continue

        stats["encontrados"] += 1

        # Verificar si ya migrado
        existing = list(user_ref.collection("loans").where("legacy_id", "==", d.id).limit(1).stream())
        if existing:
            continue

        ts = data.get("timestamp")
        fecha = ts.strftime("%Y-%m-%d") if ts and hasattr(ts, 'strftime') else datetime.now().strftime("%Y-%m-%d")

        try:
            loan_ref = user_ref.collection("loans").document()
            loan_ref.set({
                "persona": data.get("descripcion", "Préstamo migrado"),
                "monto_original": float(data.get("monto", 0)),
                "monto_pagado": 0.0,
                "monto_pendiente": float(data.get("monto", 0)),
                "fecha": fecha,
                "nota": f"Migrado de finanzas/ (ID legacy: {d.id})",
                "status": "pendiente",
                "pagos": [],
                "legacy_id": d.id,
                "created_at": ts if ts else None,
            })
            stats["migrados"] += 1
        except Exception as e:
            stats["errores"] += 1

    return stats


def migrar_metas_legacy(db, usuario_id="default"):
    """Migra metas legacy a goals/."""
    stats = {"leidas": 0, "migradas": 0, "errores": 0}

    # Sin filtro
    docs = list(db.collection("metas").stream())

    user_ref = db.collection("users").document(usuario_id)

    for d in docs:
        data = d.to_dict()
        stats["leidas"] += 1

        existing = list(user_ref.collection("goals").where("legacy_id", "==", d.id).limit(1).stream())
        if existing:
            continue

        try:
            goal_ref = user_ref.collection("goals").document()
            goal_ref.set({
                "nombre": data.get("nombre", "Meta"),
                "monto_objetivo": float(data.get("monto_objetivo", 0)),
                "current_amount": float(data.get("monto_actual", 0)),
                "fecha_limite": data.get("fecha_limite", ""),
                "categoria": data.get("categoria", ""),
                "completada": data.get("completada", False),
                "legacy_id": d.id,
                "created_at": data.get("timestamp"),
            })
            stats["migradas"] += 1
        except Exception as e:
            stats["errores"] += 1

    return stats


def migrar_pagos_fijos_legacy(db, usuario_id="default"):
    """Migra pagos_fijos legacy a recurring/."""
    stats = {"leidos": 0, "migrados": 0, "errores": 0}

    # Sin filtro
    docs = list(db.collection("pagos_fijos").stream())

    user_ref = db.collection("users").document(usuario_id)

    for d in docs:
        data = d.to_dict()
        stats["leidos"] += 1

        existing = list(user_ref.collection("recurring").where("legacy_id", "==", d.id).limit(1).stream())
        if existing:
            continue

        # Buscar categoría
        cat_nombre = data.get("categoria", "General")
        existing_cat = list(user_ref.collection("categories").where("nombre", "==", cat_nombre).limit(1).stream())
        cat_id = existing_cat[0].id if existing_cat else None

        try:
            rec_ref = user_ref.collection("recurring").document()
            rec_ref.set({
                "nombre": data.get("nombre", "Pago fijo"),
                "monto": float(data.get("monto", 0)),
                "frecuencia": "monthly",
                "dia": int(data.get("dia_mes", 1)),
                "category_id": cat_id,
                "activo": data.get("activo", True),
                "legacy_id": d.id,
                "created_at": data.get("timestamp"),
            })
            stats["migrados"] += 1
        except Exception as e:
            stats["errores"] += 1

    return stats


def migrar_tareas_legacy(db, usuario_id="default"):
    """Migra tareas legacy a reminders/."""
    stats = {"leidas": 0, "migradas": 0, "errores": 0}

    # Sin filtro
    docs = list(db.collection("tareas").stream())

    user_ref = db.collection("users").document(usuario_id)

    for d in docs:
        data = d.to_dict()
        stats["leidas"] += 1

        existing = list(user_ref.collection("reminders").where("legacy_id", "==", d.id).limit(1).stream())
        if existing:
            continue

        try:
            ts = data.get("timestamp")
            dia = 1
            if ts and hasattr(ts, 'strftime'):
                dia = ts.day

            rem_ref = user_ref.collection("reminders").document()
            rem_ref.set({
                "text": data.get("tarea", ""),
                "day": dia,
                "month": f"{datetime.now().month:02d}",
                "year": str(datetime.now().year),
                "prioridad": data.get("prioridad", ""),
                "fecha_limite": data.get("fecha_limite", ""),
                "done": False,
                "legacy_id": d.id,
                "created_at": ts,
            })
            stats["migradas"] += 1
        except Exception as e:
            stats["errores"] += 1

    return stats


def migrar_todo(usuario_id="default"):
    """Ejecuta toda la migración en orden. Retorna stats consolidado."""
    from modules.database import inicializar_firebase, ensure_user, crear_categoria

    db = inicializar_firebase()
    if not db:
        return {"error": "Firebase no disponible"}

    ensure_user(usuario_id, "Pool")

    # 1. Crear categorías base (para que las transacciones tengan references)
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

    resultado = {
        "categorias_base_creadas": cats_creadas,
        "transacciones": migrar_transacciones_legacy(db, usuario_id),
        "presupuestos": migrar_presupuestos_legacy(db, usuario_id),
        "prestamos": migrar_prestamos_legacy(db, usuario_id),
        "metas": migrar_metas_legacy(db, usuario_id),
        "pagos_fijos": migrar_pagos_fijos_legacy(db, usuario_id),
        "tareas": migrar_tareas_legacy(db, usuario_id),
    }

    total_migradas = (
        resultado["transacciones"].get("migradas", 0) +
        resultado["presupuestos"].get("migrados", 0) +
        resultado["prestamos"].get("migrados", 0) +
        resultado["metas"].get("migradas", 0) +
        resultado["pagos_fijos"].get("migrados", 0) +
        resultado["tareas"].get("migradas", 0)
    )

    resultado["total_migrado"] = total_migradas
    resultado["status"] = "ok"

    return resultado
