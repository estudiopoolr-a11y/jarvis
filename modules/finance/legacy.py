"""Firestore domain helpers. Do not import modules.db from here."""
from datetime import datetime, timedelta

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from modules.firestore.client import (
    USUARIO_PRINCIPAL,
    _get_user_ref,
    get_db,
    inicializar_firebase,
)

import json
from modules.firestore.users import ensure_user

# ==================== FUNCIONES LEGACY (para compatibilidad) ====================
# Estas funciones usan la estructura ANTIGUA de Firestore (colecciones planas)

def obtener_balance_financiero(usuario_id: str = "default", mes: str = None):
    """Obtener balance financiero. Lee KEBO (users/{id}/transactions/) con fallback legacy."""
    db = get_db()
    if not db: return 0.0, 0.0, 0.0, []

    # ---- 1) Estructura KEBO ----
    try:
        _, user_ref = _get_user_ref(usuario_id)
        if user_ref:
            # Mapa de categoría (id -> nombre) para traducir category_id a legible
            cat_map = {}
            try:
                for c in user_ref.collection("categories").stream():
                    cd = c.to_dict() or {}
                    cat_map[c.id] = cd.get("nombre") or cd.get("name", "General")
            except Exception:
                pass

            # Listar IDs de mes. Si falla o queda vacío, probar fechas recientes directas.
            if mes:
                y, m = str(mes).split("-")
                meses_docs = [f"{y}-{f'{int(m):02d}'}"]
            else:
                try:
                    meses_docs = [d.id for d in user_ref.collection("transactions").stream()]
                except Exception as e:
                    print(f"Balance kebo: no pude listar transactions: {e}")
                    meses_docs = []
                # Fallback: siempre probar el mes actual y los 5 anteriores
                ahora_m = datetime.now()
                fallback = [f"{ahora_m.year}-{ahora_m.month:02d}"]
                for i in range(1, 6):
                    f = datetime(ahora_m.year, ahora_m.month, 1) - timedelta(days=30 * i)
                    fallback.append(f"{f.year}-{f.month:02d}")
                for f in fallback:
                    if f not in meses_docs:
                        meses_docs.append(f)

            kebo = []
            for month_id in meses_docs:
                try:
                    docs = user_ref.collection("transactions").document(month_id).collection("items").stream()
                except Exception:
                    continue
                for d in docs:
                    t = d.to_dict() or {}
                    t["_id"] = d.id
                    monto = float(t.get("amount")) if t.get("amount") is not None else float(t.get("monto", 0))
                    tipo_kebo = (t.get("type") or t.get("tipo") or "expense")
                    # Traducir a claves legacy esperadas por la app (tipo/monto/categoria)
                    t["tipo"] = "ingreso" if tipo_kebo == "income" else "gasto"
                    t["monto"] = monto
                    t["categoria"] = cat_map.get(t.get("category_id")) or t.get("category_name") or "General"
                    kebo.append(t)

            if kebo:
                ingresos = sum(float(x["monto"]) for x in kebo if x["tipo"] == "ingreso")
                gastos = sum(float(x["monto"]) for x in kebo if x["tipo"] == "gasto")
                return ingresos - gastos, ingresos, gastos, kebo
    except Exception as e:
        print(f"Error balance kebo: {e}")

    # ---- 2) Fallback LEGACY ----
    try:
        filter_criteria = FieldFilter("usuario_id", "==", str(usuario_id))
        if mes:
            filter_criteria = FieldFilter("mes", "==", mes)

        docs = db.collection("finanzas").where(filter=filter_criteria).stream()
        ingresos = 0.0
        gastos = 0.0
        transacciones = []
        for doc in docs:
            t = doc.to_dict()
            monto = float(t.get("monto", 0))
            tipo = t.get("tipo", "gasto")
            transacciones.append(t)
            if tipo == "ingreso":
                ingresos += monto
            else:
                gastos += monto
        return ingresos - gastos, ingresos, gastos, transacciones
    except Exception as e:
        print(f"Error obteniendo balance legacy: {e}")
        return 0.0, 0.0, 0.0, []

