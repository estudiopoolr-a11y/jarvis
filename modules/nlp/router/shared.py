"""Shared helpers for deterministic NLP router.

Este archivo NO ejecuta escrituras; solo ofrece utilidades de parsing/tiempo.
"""

from __future__ import annotations

import re
from datetime import datetime

# Shared month mapping
_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "septimebre": 9, "setiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
    "sep": 9, "sept": 9, "set": 9,
    "ago": 8, "dic": 12, "ene": 1, "feb": 2,
    "mar": 3, "abr": 4, "jun": 6, "jul": 7, "oct": 10, "nov": 11,
}

_NOMBRES_MESES = [
    "",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def meses_spanish() -> dict[str, int]:
    return dict(_MESES)


def nombre_mes(mes_num: int) -> str:
    return _NOMBRES_MESES[mes_num]


def detectar_mes_num(texto_lc: str, now: datetime | None = None) -> int:
    """Devuelve mes (1-12) detectado o mes actual si no hay match."""
    now = now or datetime.now()
    for nombre, num in _MESES.items():
        if nombre in texto_lc:
            return num
    return now.month


def detectar_year(texto_lc: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    year_match = re.search(r"\b(20\d{2})\b", texto_lc)
    return year_match.group(1) if year_match else str(now.year)


def normalizar_limite_audio_audio(es_audio: bool, limite: float | int | None) -> float | None:
    if limite is None:
        return None
    if es_audio and limite < 1000:
        return float(limite) * 1000
    return float(limite)
