"""Módulo para análisis financiero y exportación de datos."""

from datetime import datetime, timedelta
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from modules.firestore.client import (
    USUARIO_PRINCIPAL,
    _get_user_ref,
    get_db,
    inicializar_firebase,
)
from modules.finance.categories import listar_categorias
from modules.finance.accounts import listar_cuentas
from modules.goals.service import listar_metas_v2
from modules.reminders.service import listar_recurrentes

def obtener_balance_v2(usuario_id="default", mes=None):
    """Obtiene balance del mes actual o especificado."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return 0.0, 0.0, 0.0, []

    if not mes:
        mes = datetime.now().strftime("%Y-%m")
    year, month = mes.split("-")

    try:
        docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
        ingresos = 0.0
        gastos = 0.0
        transacciones = []
        for d in docs:
            t = d.to_dict()
            t["_id"] = d.id
            monto = float(t.get("amount") or t.get("monto", 0))
            tipo = t.get("type") or t.get("tipo", "expense")
            transacciones.append(t)
            if tipo == "income":
                ingresos += monto
            elif tipo == "expense":
                gastos += monto
        return ingresos - gastos, ingresos, gastos, transacciones
    except Exception as e:
        print(f"Error obteniendo balance v2: {e}")
        return 0.0, 0.0, 0.0, []

def obtener_alertas_presupuesto(usuario_id="default"):
    """Genera alertas cuando el gasto supera el 80% del presupuesto."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        mes = datetime.now().strftime("%Y-%m")
        year, month = mes.split("-")

        cats = listar_categorias(usuario_id)
        alertas = []

        docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
        gastos_por_cat = {}
        for d in docs:
            t = d.to_dict()
            tipo = t.get("type") or t.get("tipo", "expense")
            if tipo == "expense":
                cat_id = t.get("category_id")
                monto = float(t.get("amount") or t.get("monto", 0))
                gastos_por_cat[cat_id] = gastos_por_cat.get(cat_id, 0) + monto

        for cat in cats:
            budget = float(cat.get("budget", 0))
            if budget <= 0:
                continue
            gastado = gastos_por_cat.get(cat["_id"], 0)
            pct = (gastado / budget) * 100

            if pct >= 100:
                alertas.append({
                    "tipo": "excedido",
                    "categoria": cat.get("nombre"),
                    "porcentaje": round(pct, 1),
                    "mensaje": f"🚨 {cat.get('nombre')} EXCEDIDO: ${gastado:,.0f} de ${budget:,.0f}"
                })
            elif pct >= 80:
                alertas.append({
                    "tipo": "alerta",
                    "categoria": cat.get("nombre"),
                    "porcentaje": round(pct, 1),
                    "mensaje": f"⚠️ {cat.get('nombre')} al {pct:.0f}%: ${gastado:,.0f} de ${budget:,.0f}"
                })

        return alertas
    except Exception as e:
        print(f"Error generando alertas: {e}")
        return []

def obtener_estadisticas(usuario_id="default", meses=6):
    """Obtiene estadísticas de gastos por categoría y tendencia."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return {}
    try:
        stats = {"por_categoria": {}, "por_mes": {}, "tendencia": []}
        ahora = datetime.now()
        meses_data = {}

        for i in range(meses):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            mes_key = f"{year}-{month}"

            try:
                docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
                ingresos_mes = 0.0
                gastos_mes = 0.0

                for d in docs:
                    t = d.to_dict()
                    monto = float(t.get("amount") or t.get("monto", 0))
                    tipo = t.get("type") or t.get("tipo", "expense")

                    if tipo == "income":
                        ingresos_mes += monto
                    elif tipo == "expense":
                        gastos_mes += monto
                        cat_id = t.get("category_id")
                        if cat_id not in stats["por_categoria"]:
                            stats["por_categoria"][cat_id] = {"total": 0, "nombre": cat_id}
                        stats["por_categoria"][cat_id]["total"] += monto

                meses_data[mes_key] = {"ingresos": ingresos_mes, "gastos": gastos_mes, "balance": ingresos_mes - gastos_mes}
            except Exception:
                pass

        stats["por_mes"] = meses_data
        for mes_key in sorted(meses_data.keys()):
            stats["tendencia"].append({"mes": mes_key, **meses_data[mes_key]})

        cats = listar_categorias(usuario_id)
        cat_nombres = {c["_id"]: c.get("nombre", "Desconocida") for c in cats}
        for cat_id in stats["por_categoria"]:
            if cat_id in cat_nombres:
                stats["por_categoria"][cat_id]["nombre"] = cat_nombres[cat_id]

        return stats
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        return {}

def exportar_json_completo(usuario_id="default"):
    """Exporta todos los datos del usuario a JSON."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        export = {
            "fecha_export": datetime.now().isoformat(),
            "usuario_id": usuario_id,
            "cuentas": listar_cuentas(usuario_id),
            "categorias": listar_categorias(usuario_id),
            "metas": listar_metas_v2(usuario_id),
            "recurrentes": listar_recurrentes(usuario_id),
            "transacciones": {}
        }

        ahora = datetime.now()
        for i in range(12):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            mes_key = f"{year}-{month}"
            try:
                docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
                export["transacciones"][mes_key] = [{**d.to_dict(), "_id": d.id} for d in docs]
            except Exception:
                pass

        return export
    except Exception as e:
        print(f"Error exportando: {e}")
        return None

def exportar_csv(usuario_id="default", mes=None):
    """Exporta transacciones del mes a CSV."""
    if not mes:
        mes = datetime.now().strftime("%Y-%m")
    year, month = mes.split("-")
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None, "DB no disponible"
    try:
        docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
        lineas = ["Fecha,Tipo,Monto,Descripción"]
        for d in docs:
            t = d.to_dict()
            fecha = t.get("fecha", "")
            tipo = t.get("tipo", "")
            monto = t.get("monto", 0)
            desc = t.get("descripcion", "").replace(",", ";").replace("\n", " ")
            lineas.append(f"{fecha},{tipo},{monto},{desc}")
        return "\n".join(lineas), f"export_{mes}.csv"
    except Exception as e:
        return None, f"Error: {e}"
