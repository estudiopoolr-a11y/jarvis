"""Deterministic parsers. No Firestore writes here."""
import re
from datetime import datetime, timedelta

from modules.nlp.amounts import _normalizar_monto

def _parse_listar_categorias(texto: str) -> bool:
    """Detecta intención de listar categorías."""
    texto_lower = texto.lower()
    patrones = [
        r'categor[íi]as?\s+(hay|cu[áé]n?tas?|cu[áé]les?|listar|ver|mostrar|todas)',
        r'qu[ée]?\s+categor[íi]as?\s+(hay|tienes)',
        r'todas?\s+las?\s+categor[íi]as?',
        r'list[ao]?\s+categor[íi]as?',
    ]
    return any(re.search(p, texto_lower) for p in patrones)


def _parse_analisis_financiero(texto: str) -> bool:
    """Detecta intención de análisis financiero."""
    texto_lower = texto.lower()
    patrones = [
        r'an[áa]l[íi]s[íi]s\s+(financiero|mensual|del\s+mes|completo)',
        r'dame\s+(?:un|una|el|la)\s+(?:an[áa]l[íi]s[íi]s|reporte|resumen)\s+(?:financiero|del\s+mes)?',
        r'(?:un?\s+)?reporte\s+(?:mensual|financiero|del\s+mes)',
        r'(?:un?\s+)?resumen\s+(?:mensual|financiero|del\s+mes)',
    ]
    return any(re.search(p, texto_lower) for p in patrones)


def _parse_sobrante(texto: str) -> bool:
    """Detecta intención de no asignar/remarcar sobrante."""
    texto_lower = texto.lower()
    patrones = [
        r'deja\s+(lo\s+)?(que\s+)?sobr[ae]',
        r'dejar\s+(lo\s+)?(que\s+)?sobr[ae]',
        r'sobrante|excedente',
        r'no\s+(asignes?|uses?|gastes?)\s+(lo\s+)?(sobrante|que\s+sobr[ae])',
        r'queda\s+(libre|sin\s+asignar)',
    ]
    return any(re.search(p, texto_lower) for p in patrones)


def _parse_ajustar_balance(texto: str) -> bool:
    """Detecta intención de ajustar/alinear balance a presupuestos."""
    texto_lower = texto.lower()
    patrones = [
        r'ajustar\s+(mi\s+)?balance\s+a\s+(los?\s+)?presupuestos',
        r'alinear\s+(mi\s+)?balance\s+a\s+(los?\s+)?presupuestos',
        r'presupuestos?\s+(son\s+)?techos',
        r'balance\s+(no\s+)?(es\s+)?(presupuesto|techo)',
    ]
    return any(re.search(p, texto_lower) for p in patrones)


def _parse_ver_presupuesto(texto: str) -> bool:
    """Detecta intención de VER presupuestos (requiere palabra de consulta).
    Evita que 'ajustar mi balance a los presupuestos' se interprete como ver.
    """
    texto_lower = texto.lower()
    # Debe tener la palabra "presupuesto" Y una palabra de consulta
    tiene_presupuesto = "presupuesto" in texto_lower or "presupuestos" in texto_lower
    tiene_consulta = any(k in texto_lower for k in [
        "dame", "ver", "mostrar", "hay", "cu[áé]les", "cuales", "lista", "listar", "consultar"
    ])
    return tiene_presupuesto and tiene_consulta
