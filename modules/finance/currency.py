"""Firestore domain helpers. Do not import modules.db from here."""
from datetime import datetime, timedelta

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from modules.firestore.client import (
    USUARIO_PRINCIPAL,
    _get_user_ref,
    get_db,
    inicializar_firebase,
)

from modules.firestore.users import ensure_user

# ==================== MONEDAS Y CONVERSIONES (KEBO) ====================

# Tasas de cambio default (COP base). Se pueden actualizar con tasas reales.
# Estructura: users/{userId}/exchange_rates/{currency}/ (rate, updated_at)
TASAS_DEFAULT = {
    "COP": 1.0,
    "USD": 4100.0,   # 1 USD = 4100 COP
    "EUR": 4500.0,   # 1 EUR = 4500 COP
    "GBP": 5200.0,   # 1 GBP = 5200 COP
    "MXN": 230.0,    # 1 MXN = 230 COP
    "ARS": 4.5,      # 1 ARS = 4.5 COP
}

MONEDAS_SIMBOLO = {
    "COP": "$",
    "USD": "US$",
    "EUR": "€",
    "GBP": "£",
    "MXN": "$",
    "ARS": "$",
}


def convertir_monto(monto, de_moneda, a_moneda="COP"):
    """Convierte un monto entre monedas usando tasas guardadas o default."""
    if de_moneda == a_moneda:
        return float(monto)
    _, user_ref = _get_user_ref()
    if not user_ref:
        return float(monto)
    try:
        # Intentar leer tasa guardada
        rate_doc = user_ref.collection("exchange_rates").document(de_moneda).get()
        if rate_doc.exists:
            rate = rate_doc.to_dict().get("rate", TASAS_DEFAULT.get(de_moneda, 1.0))
        else:
            rate = TASAS_DEFAULT.get(de_moneda, 1.0)
        # Convertir a COP primero, luego a la moneda destino
        en_cop = float(monto) * rate
        if a_moneda == "COP":
            return en_cop
        # Leer tasa destino
        rate_dest = user_ref.collection("exchange_rates").document(a_moneda).get()
        if rate_dest.exists:
            rate_dest_val = rate_dest.to_dict().get("rate", TASAS_DEFAULT.get(a_moneda, 1.0))
        else:
            rate_dest_val = TASAS_DEFAULT.get(a_moneda, 1.0)
        return en_cop / rate_dest_val
    except Exception:
        return float(monto)


def guardar_tasa_cambio(usuario_id, moneda, tasa):
    """Guarda una tasa de cambio personalizada para el usuario."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        user_ref.collection("exchange_rates").document(moneda).set({
            "rate": float(tasa),
            "updated_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
        return True
    except Exception as e:
        print(f"Error guardando tasa: {e}")
        return False


def obtener_tasas_cambio(usuario_id):
    """Obtiene todas las tasas de cambio guardadas."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return {}
    try:
        tasas = {}
        for d in user_ref.collection("exchange_rates").stream():
            tasas[d.id] = d.to_dict()
        return tasas
    except Exception:
        return {}


def obtener_balance_total_multimoneda(usuario_id="default", moneda_base="COP"):
    """Obtiene el balance total convertido a una moneda base.
    Suma balances de todas las cuentas, convirtiendo cada una a la moneda base.
    """
    from modules.finance.accounts import listar_cuentas
    cuentas = listar_cuentas(usuario_id)
    total = 0.0
    for c in cuentas:
        balance = float(c.get("balance", 0))
        currency = c.get("currency", "COP")
        total += convertir_monto(balance, currency, moneda_base)
    return total

