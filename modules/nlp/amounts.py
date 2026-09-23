"""Normalización de montos COP (k/m, miles, decimales)."""

def _normalizar_monto(monto_str: str) -> float | None:
    """Normaliza un monto: quita separadores de miles, maneja k/m, corrige typos."""
    tiene_k = monto_str.endswith('k')
    tiene_m = monto_str.endswith('m')
    monto_str = monto_str.rstrip('km')

    # Quitar comas (separador de miles en ingles)
    monto_str = monto_str.replace(',', '')

    # Manejar punto
    if '.' in monto_str:
        partes = monto_str.split('.')
        if len(partes) == 2:
            decimales = partes[1]
            if len(decimales) == 3:
                # Separador de miles: '205.000' -> '205000'
                monto_str = monto_str.replace('.', '')
            elif len(decimales) <= 2:
                # Decimal: '150.50' -> '150.50' (no cambiar)
                pass
            elif len(decimales) == 4:
                # 4 digitos: tipico error de tipeo '205.0000' -> '205.000' -> 205000
                monto_str = monto_str.replace('.', '')[:-1]
            else:
                # 5+ digitos: probablemente separador de miles
                monto_str = monto_str.replace('.', '')
        else:
            # Multiples puntos: '1.500.000' -> separadores de miles
            monto_str = monto_str.replace('.', '')

    try:
        monto = float(monto_str)
    except ValueError:
        return None

    if tiene_k:
        monto *= 1000
    elif tiene_m:
        monto *= 1000000

    return monto