def obtener_resumen_presupuestos(usuario_id: str = "default", mes: str = None):
    """Obtener presupuestos. Lee KEBO budgets/{YYYY-MM}/items con fallback legacy."""
    db = get_db()
    if not db: return {}

    # ---- 1) Estructura KEBO ----
    try:
        _, user_ref = _get_user_ref(usuario_id)
        if user_ref:
            # Calcular los IDs de mes candidatos (con y sin cero para tolerar datos viejos)
            if mes:
                y, m = str(mes).split("-")
                candidatos = [f"{y}-{f'{int(m):02d}'}", f"{y}-{int(m)}"]
            else:
                ahora = datetime.now()
                candidatos = [f"{ahora.year}-{ahora.month:02d}", f"{ahora.year}-{ahora.month}"]

            for month_id in candidatos:
                try:
                    items = user_ref.collection("budgets").document(month_id).collection("items").stream()
                except Exception:
                    continue
                presupuestos = {}
                for d in items:
                    data = d.to_dict() or {}
                    presupuestos[data.get("category_name")] = float(data.get("amount", 0))
                if presupuestos:
                    return presupuestos
    except Exception as e:
        print(f"Error presupuestos kebo: {e}")

    # ---- 2) Fallback LEGACY ----
    try:
        filter_criteria = FieldFilter("usuario_id", "==", str(usuario_id))
        p_docs = db.collection("presupuestos").where(filter=filter_criteria).stream()
        presupuestos = {}
        for doc in p_docs:
            d = doc.to_dict()
            presupuestos[d.get("categoria")] = float(d.get("limite", 0))
        return presupuestos
    except Exception as e:
        print(f"Error obteniendo presupuestos legacy: {e}")
        return {}


