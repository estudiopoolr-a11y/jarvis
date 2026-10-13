"""Live financial aggregates shared by the dashboard and widget APIs."""
from datetime import datetime
import logging
from typing import Any

from modules.firestore.client import get_db

logger = logging.getLogger("jarvis.finance.dashboard")

_MONTH_NAMES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


def _amount(data: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = data.get(key)
        if value is not None:
            return float(value)
    return 0.0


def obtener_resumen_dashboard(
    _usuario_id: str = "default", mes: str | None = None
) -> dict[str, Any]:
    """Load monthly aggregates from the current root-collection Firestore schema."""
    del _usuario_id
    mes_actual = mes or datetime.now().strftime("%Y-%m")
    fecha_mes = datetime.strptime(mes_actual, "%Y-%m")
    mes_actual = fecha_mes.strftime("%Y-%m")

    db = get_db()
    if db is None:
        raise RuntimeError("Firebase Firestore no está disponible")

    categorias = {}
    categorias_data = {}
    for doc in db.collection("categories").stream():
        data = doc.to_dict() or {}
        categorias_data[doc.id] = data
        categorias[doc.id] = data.get("nombre") or data.get("name") or doc.id

    ingresos = 0.0
    gastos = 0.0
    gastos_por_categoria = {}
    transacciones = db.collection("transactions").document(mes_actual).collection("items").stream()
    for doc in transacciones:
        data = doc.to_dict() or {}
        tipo = str(data.get("type") or data.get("tipo") or "expense").strip().lower()
        monto = _amount(data, "amount", "monto")
        categoria = (
            data.get("category_name")
            or data.get("categoria")
            or categorias.get(data.get("category_id"))
            or "General"
        )

        if tipo in {"income", "ingreso"}:
            ingresos += monto
        elif tipo in {"expense", "gasto"}:
            gastos += monto
            gastos_por_categoria[categoria] = gastos_por_categoria.get(categoria, 0.0) + monto
        else:
            logger.warning("Tipo de transacción desconocido (%s) en %s", tipo, doc.id)

    presupuestos_por_categoria = {}
    budget_docs = db.collection("budgets").document(mes_actual).collection("items").stream()
    for doc in budget_docs:
        data = doc.to_dict() or {}
        categoria = (
            data.get("category_name")
            or data.get("categoria")
            or categorias.get(data.get("category_id"))
        )
        if categoria:
            presupuestos_por_categoria[categoria] = _amount(data, "amount", "limite")

    if not presupuestos_por_categoria:
        for categoria_id, category_data in categorias_data.items():
            limite = _amount(category_data, "budget", "limite")
            if limite > 0:
                nombre = category_data.get("nombre") or category_data.get("name") or categoria_id
                presupuestos_por_categoria[nombre] = limite

    presupuestos = []
    datos_por_categoria = []
    total_limite = 0.0
    for categoria, limite in sorted(presupuestos_por_categoria.items()):
        gastado = gastos_por_categoria.get(categoria, 0.0)
        libre = limite - gastado
        total_limite += limite
        fila = {
            "categoria": categoria,
            "limite": round(limite),
            "gastado": round(gastado),
            "libre": round(libre),
            "excedido": libre < 0,
        }
        presupuestos.append(fila)
        datos_por_categoria.append(fila)

    cuentas = []
    balance_cuentas = 0.0
    for doc in db.collection("accounts").stream():
        data = doc.to_dict() or {}
        balance = _amount(data, "balance", "saldo")
        cuentas.append({
            "id": doc.id,
            "nombre": data.get("nombre") or data.get("name") or "Cuenta sin nombre",
            "disponible": balance,
            "balance": balance,
        })
        balance_cuentas += balance

    porcentaje_uso = gastos / total_limite * 100 if total_limite > 0 else 0.0
    total_libre = sum(item["libre"] for item in datos_por_categoria)
    return {
        "status": "ok",
        "mes": f"{_MONTH_NAMES[fecha_mes.month - 1]} {fecha_mes.year}",
        "balance": round(ingresos - gastos),
        "balance_cuentas": round(balance_cuentas),
        "total_balance_cuentas": round(balance_cuentas),
        "balance_total": round(balance_cuentas),
        "ingresos": round(ingresos),
        "total_ingresos": round(ingresos),
        "gastos": round(gastos),
        "total_gastos": round(gastos),
        "gastos_mes": round(gastos),
        "total_limite": round(total_limite),
        "presupuesto_mes": round(total_limite),
        "total_gastado": round(gastos),
        "total_libre": round(total_libre),
        "porcentaje_uso": round(porcentaje_uso, 2),
        "porcentaje_usado": round(porcentaje_uso, 2),
        "porcentaje": round(porcentaje_uso, 2),
        "comparativa_texto": f"{porcentaje_uso:.1f}% del límite mes",
        "alerta": porcentaje_uso > 85,
        "mensaje": "JARVIS Finanzas OK",
        "datos_por_categoria": datos_por_categoria,
        "presupuestos": presupuestos,
        "cuentas": cuentas,
        "gastos_por_categoria": gastos_por_categoria,
    }
