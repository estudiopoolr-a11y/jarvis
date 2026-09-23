"""Parsers determinísticos para transacciones.

No realizar escrituras en Firestore aquí.
"""

from __future__ import annotations

import re
from datetime import datetime

from modules.nlp.amounts import _normalizar_monto

_CATEGORIA_ALIASES = {"mama": "Mamá", "deuda": "Deudas"}


def _parse_transferencia(texto: str) -> dict | None:
    """Detecta transferencias entre cuentas."""
    texto_lower = texto.lower()

    match = re.search(
        r"pas[eé]\s+([\d,.]+)\s+(?:de|desde)\s+(\w+)\s+(?:a|hacia)\s+(\w+)",
        texto_lower,
    )
    if not match:
        return None

    monto_str, origen, destino = match.groups()
    monto = _normalizar_monto(monto_str)
    if monto is None:
        return None

    return {
        "tipo": "transferencia",
        "monto": monto,
        "origen": origen.title(),
        "destino": destino.title(),
        "status": "cleared",
    }


def _parse_transaccion(texto: str) -> dict | None:
    """Extrae tipo, monto, categoría, payee, tags y fee."""
    texto_lower = texto.lower()

    tags = re.findall(r"#(\w+)", texto)
    tags = [f"#{t}" for t in tags] if tags else []

    fee = 0.0
    fee_match = re.search(
        r"(?:con\s+)?(?:comisi[oó]n|fee)\s+([\d,.]+)",
        texto_lower,
    )
    if fee_match:
        fee = float(fee_match.group(1).replace(",", ""))

    gasto_patterns = [
        (
            r"(?:gasto|gast[eé]|gastó|compr[eéó]|pag(?:ue|ué|ó))\s+"
            r"([\d.,]+(?:[km])?)\s*(?:en\s+)?(.+?)(?:\s*$|$)",
            "monto_primero",
        ),
        (
            r"(?:gasto|gast[eé]|gastó|compr[eéó]|pag(?:ue|ué|ó))\s+"
            r"(?:en\s+)?(.+?)\s+([\d.,]+(?:[km])?)(?:\s*$|$)",
            "categoria_primero",
        ),
    ]

    for patron, orden in gasto_patterns:
        match = re.search(patron, texto_lower)
        if not match:
            continue

        if orden == "monto_primero":
            monto_str, cat = match.group(1), match.group(2).strip()
        else:
            cat, monto_str = match.group(1).strip(), match.group(2)

        monto = _normalizar_monto(monto_str)
        if monto is None:
            continue

        cat = re.sub(r"^(en|del|de|la|el|los|las)\s+", "", cat).strip()
        cat = re.sub(r"\s+de$", "", cat).strip()
        cat = _CATEGORIA_ALIASES.get(cat.casefold(), cat.title() if cat else "General")

        return {
            "tipo": "gasto",
            "monto": monto,
            "categoria": cat,
            "payee": "",
            "fee": fee,
            "status": "cleared",
            "tags": tags,
        }

    ingreso_patterns = [
        r"ingreso\s+([\d,.]+)",
        r"gan[oé]\s+([\d,.]+)",
        r"recib[oí]\s+([\d,.]+)",
        r"salario\s*\+?\s*([\d,.]+)",
        r"\+\s*([\d,.]+)\s*(?:pesos?|cop)?",
    ]

    for patron in ingreso_patterns:
        match = re.search(patron, texto_lower)
        if not match:
            continue

        monto = float(match.group(1).replace(",", ""))
        return {
            "tipo": "ingreso",
            "monto": monto,
            "categoria": "Ingreso",
            "payee": "",
            "fee": 0.0,
            "status": "cleared",
            "tags": tags,
        }

    return None


def _parse_split(texto: str) -> dict | None:
    """Detecta 'dividir 100k entre Comida:50k y Transporte:50k'."""
    texto_lower = texto.lower()

    m = re.search(r"dividir\s+([\d,.]+)\s+entre\s+(.+)", texto_lower)
    if not m:
        return None

    total = float(m.group(1).replace(",", ""))
    resto = m.group(2)

    partes = re.findall(r"([\wáéíóúñ]+)\s*:?\s*([\d,.]+)\s*(k|mil|m)?", resto)
    splits: list[dict] = []

    for cat, monto, mult in partes:
        if not (cat and monto):
            continue

        m_float = float(monto.replace(",", ""))
        if mult and mult.startswith(("k", "m")):
            m_float *= 1000

        splits.append({"categoria": cat.title(), "monto": m_float})

    if not splits:
        return None

    return {"monto_total": total, "splits": splits}


def _parse_transaccion_futura(texto: str) -> dict | None:
    """Detecta 'gasto 50k mañana en comida' o 'el 15 pagaré arriendo 1.5M'."""
    texto_lower = texto.lower()

    # Simplificación: delegar lógica de fecha a un servicio de fechas si es necesario
    # Por ahora, mantener la estructura básica.
    return None
