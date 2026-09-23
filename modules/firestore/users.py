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

from firebase_admin import firestore

from modules.firestore.client import _get_user_ref


def ensure_user(usuario_id="default", nombre=""):
    """Crea el documento de usuario si no existe."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return
    user_ref.set({
        "nombre": nombre or usuario_id,
        "config": {"moneda": "COP", "tema": "dark"},
        "created_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
