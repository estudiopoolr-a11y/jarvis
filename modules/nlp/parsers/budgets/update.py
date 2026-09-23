"""Deterministic parsers. No Firestore writes here."""
import re
from datetime import datetime, timedelta

from modules.nlp.amounts import _normalizar_monto


def _parse_editar_presupuesto(texto: str) -> dict | None:
    """Detecta intención de editar un presupuesto existente.
    Ejemplos: 'edita mamá a 200k', 'cambia deudas a 300000', 'actualiza X a Y'
    """
    texto_lower = texto.lower()

    patrones = [
        r'(?:edita|editar|cambia|cambiar|actualiza|actualizar|modifica|modificar)\s+(?:el\s+)?(?:presupuesto\s+(?:de\s+|del\s+)?)?(\w+(?:\s+\w+)?)\s+(?:a|hasta)\s+([\d,.]+)\s*(k|m)?',
        r'(?:sube|baja)\s+(?:el\s+)?(?:presupuesto\s+(?:de\s+)?)?(\w+)\s+(?:a|hasta)\s+([\d,.]+)\s*(k|m)?',
    ]

    for patron in patrones:
        match = re.search(patron, texto_lower)
        if match:
            cat = match.group(1).strip()
            monto_str = match.group(2)
            sufijo = match.group(3) or ''

            # Filtrar stop words
            if cat in ['el', 'la', 'los', 'las', 'de', 'del', 'un', 'una', 'y', 'el', 'presupuesto']:
                continue

            monto = _normalizar_monto(monto_str + sufijo)
            if monto and monto > 0:
                return {"categoria": cat.title(), "nuevo_limite": monto}

    return None


def _parse_renombrar_presupuesto(texto: str) -> dict | None:
    """Detecta intención de renombrar un presupuesto, con soporte para formas enclíticas y montos.
    Ejemplos:
    - 'el presupuesto de septiembre renómbralo y ponle q sea de deudas y son 205.000 no 105.000'
    - 'el presupuesto de septiembre renómbralo y ponle q sea de deudas'
    - 'renombra el presupuesto de hola yerbis a mamá'
    - 'cambia el nombre del presupuesto de mamá deudas a deudas'
    - 'renombra presupuesto comida a alimentación y ponle 200k'
    """
    texto_lower = texto.lower().strip()

    # Patrón 1: Orden invertido / enclítico ("el presupuesto de X renómbralo a Y [y ponle Z]")
    # ej: "el presupuesto de septiembre renómbralo y ponle q sea de deudas"
    patron_invertido = (
        r'(?:el\s+)?(?:presupuesto\s+(?:de\s+|del\s+)?)?(.+?)\s+'
        r'(?:ren[oó]mbra(?:lo)?|c[aá]mbia(?:lo)?|c[aá]mbiale\s+el\s+nombre)'
        r'\s+(?:a|por|y\s+ponle\s+q(?:ue)?\s+sea\s+(?:de)?|y\s+que\s+sea\s+(?:de)?|que\s+sea\s+(?:de)?)\s+'
        r'(.+)'
    )
    m = re.search(patron_invertido, texto_lower)

    # Patrón 2: Orden directo ("renombra el presupuesto de X a Y")
    if not m:
        patron_directo = (
            r'(?:ren[oó]mbra(?:lo)?|renombrar|cambia\s+el\s+nombre\s+de(?:l)?|c[aá]mbiale\s+el\s+nombre\s+a)\s+'
            r'(?:el\s+)?(?:presupuesto\s+(?:de\s+|del\s+)?)?(.+?)'
            r'\s+(?:a|por|y\s+ponle\s+q(?:ue)?\s+sea\s+(?:de)?)\s+'
            r'(.+)'
        )
        m = re.search(patron_directo, texto_lower)

    if m:
        ant = m.group(1).strip()
        nue_raw = m.group(2).strip()

        # Extraer posible nuevo monto al final: "y son 205.000 no 105.000", "y ponle 200k", "con 150000"
        nuevo_monto = None
        m_monto = re.search(r'\s+y\s+(?:son|ponle|que\s+sean?|con|el\s+monto\s+es|monto)\s+([\d.,]+(?:k|m)?)(?:\s+no\s+[\d.,]+(?:k|m)?)?$', nue_raw)
        if m_monto:
            monto_str = m_monto.group(1)
            nue_raw = nue_raw[:m_monto.start()].strip()
            nuevo_monto = _normalizar_monto(monto_str)

        # Quitar sufijos de mes si vienen al final de nue_raw
        nue = re.sub(r'\s+(?:de|en|del)?\s*(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|septimebre|setiembre|octubre|noviembre|diciembre)\b.*$', '', nue_raw).strip()
        ant = re.sub(r'^(?:de\s+|del\s+|la\s+|el\s+)', '', ant).strip()
        nue = re.sub(r'^(?:de\s+|del\s+|la\s+|el\s+)', '', nue).strip()
        ant = ant.strip(' ,.:;!?¿¡"\'')
        nue = nue.strip(' ,.:;!?¿¡"\'')

        if ant and nue and len(ant) >= 2 and len(nue) >= 2:
            res = {"cat_antigua": ant.title(), "cat_nueva": nue.title()}
            if nuevo_monto and nuevo_monto > 0:
                res["nuevo_limite"] = nuevo_monto
            return res

    return None


def _parse_presupuesto_modificar(texto: str) -> dict | None:
    """Detecta 'sube Women a 400000' o 'cambia Alimentación a 100000'."""
    texto_lower = texto.lower()

    # Patrones: "sube <cat> a <monto>", "cambia <cat> a <monto>", "baja <cat> a <monto>"
    patrones = [
        r'(?:sube|aumenta|incrementa)\s+(\w+)\s+(?:a|hasta)\s+([\d,.]+)',
        r'(?:baja|reduce|disminuye)\s+(\w+)\s+(?:a|hasta)\s+([\d,.]+)',
        r'(?:cambia|modifica|actualiza)\s+(\w+)\s+(?:a|hasta)\s+([\d,.]+)',
        r'(?:sube|aumenta)\s+(\w+)\s+([\d,.]+)\s*(?:más|adicional)?',
        r'(?:baja|reduce)\s+(\w+)\s+([\d,.]+)',
    ]

    for i, patron in enumerate(patrones):
        match = re.search(patron, texto_lower)
        if match:
            cat = match.group(1).strip()
            # Filtrar palabras que no son categorías
            if cat in ["el", "la", "los", "las", "de", "del", "en", "un", "una", "mi", "tu", "el", "presupuesto"]:
                continue
            try:
                monto = float(match.group(2).replace(',', ''))
                accion = "subir" if i < 1 or i == 3 else ("bajar" if i < 2 or i == 4 else "cambiar")
                return {"categoria": cat.title(), "nuevo_limite": monto, "accion": accion}
            except ValueError:
                continue
    return None
