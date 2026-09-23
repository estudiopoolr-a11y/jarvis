"""Deterministic parsers. No Firestore writes here."""
import re
from datetime import datetime, timedelta

from modules.nlp.amounts import _normalizar_monto

def _parse_meta(texto: str) -> dict | None:
    """Extrae nombre, monto y fecha de una meta financiera."""
    texto_lower = texto.lower()

    # Patrones para crear meta
    # "meta vacaciones 3000000 diciembre"
    # "crear meta casa 50000000"
    # "quiero ahorrar 1 millon para navidad"
    # "meta 1 millon"
    patrones = [
        r'meta\s+(\w+(?:\s+\w+)?)\s+([\d,.]+)',
        r'crear\s+meta\s+(\w+(?:\s+\w+)?)\s+([\d,.]+)',
        r'ahorrar\s+(?:para\s+)?(?:un[ao]?\s+)?(\w+(?:\s+\w+)?)\s+([\d,.]+)',
        r'quiero\s+ahorrar\s+([\d,.]+)\s+(?:para\s+)?(.+?)(?:\s+(?:en|hasta|para)\s+(.+))?$',
    ]

    for i, patron in enumerate(patrones):
        match = re.search(patron, texto_lower)
        if match:
            if i == 3:  # "quiero ahorrar 1 millon para X"
                monto_str = match.group(1).replace(',', '')
                nombre = match.group(2).strip()
            else:
                nombre = match.group(1).strip()
                monto_str = match.group(2).replace(',', '')

            try:
                monto = float(monto_str)
            except ValueError:
                continue

            # Detectar fecha
            fecha = ""
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                     "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            mes_encontrado = next((m for m in meses if m in texto_lower), None)
            if mes_encontrado:
                mes_num = meses.index(mes_encontrado) + 1
                fecha = f"2026-{mes_num:02d}-28"

            return {"nombre": nombre.title(), "monto": monto, "fecha": fecha}
    return None

