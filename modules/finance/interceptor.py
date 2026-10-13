"""Interceptor financiero: detecta consultas financieras por palabras clave
y las resuelve directamente con Firestore antes de que el LLM las alucine.
"""
import re
import logging
from datetime import datetime

from modules.finance.dashboard import obtener_resumen_dashboard

logger = logging.getLogger("jarvis.finance.interceptor")

# Meses en español mapeados a su número y código YYYY-MM
_MES_ES_POR_NUM = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Palabras clave que indican intención financiera obligatoria
_KEYWORDS = [
    "presupuesto", "presupuestos",
    "gasto", "gastos", "gasté", "gaste", "gastado", "gastar",
    "balance", "saldo",
    "ingreso", "ingresos", "ingrese", "ingresar",
    "cuánto tengo", "cuanto tengo",
    "debo", "deuda", "deudas",
    "prestamo", "prestamos",  # también "préstamo" con acento
    "dinero", "plata",
    "cuánto cuesta", "cuanto cuesta", "precio", "costo",
    "cobrar", "cobro", "cobré", "cobre",
    "pagar", "pago", "pagué", "pague",
]


def _detectar_mes_en_texto(texto: str) -> str | None:
    """Extraer un mes YYYY-MM del texto del usuario, o None si no se menciona."""
    texto_lower = texto.lower()

    for nombre_mes, num_mes in _MES_ES_POR_NUM.items():
        if nombre_mes in texto_lower:
            # Asumir año 2026 para los datos existentes
            return f"2026-{num_mes:02d}"

    # Buscar formato YYYY-MM explícito (ej. "2026-07", "julio 2026")
    match = re.search(r"(202[4-9])-(0[1-9]|1[0-2])", texto_lower)
    if match:
        return match.group(0)

    return None


def detectar_e_interactuar_finanzas(texto_usuario: str) -> str | None:
    """Detectar si el mensaje tiene intención financiera y consultar Firestore.

    Retorna la respuesta formateada con datos reales si se detecta una
    consulta financiera; retorna None si no aplica (dejar que el LLM la
    responda).
    """
    texto_lower = texto_usuario.lower()

    # Verificar si alguna palabra clave financiera está presente
    tiene_intencion = any(kw in texto_lower for kw in _KEYWORDS)

    if not tiene_intencion:
        return None

    # Determinar el mes: explícito del usuario o el mes activo por defecto
    mes = _detectar_mes_en_texto(texto_usuario)
    if mes is None:
        # El dashboard usa automáticamente el último mes con datos
        mes = "2026-08"  # fallback conocido; el dashboard lo sobrescribe si hay datos más recientes

    try:
        resumen = obtener_resumen_dashboard(mes=mes)

        if resumen.get("status") != "ok":
            return "⚠️ No hay datos financieros disponibles para el periodo consultado."

        mes_nombre = resumen.get("mes", mes)
        total_limite = resumen.get("total_limite", 0)
        gastos = resumen.get("total_gastos", 0)
        ingresos = resumen.get("total_ingresos", 0)
        porcentaje = resumen.get("porcentaje_uso", 0)
        libre = resumen.get("total_libre", 0)

        # Si no hay presupuestos definidos, dar info básica
        if total_limite == 0:
            return (
                f"📊 **Resumen Financiero ({mes_nombre})**\n"
                f"🟢 Ingresos: ${ingresos:,.0f} COP\n"
                f"📉 Gastos: ${gastos:,.0f} COP\n"
                f"💰 Balance neto: ${ingresos - gastos:,.0f} COP\n"
                f"ℹ️ No hay presupuestos configurados para este mes."
            )

        # Formato con uso de presupuesto
        return (
            f"📊 **Datos Financieros ({mes_nombre})**\n"
            f"🟢 Ingresos: ${ingresos:,.0f} COP\n"
            f"📉 Gastos: ${gastos:,.0f} COP\n"
            f"🎯 Uso del presupuesto: {porcentaje:.1f}% "
            f"(${gastos:,.0f} / ${total_limite:,.0f} COP)\n"
            f"✅ Disponible: ${libre:,.0f} COP"
        )

    except Exception as e:
        logger.error("Error en interceptor financiero: %s", e)
        return f"⚠️ No se pudo consultar la base de datos: {str(e)[:80]}"
