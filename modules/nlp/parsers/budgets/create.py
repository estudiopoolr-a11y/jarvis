"""Deterministic parsers. No Firestore writes here."""
import re
from datetime import datetime, timedelta

from modules.nlp.amounts import _normalizar_monto


def _parse_presupuesto(texto: str) -> dict | None:
    """Extrae categoría y límite de presupuesto."""
    texto_lower = texto.lower()

    # Patrones: "presupuesto Comida 50000", "límite Comida 50000", "presupuesto para Comida 50000"
    patrones = [
        r'presupuesto\s+(?:para\s+)?(\w+)\s+([\d,.]+)',
        r'l[íi]mite\s+(\w+)\s+([\d,.]+)',
        r'(\w+)\s+(?:presupuesto\s+)?([\d,.]+)',
    ]
    for patron in patrones:
        match = re.search(patron, texto_lower)
        if match:
            cat = match.group(1).strip()
            limite = float(match.group(2).replace(',', ''))
            # Filtrar palabras que no son categorías
            if cat not in ["el", "la", "los", "las", "de", "del", "en", "un", "una"]:
                return {"categoria": cat.title(), "limite": limite}

    return None

def _parse_presupuesto_multiple(texto: str) -> list[dict] | None:
    """Extrae múltiples presupuestos de un mensaje natural.

    Enfoque: separar por 'y'/coma, encontrar ÚLTIMO número en cada parte,
    todo lo anterior es la categoría (limpiada).

    Ejemplos:
    - "pon presupuesto para mi mama 150.000 y deudas 205.000"
    - "para septiembre presupuesto comida 100k y transporte 50k"
    - "un presupuesto de 150 para mi mamá y en la categoría de deudas pon un presupuesto de 205"
    - "establece presupuesto mama 150.000, deudas 205.000"
    """
    resultados = []
    texto_lower = texto.lower()

    # Si el texto contiene intenciones de renombrar o borrar, no es creación de presupuestos
    if re.search(r'\b(?:ren[oó]mbra\w*|c[aá]mbia\w*\s+el\s+nombre|c[aá]mbiale\s+el\s+nombre|borr\w*|elimin\w*|quit\w*|remuev\w*)\b', texto_lower):
        return None

    # Diccionario extendido de meses (incluye typos comunes)
    _MESES_ALIASES = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "septimebre": 9, "setiembre": 9, "sep": 9,
        "octubre": 10, "noviembre": 11, "diciembre": 12,
        "ago": 8, "dic": 12, "ene": 1, "feb": 2,
        "mar": 3, "abr": 4, "jun": 6, "jul": 7, "oct": 10, "nov": 11,
        "sept": 9, "set": 9
    }

    # Detectar mes objetivo
    mes_target = None
    for nombre, num in _MESES_ALIASES.items():
        if nombre in texto_lower:
            mes_target = num
            break

    # Detectar año
    year_match = re.search(r'\b(20\d{2})\b', texto_lower)
    year = int(year_match.group(1)) if year_match else None

    # PASO 1: Separar por "y" y comas para obtener segmentos individuales
    # Reemplazar "y en la categoria de" / "y la categoria de" por solo "y"
    texto_separado = re.sub(r'\s+y\s+(?:en\s+)?(?:la\s+)?categor[ií]a\s+de\s+', ' y ', texto_lower)
    texto_separado = re.sub(r'\s+y\s+(?:un\s+)?(?:presupue?sto?|presupe?sto?)\s+de\s+', ' y ', texto_separado)
    # Separar por "y" o coma
    partes = re.split(r'\s+y\s+|\s*,\s*', texto_separado)

    # Palabras que NUNCA deben aparecer en una categoría
    _STOP_CATEGORIA = {
        'el', 'la', 'los', 'las', 'de', 'del', 'para', 'en', 'un', 'una',
        'mi', 'mis', 'tu', 'y', 'con', 'a', 'o', 'mes',
        'presupuesto', 'presupuestos', 'presupesto',
        'categoria', 'categoría', 'categorias', 'categorías',
        'pon', 'pone', 'ponga', 'ponme', 'ponte', 'poner',
        'crea', 'crear', 'establece', 'establecer',
        'configura', 'configurar', 'agrega', 'agregar',
        'sube', 'baja', 'cambia', 'modifica', 'actualiza',
        'hola', 'necesito', 'quiero', 'puedes', 'puede',
        'jarvis', 'bot', 'please', 'por',
        'no', 'son', 'era', 'eran', 'es', 'sea', 'sean', 'que', 'q',
        'debe', 'ser', 'más', 'mas', 'pero',
        # Nombres de meses (no deben ser categorías)
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'setiembre', 'septimebre',
        'octubre', 'noviembre', 'diciembre',
        'sep', 'sept', 'set', 'ene', 'feb', 'mar', 'abr', 'jun', 'jul', 'ago', 'oct', 'nov', 'dic',
    }

    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue

        # Quitar años como 2024|2025|2026 para que no interfieran como monto
        parte_sin_anio = re.sub(r'\b20\d{2}\b', '', parte).strip()

        # PASO 2: Encontrar EL ÚLTIMO número en esta parte (es el monto)
        # Patrón: dígitos opcionales con punto/coma/k/m
        patron_num = list(re.finditer(r'([\d]+[.,]?[\d]*(?:k|m)?)\b', parte_sin_anio))
        if not patron_num:
            continue

        ultimo_num = patron_num[-1]
        monto_str = ultimo_num.group(1)
        # 1) categoría DESPUÉS del número: "150 para mamá" → "mamá"
        despues_raw = parte_sin_anio[ultimo_num.end():].strip()
        despues_raw = re.sub(r'^(?:para|en|de|del|la|el|los|las|un|una|y|el)\s+', '', despues_raw).strip()
        despues_raw = re.sub(r'\s+(?:para|en|de|del|y)$', '', despues_raw).strip()
        cat_despues = ''
        if despues_raw:
            cat_despues_words = [w for w in despues_raw.split() if re.sub(r'[^\w]', '', w.lower()) not in _STOP_CATEGORIA]
            cat_despues = ' '.join(cat_despues_words).strip()
        # 2) categoría ANTES del número (modo clásico)
        cat_antes = parte_sin_anio[:ultimo_num.start()].strip()
        # Elegir la mejor opción
        cat_texto = ''
        if cat_despues and len(cat_despues) >= 2 and len(cat_despues.split()) <= 4:
            cat_texto = cat_despues  # audio: "150 para mamá"
        elif cat_antes:
            cat_texto = cat_antes   # texto: "mamá 150.000"

        if not cat_texto:
            continue

        # PASO 3: Limpiar la categoría agresivamente
        # Quitar "para [mes]" al inicio
        cat_texto = re.sub(r'^para\s+\w+\s+', '', cat_texto)
        cat_texto = re.sub(r'^para\s+', '', cat_texto)
        # Quitar "un/una/el/la/los/las/mi/mis/tu" al inicio
        cat_texto = re.sub(r'^(?:un|una|el|la|los|las|mi|mis|tu|de|del)\s+', '', cat_texto)
        # Quitar "presupuesto [de]"/"presupesto [de]" en cualquier posición
        cat_texto = re.sub(r'(?:un\s+)?(?:presupue?sto?t?s?|presupe?sto?t?s?)\s*(?:de\s+)?', ' ', cat_texto)
        # Quitar "la categoría de"/"categoría de"/"categoria de" en cualquier posición
        cat_texto = re.sub(r'(?:la\s+)?categor[ií]a\s+de\s+', ' ', cat_texto)
        # Quitar verbos comandos al inicio: "pon", "ponme", "crea", etc.
        cat_texto = re.sub(r'^(?:pon|pone|ponga|ponme|ponte|crea|crear|establece|establecer|configura|configurar|agrega|agregar|sube|baja|cambia|modifica|actualiza)\s+', '', cat_texto)
        # Quitar "para" / "y" sueltos al inicio
        cat_texto = re.sub(r'^(?:para|y)\s+', '', cat_texto)
        # Limpiar espacios múltiples
        cat_texto = re.sub(r'\s+', ' ', cat_texto).strip()
        # Quitar artículos/conectores residuales al inicio y final
        cat_texto = re.sub(r'^(?:de|del|el|la|los|las|un|una|y|en|para)\s+', '', cat_texto)
        cat_texto = re.sub(r'\s+(?:de|del|el|la|los|las|un|una|y)$', '', cat_texto)
        cat_texto = cat_texto.strip(' ,.:;!?¿¡"\'')

        # Filtrar palabras stop por palabra (normalizando puntuación)
        if cat_texto:
            words = cat_texto.split()
            words_filtradas = [w for w in words if re.sub(r'[^\w]', '', w.lower()) not in _STOP_CATEGORIA]
            cat_texto = ' '.join(words_filtradas).strip()

        # Validación: no debe contener dígitos (ej: "Son 205.000 No")
        if re.search(r'\d', cat_texto):
            continue

        # Validación: categoría debe ser razonable (1-4 palabras, >=2 chars)
        if not cat_texto or len(cat_texto) < 2:
            continue
        num_words = len(cat_texto.split())
        if num_words > 4:
            continue  # Probablemente basura conversacional

        # PASO 4: Normalizar monto
        monto = _normalizar_monto(monto_str)
        if monto is None:
            continue

        resultados.append({
            "categoria": cat_texto.title(),
            "limite": monto,
            "mes": mes_target,
            "year": year
        })

    return resultados if resultados else None
