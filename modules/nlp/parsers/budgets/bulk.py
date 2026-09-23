"""Deterministic parsers. No Firestore writes here."""
import re
from datetime import datetime, timedelta

from modules.nlp.amounts import _normalizar_monto


def _parse_configuracion_masiva(texto: str) -> tuple[dict, list] | None:
    """
    Parser directo para el formato de configuración masiva.
    Formatos soportados:
      Formato estructurado (preferido):
        - tipo: ingreso, monto: 806199.03, categoria: Salario, descripcion: Salario mensual
        - tipo: gasto, monto: 332540, categoria: Women, descripcion: Gastos categoría Women
      Formato simple:
        - Salario +806199.03
        - Gasto Women 332540
    Retorna (presupuestos_dict, transacciones_list) o None si no coincide.
    """

    presupuestos = {}
    transacciones = []

    # Buscar sección de presupuestos
    match_pres = re.search(r'presupuestos?[:\s]+(.+?)(?=transacciones?[:\s]|$)', texto, re.IGNORECASE | re.DOTALL)
    if match_pres:
        pres_text = match_pres.group(1)
        for cat_match in re.finditer(r'(\w+)\s*:\s*([\d,.]+)', pres_text):
            cat = cat_match.group(1).strip()
            try:
                monto = float(cat_match.group(2).replace(',', ''))
                if monto > 0:
                    presupuestos[cat] = monto
            except ValueError:
                pass

    # Buscar sección de transacciones
    match_trans = re.search(r'transacciones?[:\s]+(.+?)(?=$)', texto, re.IGNORECASE | re.DOTALL)
    if match_trans:
        trans_text = match_trans.group(1)

        # Parsear cada línea de transacción (formato estructurado)
        lineas = trans_text.strip().split('\n')
        for linea in lineas:
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue

            # Intentar parsear formato estructurado primero
            # Ejemplo: "- tipo: ingreso, monto: 806199.03, categoria: Salario, descripcion: Salario mensual"
            trans_match = re.search(
                r'tipo:\s*(ingreso|gasto)\s*,\s*monto:\s*([\d,.]+)\s*,\s*categoria:\s*([^,]+?)\s*(?:,\s*descripcion:\s*(.+))?$',
                linea, re.IGNORECASE
            )

            if trans_match:
                tipo = trans_match.group(1).lower()
                monto = float(trans_match.group(2).replace(',', ''))
                cat = trans_match.group(3).strip()
                desc = (trans_match.group(4) or cat).strip()

                if monto > 0:
                    transacciones.append({
                        'tipo': tipo,
                        'monto': monto,
                        'categoria': cat.title() if cat else 'General',
                        'descripcion': desc
                    })
                continue

            # Fallback al formato simple: "Palabra +/-Monto" o "Gasto Palabra Monto"
            simple_match = re.search(r'([\w\s]+?)\s*([+-])?\s*\$?\s*([\d,.]+)$', linea)
            if simple_match:
                desc = simple_match.group(1).strip()
                try:
                    monto = float(simple_match.group(3).replace(',', ''))
                    if monto > 0:
                        desc_lower = desc.lower()
                        if desc_lower.startswith('gasto'):
                            tipo = 'gasto'
                            cat = desc[5:].strip() if len(desc) > 5 else 'General'
                        else:
                            tipo = 'ingreso'
                            cat = 'General'
                        transacciones.append({
                            'tipo': tipo,
                            'monto': monto,
                            'categoria': cat.title() if cat else 'General',
                            'descripcion': desc
                        })
                except ValueError:
                    pass

    if presupuestos or transacciones:
        return presupuestos, transacciones
    return None


# ============================================================
# PARSERS DETERMINÍSTICOS (evitan llamadas a Gemini)
# ============================================================
def _parse_bloque_presupuesto_mensual(texto: str) -> tuple[list, str] | None:
    """
    Parser de bloques de presupuesto y gastos mensuales.

    Formato:
    --- MES YYYY ---
    Presupuesto Total: $770.000,00 | Gastado: $1.094.775,69
    Alimentación: Presupuestado $120.000,00 | Gastado $120.000,00
    Moto: Presupuestado $100.000,00 | Gastado $222.427,00

    Devuelve (acciones, mes, año) donde:
    - acciones = lista de tuplas ('presupuesto', categoria, monto) o ('gasto', categoria, monto, fecha)
    - mes = número del mes
    - año = número del año
    """
    acciones = []
    mes_encontrado = None
    año_encontrado = None

    # Patrón para el encabezado del mes
    MES_PATTERN = re.compile(
        r'---\s*([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+(\d{4})\s*---?',
        re.IGNORECASE
    )

    # Patrón para cada línea de categoría
    LINEA_PATTERN = re.compile(
        r'^\s*([^:]+?)\s*:\s*Presupuestado\s*\$?\s*([\d.,]+)\s*\|\s*Gastado\s*\$?\s*([\d.,]+)\s*$',
        re.IGNORECASE
    )

    lineas = texto.splitlines()

    for i, linea in enumerate(lineas):
        # Buscar el encabezado del mes
        m = MES_PATTERN.search(linea)
        if m:
            mes_str, año_str = m.group(1), m.group(2)
            # Convertimos nombre de mes a número
            meses = {
                "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
                "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12,
                "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
                "july":7,"august":8,"september":9,"october":10,"november":11,"december":12
            }
            mes_encontrado = meses.get(mes_str.lower())
            año_encontrado = int(año_str)
            continue  # seguimos procesando líneas posteriores

        # Si ya tenemos mes/año, intentamos coincidir con la línea de categoría
        if mes_encontrado and año_encontrado:
            # Saltar línea de total si existe en la primera iteración
            if i == 0 and "Presupuesto Total:" in linea:
                continue

            l = LINEA_PATTERN.match(linea.strip())
            if l:
                categoria_raw, presup_str, gasto_str = l.groups()
                categoria = categoria_raw.strip().title()

                # Convertimos montos (quitamos puntos de miles y cambiamos coma por punto)
                def to_float(s): return float(s.replace('.', '').replace(',', '.'))

                presupuesto = to_float(presup_str)
                gasto = to_float(gasto_str)

                # 1️⃣ Establecer presupuesto del mes
                acciones.append(('presupuesto', categoria, presupuesto, mes_encontrado, año_encontrado))

                # 2️⃣ Registrar el gasto como transacción del mes (solo si > 0)
                if gasto > 0:
                    fecha = f"{año_encontrado:04d}-{mes_encontrado:02d}-15"  # día medio del mes
                    acciones.append(('gasto', categoria, gasto, fecha))

    if acciones:
        return acciones, mes_encontrado, año_encontrado
    return None
