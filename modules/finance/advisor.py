"""Historical budget recommendations based on real Firestore aggregates."""
import logging
import re
import unicodedata
from datetime import datetime
from typing import Any

from modules.finance.dashboard import obtener_resumen_dashboard

logger = logging.getLogger("jarvis.finance.advisor")

_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
_MONTH_NAMES = tuple(_MONTHS)


def _normalize_text(text: str) -> str:
    """Normalize Spanish month names for parsing."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    ).lower()


def _month_id(mes_destino: str) -> str:
    """Parse a YYYY-MM value or Spanish month name into a valid month ID."""
    normalized = _normalize_text(mes_destino)
    explicit = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", normalized)
    if explicit:
        return explicit.group(0)

    month_number = next(
        (
            number
            for name, number in _MONTHS.items()
            if re.search(rf"\b{name}\b", normalized)
        ),
        None,
    )
    if month_number is None:
        raise ValueError(f"Mes de destino no reconocido: {mes_destino}")

    year_match = re.search(r"\b(20\d{2})\b", normalized)
    year = int(year_match.group(1)) if year_match else datetime.now().year
    return f"{year:04d}-{month_number:02d}"


def _previous_month(month_id: str) -> str:
    """Return the calendar month immediately before a YYYY-MM month."""
    date = datetime.strptime(month_id, "%Y-%m")
    if date.month == 1:
        return f"{date.year - 1:04d}-12"
    return f"{date.year:04d}-{date.month - 1:02d}"


def _month_label(month_id: str) -> str:
    date = datetime.strptime(month_id, "%Y-%m")
    return f"{_MONTH_NAMES[date.month - 1].capitalize()} {date.year}"


def calcular_propuesta_presupuesto(mes_destino: str) -> dict[str, Any]:
    """Build a monthly budget proposal from up to four active prior months.

    Empty months are skipped; no default income or synthetic financial values
    are introduced when Firestore has no usable history.
    """
    destino_id = _month_id(mes_destino)
    cursor = _previous_month(destino_id)
    meses_historial: list[str] = []
    ingresos_positivos: list[float] = []
    gastos_por_categoria: dict[str, float] = {}

    for _ in range(12):
        resumen = obtener_resumen_dashboard("default", mes=cursor)
        if resumen.get("status") != "ok":
            raise RuntimeError(f"No se pudo cargar el resumen real de {cursor}")

        ingreso = float(resumen.get("total_ingresos", resumen.get("ingresos", 0)))
        gasto_mes = float(resumen.get("total_gastos", resumen.get("gastos", 0)))
        if ingreso > 0 or gasto_mes > 0:
            meses_historial.append(cursor)
            if ingreso > 0:
                ingresos_positivos.append(ingreso)
            for categoria, monto in (resumen.get("gastos_por_categoria") or {}).items():
                gastos_por_categoria[categoria] = (
                    gastos_por_categoria.get(categoria, 0.0) + float(monto)
                )
            if len(meses_historial) == 4:
                break
        cursor = _previous_month(cursor)

    if not meses_historial:
        return {
            "status": "sin_historial",
            "mes_destino": _month_label(destino_id),
            "meses_historial": [],
        }
    if not ingresos_positivos:
        return {
            "status": "sin_historial_ingresos",
            "mes_destino": _month_label(destino_id),
            "meses_historial": meses_historial,
        }

    ingreso_proyectado = (
        sum(ingresos_positivos) / len(ingresos_positivos)
        if ingresos_positivos
        else 0.0
    )
    cantidad_meses = len(meses_historial)
    topes_sugeridos = {
        categoria: round(total / cantidad_meses, 2)
        for categoria, total in sorted(gastos_por_categoria.items())
    }
    total_gastos_sugeridos = round(sum(topes_sugeridos.values()), 2)
    ahorro_inversion_sugerido = round(
        max(0.0, ingreso_proyectado - total_gastos_sugeridos), 2
    )

    logger.info(
        "Propuesta de presupuesto para %s calculada con meses reales: %s",
        destino_id,
        meses_historial,
    )
    return {
        "status": "ok",
        "mes_destino": _month_label(destino_id),
        "meses_historial": meses_historial,
        "ingreso_proyectado": round(ingreso_proyectado, 2),
        "topes_sugeridos": topes_sugeridos,
        "total_gastos_sugeridos": total_gastos_sugeridos,
        "ahorro_inversion_sugerido": ahorro_inversion_sugerido,
        "recomendacion": (
            "Como guía general, podrías distribuir el excedente entre un fondo "
            "de emergencia y ahorro/inversión diversificada. Una división 50/50 "
            "es solo ilustrativa: prioriza deudas y considera tu tolerancia al "
            "riesgo antes de invertir."
        ),
    }


def generar_mensaje_propuesta(propuesta: dict[str, Any]) -> str:
    """Format a real-data proposal for Telegram."""
    if propuesta.get("status") == "sin_historial":
        return (
            f"ℹ️ No puedo proponer un presupuesto para "
            f"{propuesta['mes_destino']}: Firestore no tiene meses anteriores "
            "con ingresos o gastos registrados para calcular un promedio."
        )
    if propuesta.get("status") == "sin_historial_ingresos":
        meses = ", ".join(
            _month_label(month_id) for month_id in propuesta["meses_historial"]
        )
        return (
            f"ℹ️ Encontré gastos históricos ({meses}), pero no ingresos "
            f"registrados para proyectar {propuesta['mes_destino']}. No voy a "
            "inventar un ingreso ni sugerir un presupuesto basado en uno."
        )

    meses = ", ".join(
        _month_label(month_id) for month_id in propuesta["meses_historial"]
    )
    mensaje = (
        f"💡 **Propuesta de Presupuesto para {propuesta['mes_destino']}**\n\n"
        f"📚 **Historial real usado:** {meses}\n"
        f"💵 **Ingreso proyectado (promedio con ingresos):** "
        f"${propuesta['ingreso_proyectado']:,.2f} COP\n\n"
        "🎯 **Topes sugeridos por categoría (promedio mensual):**\n"
    )

    for categoria, tope in propuesta["topes_sugeridos"].items():
        mensaje += f" - **{categoria.capitalize()}:** ${tope:,.2f} COP\n"

    mensaje += (
        f"\n📉 **Gastos mensuales sugeridos:** "
        f"${propuesta['total_gastos_sugeridos']:,.2f} COP\n"
        f"💰 **Excedente estimado para ahorro/inversión:** "
        f"${propuesta['ahorro_inversion_sugerido']:,.2f} COP\n\n"
        f"📈 **Recomendación general:** {propuesta['recomendacion']}\n\n"
        "Esta es una estimación basada en el historial, no una garantía de "
        "ingresos futuros ni asesoría financiera personalizada. "
        "No se guardó ningún presupuesto. ¿Deseas que lo guardemos?"
    )
    return mensaje