def deduplicar_gastos(usuario_id, year, month, dry_run=True):
    """Detecta y (si dry_run=False) elimina gastos duplicados del mes.

    Agrupa los gastos (type=expense) de users/{id}/transactions/{YYYY-MM}/items/
    por (category_id, date, amount). Si un grupo tiene más de uno con el mismo
    category_id+monto+date, son duplicados: en modo delete se conserva el primero
    y se borran los demás.

    Devuelve un reporte legible.
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return "⚠️ No se encontró el usuario en la base de datos."

    year = str(year); month = f"{int(month):02d}"
    month_id = f"{year}-{month}"

    try:
        docs = list(user_ref.collection("transactions").document(month_id).collection("items").stream())
    except Exception as e:
        return f"⚠️ Error leyendo transacciones de {month_id}: {e}"

    # Agrupar gastos por clave (category_id, date, amount)
    grupos = {}
    for d in docs:
        t = d.to_dict() or {}
        if (t.get("type") or t.get("tipo")) != "expense":
            continue
        cat = t.get("category_id") or t.get("categoria") or "?"
        fecha = (t.get("date") or "").split("T")[0][:10]
        monto = round(float(t.get("amount") if t.get("amount") is not None else t.get("monto", 0)), 2)
        clave = (cat, fecha, monto)
        grupos.setdefault(clave, []).append((d.id, t))

    duplicados = {k: v for k, v in grupos.items() if len(v) > 1}

    if not duplicados:
        return f"✅ **Sin gastos duplicados en {month_id}.**\n\nTotal gastos: **{sum(1 for d in docs if (d.to_dict() or {}).get('type','expense')=='expense' or (d.to_dict() or {}).get('tipo')=='gasto')}** (vs {len(docs)} transacciones totales)."

    lineas = []
    a_borrar = 0
    for clave, items in duplicados.items():
        cat_id, fecha, monto = clave
        lineas.append(f"**{cat_id}** — {fecha} — ${monto:,.0f}: **{len(items)} copias**")
        if not dry_run:
            # Conservar la primera, borrar el resto
            for extra_id, _ in items[1:]:
                user_ref.collection("transactions").document(month_id).collection("items").document(extra_id).delete()
            a_borrar += len(items) - 1

    modo = "PREVIEW (no borró nada)" if dry_run else f"ELIMINADOS {a_borrar} duplicados"
    cabecera = f"🔍 **DUPLICADOS en {month_id}** — {modo}\n\n"
    return cabecera + "\n".join(lineas) + "\n\n_Usa `!corregir_gastos confirmar` para borrar los duplicados._"

def obtener_tareas_pendientes(usuario_id: str = "default"):
    """Obtener tareas pendientes (legacy)."""
    db = get_db()
    if not db: return []
    try:
        docs = db.collection("tareas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).where(filter=FieldFilter("completada", "==", False)).stream()
        tareas = []
        for doc in docs:
            t = doc.to_dict()
            t["id"] = doc.id
            tareas.append(t)
        return tareas
    except Exception as e:
        print(f"Error obteniendo tareas: {e}")
        return []

def guardar_tarea(usuario_id: str, tarea: str, prioridad: str = "Media", fecha_limite: str = "Pronto"):
    """Guardar tarea (legacy)."""
    db = get_db()
    if not db: return
    try:
        db.collection("tareas").add({
            "usuario_id": str(usuario_id),
            "tarea": tarea,
            "prioridad": prioridad,
            "fecha_limite": fecha_limite,
            "completada": False,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error guardando tarea: {e}")

def marcar_tarea_completada(usuario_id: str, texto_busqueda: str):
    """Marcar tarea como completada (legacy)."""
    db = get_db()
    if not db: return None
    try:
        docs = db.collection("tareas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).where(filter=FieldFilter("completada", "==", False)).stream()
        for doc in docs:
            data = doc.to_dict()
            if texto_busqueda.lower() in data.get("tarea", "").lower():
                doc.reference.update({"completada": True})
                return data.get("tarea")
    except Exception as e:
        print(f"Error completando tarea: {e}")
    return None

def registrar_transaccion(usuario_id: str, tipo: str, monto: float, categoria: str, descripcion: str):
    """Registrar transacción en estructura legacy."""
    db = get_db()
    if not db: return ""
    try:
        from datetime import datetime
        mes_actual = datetime.now().strftime("%Y-%m")
        db.collection("finanzas").add({
            "usuario_id": str(usuario_id),
            "tipo": tipo.lower(),
            "monto": float(monto),
            "categoria": categoria.capitalize(),
            "descripcion": descripcion,
            "mes": mes_actual,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error registrando transacción legacy: {e}")
    return ""

def establecer_presupuesto(usuario_id: str, categoria: str, limite: float):
    """Establecer presupuesto (legacy)."""
    db = get_db()
    if not db: return
    try:
        db.collection("presupuestos").document(f"{usuario_id}_{categoria.lower()}").set({
            "usuario_id": str(usuario_id),
            "categoria": categoria.capitalize(),
            "limite": float(limite)
        })
    except Exception as e:
        print(f"Error estableciendo presupuesto: {e}")

def modificar_presupuesto(usuario_id: str, categoria: str, nuevo_limite: float):
    """Modificar presupuesto (legacy)."""
    db = get_db()
    if not db: return False
    try:
        doc_id = f"{usuario_id}_{categoria.lower()}"
        db.collection("presupuestos").document(doc_id).set({
            "usuario_id": str(usuario_id),
            "categoria": categoria.capitalize(),
            "limite": float(nuevo_limite),
            "actualizado": firestore.SERVER_TIMESTAMP
        }, merge=True)
        return True
    except Exception as e:
        print(f"Error modificando presupuesto: {e}")
        return False

def limpiar_y_cargar_datos_dinamicos(usuario_id: str, presupuestos: dict, transacciones: list):
    """Reestructurar base de datos (legacy)."""
    db = get_db()
    if not db: return "Error de conexión a Firebase"
    try:
        for col_name in ["finanzas", "presupuestos", "tareas"]:
            docs = db.collection(col_name).stream()
            for doc in docs:
                doc.reference.delete()
        for cat, limite in presupuestos.items():
            db.collection("presupuestos").document(f"{usuario_id}_{cat.lower()}").set({
                "usuario_id": str(usuario_id),
                "categoria": cat.capitalize(),
                "limite": float(limite)
            })
        for t in transacciones:
            db.collection("finanzas").add({
                "usuario_id": str(usuario_id),
                "tipo": t.get("tipo", "gasto").lower(),
                "monto": float(t.get("monto", 0)),
                "categoria": t.get("categoria", "General").capitalize(),
                "descripcion": t.get("descripcion", "Movimiento registrado"),
                "timestamp": firestore.SERVER_TIMESTAMP
            })
        return f"✅ Base de datos reestructurada con éxito. {len(presupuestos)} presupuestos y {len(transacciones)} transacciones cargadas."
    except Exception as e:
        return f"❌ Error reestructurando base de datos: {e}"

def obtener_contexto_financiero(usuario_id: str = "default") -> str:
    """Construye contexto financiero etiquetado por periodo para el modelo.

    Los presupuestos son techos mensuales; no representan dinero gastado ni deben
    restarse del neto histórico. Mantener las etiquetas explícitas evita que el
    modelo mezcle liquidez, mes actual e histórico.
    """
    ahora = datetime.now()
    mes_actual = ahora.strftime("%Y-%m")

    # Histórico: conserva la consulta existente, pero queda etiquetado como tal.
    historico_neto, historico_ingresos, historico_gastos, _ = obtener_balance_financiero(usuario_id)

    # Periodo actual: todas las comparaciones de presupuesto usan este mismo mes.
    mes_neto, mes_ingresos, mes_gastos, transacciones_mes = obtener_balance_financiero(
        usuario_id, mes_actual
    )
    presupuestos_mes = obtener_presupuestos_v2(usuario_id, mes_actual)

    cuentas = listar_cuentas(usuario_id)
    liquidez = sum(float(c.get("balance", 0) or 0) for c in cuentas)

    pres_partes = []
    for nombre, info in presupuestos_mes.items():
        limite = float(info.get("limite", 0) or 0)
        gastado = float(info.get("gastado", 0) or 0)
        restante = limite - gastado
        pres_partes.append(
            f"{nombre}:limite=${limite:,.0f},gastado=${gastado:,.0f},restante=${restante:,.0f}"
        )

    movimientos = []
    for transaccion in transacciones_mes[-3:]:
        tipo = transaccion.get("tipo", "?")
        monto = transaccion.get("monto", 0)
        categoria = transaccion.get("categoria", "General")
        movimientos.append(f"{tipo[:1].upper()}:{float(monto or 0):,.0f}@{categoria}")

    tareas = obtener_tareas_pendientes(usuario_id)
    tareas_str = f"{len(tareas)} tareas" if tareas else "sin tareas"
    presupuestos_str = "{}" if not pres_partes else "{" + "; ".join(pres_partes) + "}"
    movimientos_str = "[]" if not movimientos else "[" + ", ".join(movimientos) + "]"

    return (
        f"[JARVIS] LIQUIDEZ_CUENTAS=${liquidez:,.0f} | "
        f"MES_ACTUAL({mes_actual}): Ing=${mes_ingresos:,.0f} "
        f"Gas=${mes_gastos:,.0f} Neto=${mes_neto:,.0f} | "
        f"PRESUPUESTOS_MES={presupuestos_str} | "
        f"HISTORICO: Ing=${historico_ingresos:,.0f} "
        f"Gas=${historico_gastos:,.0f} Neto=${historico_neto:,.0f} | "
        f"MOV_ACTUAL={movimientos_str} | {tareas_str}"
    )

def guardar_mensaje(usuario_id: str, remitente: str, mensaje: str):
    """Guardar mensaje en historial (legacy)."""
    db = get_db()
    if not db: return
    try:
        db.collection("historial_chat").add({
            "usuario_id": str(usuario_id),
            "remitente": remitente,
            "mensaje": mensaje,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error guardando mensaje: {e}")

def guardar_meta(usuario_id: str, nombre: str, monto_objetivo: float, fecha_limite: str = "", categoria: str = "General"):
    """Guardar meta (legacy)."""
    db = get_db()
    if not db: return
    try:
        db.collection("metas").document(f"{usuario_id}_{nombre.lower().replace(' ', '_')[:30]}").set({
            "usuario_id": str(usuario_id),
            "nombre": nombre.title(),
            "monto_objetivo": float(monto_objetivo),
            "monto_actual": 0.0,
            "fecha_limite": fecha_limite,
            "categoria": categoria.capitalize(),
            "completada": False,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error guardando meta: {e}")

def obtener_metas(usuario_id: str = "default"):
    """Obtener metas (legacy)."""
    db = get_db()
    if not db: return []
    try:
        docs = db.collection("metas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        metas = []
        for doc in docs:
            m = doc.to_dict()
            m["id"] = doc.id
            metas.append(m)
        return metas
    except Exception as e:
        print(f"Error obteniendo metas: {e}")
        return []

def actualizar_progreso_meta(usuario_id: str, nombre: str, monto_actual: float):
    """Actualizar progreso meta (legacy)."""
    db = get_db()
    if not db: return False
    try:
        doc_id = f"{usuario_id}_{nombre.lower().replace(' ', '_')[:30]}"
        doc_ref = db.collection("metas").document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            nuevo_monto = float(data.get("monto_actual", 0)) + float(monto_actual)
            completada = nuevo_monto >= float(data.get("monto_objetivo", 0))
            doc_ref.update({"monto_actual": nuevo_monto, "completada": completada})
            return True
    except Exception as e:
        print(f"Error actualizando meta: {e}")
    return False

def eliminar_meta(usuario_id: str, nombre: str):
    """Eliminar meta (legacy)."""
    db = get_db()
    if not db: return False
    try:
        nombre_norm = nombre.lower().strip()
        docs = db.collection("metas").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        for doc in docs:
            data = doc.to_dict()
            if nombre_norm in data.get("nombre", "").lower():
                doc.reference.delete()
                return True
    except Exception as e:
        print(f"Error eliminando meta: {e}")
    return False

def proyectar_meta(meta: dict, capacidad_ahorro_mensual: float) -> dict:
    """Calcular proyección de meta."""
    from datetime import datetime
    objetivo = float(meta.get("monto_objetivo", 0))
    actual = float(meta.get("monto_actual", 0))
    falta = max(0, objetivo - actual)
    meses_restantes = 12
    fecha_limite_str = meta.get("fecha_limite", "")
    if fecha_limite_str:
        try:
            fecha_limite = datetime.strptime(fecha_limite_str, "%Y-%m-%d")
            hoy = datetime.now()
            meses_restantes = max(1, (fecha_limite - hoy).days // 30)
        except (ValueError, TypeError):
            meses_restantes = 12
    ahorro_necesario = falta / meses_restantes if meses_restantes > 0 else falta
    meses_proyectados = falta / capacidad_ahorro_mensual if capacidad_ahorro_mensual > 0 else float('inf')
    atrasado = meses_proyectados > meses_restantes
    return {
        "objetivo": objetivo, "actual": actual, "falta": falta,
        "porcentaje": min(100, (actual / objetivo * 100)) if objetivo > 0 else 0,
        "meses_restantes": meses_restantes, "ahorro_necesario": ahorro_necesario,
        "ahorro_capacidad": capacidad_ahorro_mensual,
        "meses_proyectados": meses_proyectados, "atrasado": atrasado
    }

def guardar_pago_fijo(usuario_id: str, nombre: str, monto: float, dia_mes: int, categoria: str = "General"):
    """Guardar pago fijo (legacy)."""
    db = get_db()
    if not db: return
    try:
        doc_id = f"{usuario_id}_{nombre.lower().replace(' ', '_')[:30]}"
        db.collection("pagos_fijos").document(doc_id).set({
            "usuario_id": str(usuario_id),
            "nombre": nombre.title(),
            "monto": float(monto),
            "dia_mes": int(dia_mes),
            "categoria": categoria.capitalize(),
            "activo": True,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error guardando pago fijo: {e}")

def obtener_pagos_fijos(usuario_id: str = "default"):
    """Obtener pagos fijos (legacy)."""
    db = get_db()
    if not db: return []
    try:
        docs = db.collection("pagos_fijos").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        pagos = []
        for doc in docs:
            p = doc.to_dict()
            p["id"] = doc.id
            pagos.append(p)
        return pagos
    except Exception as e:
        print(f"Error obteniendo pagos fijos: {e}")
        return []

def eliminar_pago_fijo(usuario_id: str, nombre: str):
    """Eliminar pago fijo (legacy)."""
    db = get_db()
    if not db: return False
    try:
        nombre_norm = nombre.lower().strip()
        docs = db.collection("pagos_fijos").where(filter=FieldFilter("usuario_id", "==", str(usuario_id))).stream()
        for doc in docs:
            data = doc.to_dict()
            if nombre_norm in data.get("nombre", "").lower():
                doc.reference.delete()
                return True
    except Exception as e:
        print(f"Error eliminando pago fijo: {e}")
    return False

def guardar_perfil(usuario_id: str, **datos):
    """Guardar perfil (legacy)."""
    db = get_db()
    if not db: return
    try:
        db.collection("perfiles").document(str(usuario_id)).set(datos, merge=True)
    except Exception as e:
        print(f"Error guardando perfil: {e}")

def obtener_perfil(usuario_id: str = "default") -> dict:
    """Obtener perfil (legacy)."""
    db = get_db()
    if not db: return {}
    try:
        doc = db.collection("perfiles").document(str(usuario_id)).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        print(f"Error obteniendo perfil: {e}")
    return {}

