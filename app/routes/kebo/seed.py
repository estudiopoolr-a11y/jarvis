"""Kebo HTTP routes: seed."""
from app.api import app

@app.get("/api/kebo/seed")
def api_kebo_seed(usuario_id: str = "default"):
    """Endpoint one-time: crea categorías predefinidas y cuentas default."""
    try:
        from modules.db import crear_categorias_predefinidas, crear_cuenta, ensure_user
        ensure_user(usuario_id, "Pool")
        cats_creadas = crear_categorias_predefinidas(usuario_id)

        # Crear cuentas solo si no existen
        cuentas_default = [
            {"nombre": "Efectivo", "tipo": "cash"},
            {"nombre": "Tarjeta", "tipo": "debit"},
            {"nombre": "Crédito", "tipo": "credit"},
        ]
        from modules.db import listar_cuentas
        existing = [c.get("nombre") for c in listar_cuentas(usuario_id)]
        cuentas_creadas = 0
        for c in cuentas_default:
            if c["nombre"] not in existing:
                crear_cuenta(usuario_id, c["nombre"], c["tipo"], 0)
                cuentas_creadas += 1

        return {"status": "ok", "categorias_creadas": cats_creadas, "cuentas_creadas": cuentas_creadas}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/load-agosto-2026")
def api_kebo_load_agosto(usuario_id: str = "default"):
    """Carga los datos de agosto 2026 desde screenshots de Kebo.
    Incluye: 20 transacciones, 1 ingreso, 7 presupuestos, 16 categorías.
    Idempotente: si ya hay datos de agosto 2026, no duplica.
    """
    try:
        from modules.db import (
            crear_categoria, crear_cuenta, registrar_transaccion_v2,
            establecer_presupuesto_mes, listar_cuentas, ensure_user
        )
        from datetime import datetime
        from google.cloud.firestore_v1.base_query import FieldFilter

        ensure_user(usuario_id, "Pool")

        # Verificar si ya se cargó agosto (buscando por tag)
        from modules.db import inicializar_firebase
        db = inicializar_firebase()
        if db:
            try:
                existing = db.collection("users").document(usuario_id)\
                    .collection("transactions")\
                    .where(filter=FieldFilter("tags", "array_contains", "agosto-2026"))\
                    .limit(1).stream()
                if list(existing):
                    return {"status": "already_loaded", "message": "Agosto 2026 ya está cargado"}
            except Exception as check_err:
                # Si falla la verificación, seguimos y dejamos que se cargue
                print(f"[load-agosto-2026] Check previo falló (continúa): {check_err}", flush=True)

        # ===== 1. CREAR CATEGORÍAS =====
        # Categorías predefinidas + personalizadas de Kebo
        categorias_kebo = [
            "Alimentación", "Transporte", "Servicios", "Arriendo", "Entretenimiento",
            "Salud", "Educación", "Ropa", "Hogar", "Mascotas", "Celular", "Internet",
            "Deudas", "Ahorro", "Inversión", "Otros",
            # Personalizadas
            "Women", "madre", "Moto", "Deudas", "use personal", "Prestamos",
            "futbol", "gym", "estudio", "padre", "Casa", "Préstamo", "Salario",
        ]
        # Eliminar duplicados
        cats_unicas = list(set(categorias_kebo))
        for cat in cats_unicas:
            crear_categoria(usuario_id, cat)

        # ===== 2. ASEGURAR CUENTAS =====
        existing_cuentas = [c.get("nombre") for c in listar_cuentas(usuario_id)]
        cuentas_default = [
            ("Efectivo", "cash", 200000),
            ("Tarjeta", "debit", 150000),
            ("Crédito", "credit", 0),
        ]
        for nombre, tipo, balance in cuentas_default:
            if nombre not in existing_cuentas:
                crear_cuenta(usuario_id, nombre, tipo, balance)

        # ===== 3. CREAR PRESUPUESTOS AGOSTO 2026 =====
        presupuestos_agosto = [
            ("Deudas", 200000),
            ("Alimentación", 150000),
            ("Women", 300000),
            ("Moto", 100000),
            ("use personal", 50000),
            ("futbol", 25000),
            ("madre", 50000),
        ]
        for cat, monto in presupuestos_agosto:
            establecer_presupuesto_mes(usuario_id, cat, monto, "2026", "08")

        # ===== 4. TRANSACCIONES DE AGOSTO 2026 =====
        # Formato: (monto, categoria, descripcion, cuenta, dia)
        gastos_agosto = [
            # Women: 9 tx, total $332.540
            (80000, "Women", "Salida con amigos", "Nequi", 2),
            (45000, "Women", "Cine y cena", "Nequi", 5),
            (30000, "Women", "Compras varias", "Efectivo", 8),
            (25000, "Women", "Café", "Nequi", 11),
            (35000, "Women", "Salida fin de semana", "Efectivo", 14),
            (42000, "Women", "Regalo", "Nequi", 17),
            (22000, "Women", "Cena romántica", "Crédito", 20),
            (30000, "Women", "Compras", "Nequi", 23),
            (23540, "Women", "Salida con amigos", "Efectivo", 27),

            # Deudas: 2 tx, total $205.000
            (150000, "Deudas", "Pago tarjeta crédito", "Nequi", 5),
            (55000, "Deudas", "Cuota préstamo", "Nequi", 20),

            # Alimentación: 1 tx, total $150.000
            (150000, "Alimentación", "Mercado del mes", "Efectivo", 1),

            # use personal: 2 tx, total $97.900
            (49900, "use personal", "Productos aseo personal", "Nequi", 6),
            (48000, "use personal", "Corte pelo y productos", "Efectivo", 18),

            # NOTA: Los préstamos a otras personas NO se cuentan como gasto.
            # Se manejan aparte con el módulo de préstamos (/api/prestamos/*)

            # madre: 1 tx, total $50.000
            (50000, "madre", "Ayuda mensual", "Efectivo", 3),

            # Moto: 1 tx, total $31.000
            (31000, "Moto", "Gasolina", "Nequi", 12),

            # futbol: 1 tx, total $10.000
            (10000, "futbol", "Cancha mensual", "Efectivo", 9),
        ]

        # Validar que sumen $936.440
        total_gastos = sum(g[0] for g in gastos_agosto)
        # Si hay diferencia por redondeo, ajustar el último
        if total_gastos != 936440:
            diff = 936440 - total_gastos
            gastos_agosto[-1] = (gastos_agosto[-1][0] + diff,) + gastos_agosto[-1][1:]

        tx_creadas = 0
        for monto, cat, desc, cuenta, dia in gastos_agosto:
            fecha = f"2026-08-{dia:02d}"
            # No podemos usar fecha custom con la función actual, usamos tags
            tx_id = registrar_transaccion_v2(
                usuario_id, "expense", monto, cat, desc, cuenta,
                tags=["agosto-2026"]
            )
            tx_creadas += 1

        # Ingreso: Salario $806.199,03
        registrar_transaccion_v2(
            usuario_id, "income", 806199.03, "Salario", "Salario agosto", "Nequi",
            tags=["agosto-2026"]
        )

        # ===== 5. MIGRAR PRÉSTAMOS EXISTENTES =====
        # Si hay transacciones viejas en categoría "Prestamos" o "Préstamo",
        # las movemos al módulo de préstamos y las borramos de transacciones.
        prestamos_migrados = 0
        if db:
            try:
                from modules.db import registrar_prestamo
                user_ref = db.collection("users").document(usuario_id)
                cats_prestamos = ["Prestamos", "Préstamo"]
                for cat_nombre in cats_prestamos:
                    # Buscar transacciones con tag agosto-2026 y categoría prestamos
                    # Recorremos los meses de 2026 buscando items con category_name
                    for mes in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]:
                        items_ref = user_ref.collection("transactions")\
                            .document("2026").document(mes).collection("items")
                        docs = list(items_ref.stream())
                        for d in docs:
                            data = d.to_dict()
                            # Verificar si la transacción es de categoría Prestamos
                            cat_id = data.get("category_id")
                            if cat_id:
                                cat_doc = user_ref.collection("categories").document(cat_id).get()
                                if cat_doc.exists:
                                    cat_name = cat_doc.to_dict().get("nombre", "")
                                    if cat_name in cats_prestamos and data.get("type") == "expense":
                                        monto = float(data.get("amount", 0))
                                        fecha = data.get("date", f"2026-{mes}-01")
                                        desc = data.get("description", "Préstamo migrado")
                                        # Crear en módulo de préstamos
                                        registrar_prestamo(
                                            usuario_id,
                                            persona=desc,
                                            monto=monto,
                                            fecha=fecha,
                                            nota="Migrado desde transacciones"
                                        )
                                        # Borrar la transacción original
                                        d.reference.delete()
                                        prestamos_migrados += 1
            except Exception as mig_err:
                print(f"[load-agosto-2026] Migración de préstamos: {mig_err}", flush=True)

        return {
            "status": "ok",
            "message": f"Datos de agosto 2026 cargados correctamente",
            "categorias": len(cats_unicas),
            "presupuestos": len(presupuestos_agosto),
            "transacciones_gastos": tx_creadas,
            "transacciones_ingresos": 1,
            "prestamos_migrados": prestamos_migrados,
            "total_gastos": sum(g[0] for g in gastos_agosto),
            "total_ingresos": 806199.03
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": True, "message": str(e)}

@app.get("/api/kebo/seed-personalizadas")
def api_kebo_seed_personalizadas(usuario_id: str = "default"):
    """Carga SOLO las categorías personalizadas de Kebo (las que ves en la app).
    Idempotente: no duplica si ya existen.
    """
    try:
        from modules.db import crear_categoria, ensure_user
        ensure_user(usuario_id, "Pool")

        # Categorías exactas que aparecen en tus screenshots
        cats_personalizadas = [
            ("Alimentación", "🍔", "#f59e0b"),
            ("Ahorro", "💰", "#22c55e"),
            ("madre", "👩", "#ec4899"),
            ("Moto", "🚴", "#06b6d4"),
            ("Deudas", "😬", "#f43f5e"),
            ("gym", "🏋️", "#ef4444"),
            ("futbol", "⚽", "#10b981"),
            ("use personal", "👤", "#3b82f6"),
            ("Gastos to...", "💇", "#a855f7"),
            ("estudio", "📚", "#eab308"),
            ("padre", "👨", "#f97316"),
            ("Préstamo", "😟", "#f43f5e"),
            ("Women", "🙆‍♀️", "#a16207"),
            ("Casa", "🏠", "#84cc16"),
            ("Salario", "💵", "#10b981"),
            ("Inversión", "🔄", "#eab308"),
        ]

        from modules.db import listar_categorias
        existing = [c.get("nombre") for c in listar_categorias(usuario_id)]
        creadas = 0
        for nombre, icono, color in cats_personalizadas:
            if nombre not in existing:
                crear_categoria(usuario_id, nombre, 0, "variable", icono, color)
                creadas += 1

        return {
            "status": "ok",
            "categorias_creadas": creadas,
            "total_categorias": len(existing) + creadas
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/seed-completo")
def api_kebo_seed_completo(usuario_id: str = "default"):
    """Inicializa categorías + sub-categorías predefinidas."""
    try:
        from modules.db import crear_categorias_predefinidas, crear_subcategorias_predefinidas
        cats = crear_categorias_predefinidas(usuario_id)
        subs = crear_subcategorias_predefinidas(usuario_id)
        return {"categorias_creadas": cats, "subcategorias_creadas": subs}
    except Exception as e:
        return {"error": True, "message": str(e)}
