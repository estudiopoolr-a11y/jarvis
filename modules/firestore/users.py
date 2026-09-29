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


def ensure_user(usuario_id=None, nombre=""):
    """[APLANADO] Ya no crea documentos de usuario. No-op salvo para compatibilidad."""
    return
