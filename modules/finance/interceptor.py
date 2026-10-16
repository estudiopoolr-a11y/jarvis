"""Interceptor financiero: detecta consultas financieras por palabras clave
y las resuelve directamente con Firestore antes de que el LLM las alucine.
"""
import re
import logging
import unicodedata
from datetime import datetime

from modules.finance.dashboard import obtener_resumen_dashboard
from modules.finance.categories import listar_categorias
from modules.finance.advisor import (
    calcular_propuesta_presupuesto,
    generar_mensaje_propuesta,
)

logger = logging.getLogger("jarvis.finance.interceptor")


def _normalizar_texto(texto: str) -> str:
    """Normalizar texto: eliminar acentos y convertir a minúsculas para coincidencia robusta."""
    # Normalizar Unicode para separar caracteres acentuados (é -> e + ́)
    nfkd = unicodedata.normalize('NFKD', texto)
    # Eliminar diacríticos (acenta)
    sin_acentos = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    return sin_acentos.lower()

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
    # Categorias
    "categoria", "categorias", "category", "categories",
]


def _detectar_mes_en_texto(texto: str) -> str | None:
    """Extraer un mes YYYY-MM del texto del usuario, o None si no se menciona."""
    texto_lower = _normalizar_texto(texto)

    match = re.search(r"(20\d{2})-(0[1-9]|1[0-2])", texto_lower)
    if match:
        return match.group(0)

    year_match = re.search(r"\b(20\d{2})\b", texto_lower)
    year = int(year_match.group(1)) if year_match else datetime.now().year
    for nombre_mes, num_mes in _MES_ES_POR_NUM.items():
        if re.search(rf"\b{nombre_mes}\b", texto_lower):
            return f"{year:04d}-{num_mes:02d}"

    return None


def _es_consulta_categorias(texto: str) -> bool:
    """Verificar si el texto es una consulta sobre categorías."""
    texto_lower = _normalizar_texto(texto)
    return any(kw in texto_lower for kw in ["categoria", "categorias", "category", "categories"])


def _obtener_respuesta_categorias() -> str:
    """Obtener lista de categorías reales desde Firestore."""
    try:
        categorias = listar_categorias("default")
        if not categorias:
            return "⚠️ No hay categorías configuradas en la base de datos."

        # Agrupar por tipo
        tipos = {}
        for cat in categorias:
            tipo = cat.get("tipo", "variable")
            if tipo not in tipos:
                tipos[tipo] = []
            tipos[tipo].append(cat)

        respuesta = "📊 **Categorías Financieras Reales:**\n\n"

        for tipo, cats in tipos.items():
            tipo_label = "Fijos" if tipo == "fijo" else "Variables"
            respuesta += f"**{tipo_label}:**\n"
            for cat in cats:
                nombre = cat.get("nombre", "Sin nombre")
                icono = cat.get("icono", "")
                respuesta += f"  {icono} {nombre}\n"
            respuesta += "\n"

        respuesta += f"Total: {len(categorias)} categorías"
        return respuesta

    except Exception as e:
        logger.error("Error obteniendo categorías: %s", e)
        return f"⚠️ No se pudieron cargar las categorías: {str(e)[:80]}"


def detectar_e_interactuar_finanzas(texto_usuario: str) -> str | None:
    """Detectar si el mensaje tiene intención financiera y consultar Firestore.

    Retorna la respuesta formateada con datos reales si se detecta una
    consulta financiera; retorna None si no aplica (dejar que el LLM la
    responda).
    """
    texto_lower = _normalizar_texto(texto_usuario)

    # Las peticiones de recomendación deben usar historial, no el resumen del mes destino.
    intenciones_asesoria = (
        "deberia asignar",
        "deberia presupuestar",
        "que presupuesto asignar",
        "presupuesto recomendado",
        "recomiendame un presupuesto",
        "en que gastar",
        "en que ahorrar",
        "en que invertir",
        "cuanto asignar",
        "como distribuir mi ingreso",
    )
    if any(intencion in texto_lower for intencion in intenciones_asesoria):
        mes_destino = _detectar_mes_en_texto(texto_usuario)
        if mes_destino is None:
            mes_destino = datetime.now().strftime("%Y-%m")
        try:
            propuesta = calcular_propuesta_presupuesto(mes_destino)
            return generar_mensaje_propuesta(propuesta)
        except Exception as e:
            logger.exception("No se pudo calcular la propuesta de presupuesto")
            return f"⚠️ No se pudo calcular la propuesta con Firestore: {str(e)[:80]}"

    # Verificar si es una consulta de categorías
    if _es_consulta_categorias(texto_usuario):
        return _obtener_respuesta_categorias()

    # Verificar si alguna palabra clave financiera está presente
    tiene_intencion = any(kw in texto_lower for kw in _KEYWORDS)

    if not tiene_intencion:
        return None

    # Determinar el mes: explícito del usuario o el mes activo por defecto
    mes = _detectar_mes_en_texto(texto_usuario)

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
        datos_cat = resumen.get("datos_por_categoria", [])

        # Construir desglose detallado por categoría
        lineas_cat = []
        for item in sorted(datos_cat, key=lambda x: -x.get("gastado", 0)):
            cat = item.get("categoria", "General")
            gastado = item.get("gastado", 0)
            limite = item.get("limite", 0)
            excedido = item.get("excedido", False)
            linea = f"{cat}: ${gastado:,.0f} COP"
            if limite > 0:
                linea += f" / ${limite:,.0f} COP"
                if excedido:
                    linea += " ⚠️"
            lineas_cat.append(linea)

        categorias_texto = "\n".join(f"  {linea}" for linea in lineas_cat)

        respuesta = f"📊 **Desglose Financiero ({mes_nombre})**\n\n"
        respuesta += f"💵 **Ingresos:** ${ingresos:,.0f} COP\n"
        respuesta += f"📉 **Gastos Totales:** ${gastos:,.0f} COP\n"

        if total_limite > 0:
            respuesta += f"🎯 **Presupuesto:** ${total_limite:,.0f} COP\n"
            respuesta += f"✅ **Disponible:** ${libre:,.0f} COP ({porcentaje:.1f}% usado)\n"

        respuesta += "\n**Gastos por Categoría:**\n"
        respuesta += categorias_texto if categorias_texto else "  (Sin transacciones este mes)"

        if gastos == 0 and total_limite > 0:
            respuesta += "\n\n⚠️ *Este mes aún no tiene transacciones registradas, pero sí tiene presupuesto asignado.*"
        elif gastos == 0 and total_limite == 0:
            respuesta += "\n\nℹ️ *No hay datos para este mes.*"

        return respuesta

    except Exception as e:
        logger.error("Error en interceptor financiero: %s", e)
        return f"⚠️ No se pudo consultar la base de datos: {str(e)[:80]}"
