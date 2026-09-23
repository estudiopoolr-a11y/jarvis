"""Deterministic parsers. No Firestore writes here."""
import re
from datetime import datetime, timedelta

from modules.nlp.amounts import _normalizar_monto


def _parse_borrar_presupuesto(texto: str) -> dict | None:
    """Detecta intención de borrar un presupuesto o todos los presupuestos de un mes.
    Soporta subjuntivo ('necesito q elimines'), typos ('presupuestps') y múltiples categorías en una sola frase.
    Ejemplos:
    - 'borra todos los presupuestos de septiembre' -> {'todos': True}
    - 'necesito q elimines los presupuestps de X y el de Y y el de Z' -> {'categorias': ['X', 'Y', 'Z']}
    - 'borra mamá de presupuestos' -> {'categoria': 'Mamá', 'categorias': ['Mamá']}
    - 'elimina el presupuesto de comida' -> {'categoria': 'Comida', 'categorias': ['Comida']}
    """
    texto_lower = texto.lower().strip()

    _MESES_SET = {
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
        'agosto', 'septiembre', 'septimebre', 'setiembre', 'octubre',
        'noviembre', 'diciembre', 'sep', 'oct', 'nov', 'dic', 'ene', 'feb', 'mar', 'abr', 'jun', 'jul', 'ago'
    }

    # 1. Borrar TODOS los presupuestos de un mes
    if re.search(r'(?:borra|borrar|borres|elimina|eliminar|elimines|limpia|limpiar|limpies)\s+(?:todos?\s+)?(?:los\s+)?presupue?[a-z]*\b', texto_lower):
        m_cat = re.search(r'presupue?[a-z]*\s+de\s+([a-záéíóúñ]+)', texto_lower)
        if not m_cat or m_cat.group(1) in _MESES_SET:
            return {"todos": True}

    # 2. Borrar categoría o categorías específicas
    patron_verbo = r'(?:necesito\s+q(?:ue)?\s+|quiero\s+q(?:ue)?\s+|favor\s+|por\s+favor\s+)?(?:borra|borrar|borres|elimina|eliminar|elimines|quita|quitar|quites|remueve|remover|remuevas|limpia|limpiar)\s+(?:el\s+|los\s+)?(?:presupue?[a-z]*\s+(?:de\s+|del\s+)?)?'
    m = re.search(patron_verbo, texto_lower)
    if m:
        resto = texto_lower[m.end():].strip()
        # Si no había prefijo de presupuesto pero venía al final ("borra X de presupuestos")
        resto = re.sub(r'\s+(?:de|del|en)\s+(?:los\s+)?presupue?[a-z]*.*$', '', resto).strip()
        # Quitar sufijos de mes globales al final
        resto = re.sub(r'\s+(?:de|en|del)?\s*(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|septimebre|setiembre|octubre|noviembre|diciembre)\b.*$', '', resto).strip()

        # Separar categorías
        # Si tiene conectores explícitos como ' y el de ' o ' y de ' o ' y '
        if re.search(r'\s+y\s+(?:el\s+de\s+|la\s+de\s+|de\s+|del\s+)?|,\s*(?:el\s+de\s+|la\s+de\s+)', resto):
            segmentos = re.split(r'\s+y\s+(?:el\s+de\s+|la\s+de\s+|el\s+|la\s+|de\s+|del\s+)?|,\s*(?:el\s+de\s+|la\s+de\s+)', resto)
        else:
            segmentos = re.split(r'\s*,\s*|\s+y\s+', resto)

        cats_encontradas = []
        for seg in segmentos:
            seg = seg.strip()
            # Limpiar conectores y artículos
            seg = re.sub(r'^(?:de\s+|del\s+|la\s+|el\s+|un\s+|una\s+)', '', seg).strip()
            seg = re.sub(r'\s+(?:de|del|el|la)$', '', seg).strip()
            seg = seg.strip(' ,.:;!?¿¡"\'')
            if seg and len(seg) >= 2 and seg not in ['el', 'la', 'los', 'las', 'de', 'del', 'un', 'una', 'y', 'presupuesto', 'presupuestos', 'todos', 'todos los']:
                cats_encontradas.append(seg.title())

        if cats_encontradas:
            return {
                "categoria": cats_encontradas[0],
                "categorias": cats_encontradas
            }

    return None
