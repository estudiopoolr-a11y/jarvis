"""Deterministic parsers. No Firestore writes here."""
import re
from datetime import datetime, timedelta

from modules.nlp.amounts import _normalizar_monto

def _parse_pago_fijo(texto: str) -> dict | None:
    """Detecta 'pago fijo arriendo 1500000 día 5'."""
    texto_lower = texto.lower()

    # Patrón: "pago fijo <nombre> <monto> [día <N>]"
    patron = r'pago\s+fijo\s+(\w+(?:\s+\w+)?)\s+([\d,.]+)(?:\s+d[ií]a\s+(\d+))?'
    match = re.search(patron, texto_lower)
    if match:
        nombre = match.group(1).strip()
        try:
            monto = float(match.group(2).replace(',', ''))
            dia = int(match.group(3)) if match.group(3) else 1
            return {"nombre": nombre.title(), "monto": monto, "dia_mes": dia}
        except ValueError:
            pass
    return None


def _parse_perfil(texto: str) -> dict | None:
    """Detecta 'mi nombre es X', 'vivo en Y'."""
    texto_lower = texto.lower()

    # "mi nombre es Daniel"
    m = re.search(r'mi nombre es\s+(\w+)', texto_lower)
    if m:
        return {"nombre": m.group(1).title()}

    # "vivo en Bogotá"
    m = re.search(r'vivo en\s+(\w+(?:\s+\w+)?)', texto_lower)
    if m:
        return {"ciudad": m.group(1).title()}

    # "tengo X años"
    m = re.search(r'tengo\s+(\d+)\s+(?:a[ñn]os)', texto_lower)
    if m:
        return {"edad": int(m.group(1))}

    return None


def _parse_subcategoria(texto: str) -> dict | None:
    """Detecta 'subcategoría X de Y' o 'agregar X a Y'."""
    texto_lower = texto.lower()
    # "subcategoría Restaurantes de Alimentación"
    m = re.search(r'subcategor[ií]a\s+(.+?)\s+(?:de|en|para)\s+(.+)', texto_lower)
    if m:
        return {"sub_nombre": m.group(1).strip().title(), "cat_nombre": m.group(2).strip().title()}
    # "agregar Restaurantes a Alimentación"
    m = re.search(r'agregar\s+(.+?)\s+a\s+la?\s+(?:categor[ií]a\s+)?(.+)', texto_lower)
    if m and any(k in texto_lower for k in ["subcategoría", "categoría", "comida", "transporte"]):
        return {"sub_nombre": m.group(1).strip().title(), "cat_nombre": m.group(2).strip().title()}
    return None


def _parse_split(texto: str) -> dict | None:
    """Detecta 'dividir 100k entre Comida:50k y Transporte:50k'."""
    texto_lower = texto.lower()
    m = re.search(r'dividir\s+([\d,.]+)\s+entre\s+(.+)', texto_lower)
    if m:
        total = float(m.group(1).replace(',', ''))
        resto = m.group(2)
        # "Comida:50k y Transporte:50k"
        partes = re.findall(r'([\wáéíóúñ]+)\s*:?\s*([\d,.]+)\s*(k|mil|m)?', resto)
        splits = []
        for cat, monto, mult in partes:
            if cat and monto:
                m_float = float(monto.replace(',', ''))
                if mult and mult.startswith(('k', 'm')):
                    m_float *= 1000
                splits.append({"categoria": cat.title(), "monto": m_float})
        if splits:
            return {"monto_total": total, "splits": splits}
    return None


def _parse_transaccion_futura(texto: str) -> dict | None:
    """Detecta 'gasto 50k mañana en comida' o 'el 15 pagaré arriendo 1.5M'."""
    texto_lower = texto.lower()
    meses = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
             "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12}

    # "el 15 pagar arriendo 1.5M"
    m = re.search(r'el\s+(\d{1,2})\s+(?:de\s+)?(\w+)?\s*(?:pagar|gastar|gasto)\s+([\d,.]+)\s*(k|mil|m)?\s*(?:en\s+)?(.+)?', texto_lower)
    if m:
        dia = int(m.group(1))
        mes_nombre = m.group(2)
        monto = float(m.group(3).replace(',', ''))
        if m.group(4) and m.group(4).startswith(('k', 'm')):
            monto *= 1000
        cat = (m.group(5) or "General").strip().title()
        if mes_nombre and mes_nombre in meses:
            mes_num = meses[mes_nombre]
            year = datetime.now().year
        else:
            mes_num = datetime.now().month
            year = datetime.now().year
            if dia < datetime.now().day:
                mes_num += 1
                if mes_num > 12:
                    mes_num = 1
                    year += 1
        fecha = f"{year}-{mes_num:02d}-{dia:02d}"
        return {"tipo": "expense", "monto": monto, "categoria": cat, "fecha": fecha}

    # "gasto 50k mañana en comida"
    m = re.search(r'gast[oáé]\s+([\d,.]+)\s*(k|mil|m)?\s+ma[ñn]ana\s+(?:en\s+)?(.+)', texto_lower)
    if m:
        monto = float(m.group(1).replace(',', ''))
        if m.group(2) and m.group(2).startswith(('k', 'm')):
            monto *= 1000
        cat = m.group(3).strip().title()
        manana = datetime.now() + timedelta(days=1)
        fecha = manana.strftime("%Y-%m-%d")
        return {"tipo": "expense", "monto": monto, "categoria": cat, "fecha": fecha}

    return None


def _parse_recordatorio(texto: str) -> dict | None:
    """Detecta 'recuerda pagar arriendo el día 1' o 'recuérdame X el 5'."""
    texto_lower = texto.lower()
    m = re.search(r'recu[eé]rda(?:me)?\s+(?:pagar\s+|que\s+)?(.+?)\s+(?:el\s+d[ií]a\s+|el\s+)(\d{1,2})', texto_lower)
    if m:
        return {"texto": m.group(1).strip().title(), "dia": int(m.group(2))}
    return None


def _parse_busqueda(texto: str) -> dict | None:
    """Detecta 'buscar gastos de comida en septiembre'."""
    texto_lower = texto.lower()
    m = re.search(r'buscar?\s+(.+?)\s+(?:en|entre|del?)\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)', texto_lower)
    if m:
        return {"texto": m.group(1).strip(), "mes": m.group(2).title()}
    m = re.search(r'buscar?\s+(.+)', texto_lower)
    if m:
        return {"texto": m.group(1).strip()}
    return None


def _parse_tasa_cambio(texto: str) -> dict | None:
    """Detecta 'tasa USD 4500' o 'guardar tasa EUR 5000'."""
    texto_lower = texto.lower()
    m = re.search(r'tasa\s+(\w{3})\s+([\d,.]+)', texto_lower)
    if m:
        return {"moneda": m.group(1).upper(), "tasa": float(m.group(2).replace(',', ''))}
    return None


# ============================================================
# PARSERS DE CONSULTA FINANCIERA (v3.2)
# ============================================================
