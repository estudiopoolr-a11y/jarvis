"""Live financial aggregates shared by the dashboard and widget APIs."""
from datetime import datetime, timedelta
import logging
import unicodedata
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


def _es_mes_valido(valor: str) -> bool:
    """Validar que un ID de documento tenga formato de mes YYYY-MM."""
    try:
        datetime.strptime(valor, "%Y-%m")
    except (ValueError, TypeError):
        return False
    return True


def _normalizar_categoria(texto: str) -> str:
    """Normalizar nombre de categoria: minusculas, sin acentos y sin espacios extra.

    Esto permite que los datos escritos por el seed coincidan con lo que lee
    la app real (que suele mandar texto normalizado por el procesador NLP). #
    """
    if not texto:
        return ""
    base = unicodedata.normalize("NFD", str(texto).strip())
    base = "".join(
        caracter
        for caracter in base
        if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(base.lower().split())


def _meses_candidatos(db, mes_del_sistema: str, ventana: int = 24) -> list[str]:
    """Construir la lista de meses (YYYY-MM) que pueden contener transacciones.

    Se combinan dos fuentes porque el esquema actual crea los documentos
    `transactions/{YYYY-MM}` de forma implícita (al escribir la subcolección
    `items` no existe un documento padre que se pueda listar):

    1. Los documentos raíz de `transactions` que tengan formato de mes. #
    2. Una ventana hacia atrás desde el mes del sistema. #
    """
    candidatos = set()
    try:
        for doc in db.collection("transactions").stream():
            if _es_mes_valido(doc.id):
                candidatos.add(doc.id)
    except Exception:  # La colección puede no existir todavía. #
        logger.debug("No se pudo listar la raíz de transactions")

    fecha = datetime.strptime(mes_del_sistema, "%Y-%m")
    for _ in range(ventana):
        candidatos.add(fecha.strftime("%Y-%m"))
        # Retroceder un mes sin depender de librerías externas. #
        fecha = (fecha.replace(day=1) - timedelta(days=1)).replace(day=1)
    return sorted(candidatos)


def obtener_mes_activo_por_defecto(db) -> str:
    """Devolver el mes (YYYY-MM) más reciente con transacciones registradas.

    El dashboard no puede depender del mes del sistema porque los datos
    financieros se cargan de forma histórica y el mes en curso suele estar
    vacío. Se inspeccionan los meses candidatos de más nuevo a más antiguo y
    se devuelve el primero con items; si no hay datos se usa el mes actual. #
    """
    mes_del_sistema = datetime.now().strftime("%Y-%m")
    try:
        for mes in reversed(_meses_candidatos(db, mes_del_sistema)):
            items = (
                db.collection("transactions")
                .document(mes)
                .collection("items")
                .limit(1)
                .get()
            )
            if items:
                return mes
    except Exception:  # Firestore indisponible: no romper el resumen. #
        logger.exception("No se pudo resolver el mes activo por defecto")
    return mes_del_sistema


def obtener_resumen_dashboard(
    _usuario_id: str = "default", mes: str | None = None
) -> dict[str, Any]:
    """Load monthly aggregates from the current root-collection Firestore schema."""
    del _usuario_id

    db = get_db()
    if db is None:
        raise RuntimeError("Firebase Firestore no está disponible")

    # Sin mes explícito se usa el último mes con datos reales. #
    mes_actual = mes or obtener_mes_activo_por_defecto(db)
    fecha_mes = datetime.strptime(mes_actual, "%Y-%m")
    mes_actual = fecha_mes.strftime("%Y-%m")

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
            gastos_por_categoria[_normalizar_categoria(categoria)] = gastos_por_categoria.get(_normalizar_categoria(categoria), 0.0) + monto
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
            key = _normalizar_categoria(categoria)
            # Solo conservar el limite si tiene un valor real asignado.
            # Los documentos auto-generados sin 'limite'/'amount' aportan 0 y
            # no deben anular los limites semillados con valores validos. #
            valor = _amount(data, "amount", "limite")
            if valor > 0:
                presupuestos_por_categoria[key] = valor

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
