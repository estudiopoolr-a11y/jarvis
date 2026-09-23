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

def guardar_meta_v2(usuario_id, nombre, monto_objetivo, fecha_limite="", cuenta_nombre="Efectivo"):
    """Crea meta en nueva estructura."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        cuenta_id = cuenta_list[0].id if cuenta_list else None

        doc_ref = user_ref.collection("goals").document()
        doc_ref.set({
            "nombre": nombre,
            "monto_objetivo": float(monto_objetivo),
            "current_amount": 0.0,
            "fecha_limite": fecha_limite,
            "account_id": cuenta_id,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error guardando meta v2: {e}")
        return None

def listar_metas_v2(usuario_id="default"):
    """Lista todas las metas."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("goals").stream()
        metas = []
        for d in docs:
            meta = d.to_dict()
            meta["_id"] = d.id
            obj = float(meta.get("monto_objetivo", 0))
            cur = float(meta.get("current_amount", 0))
            meta["porcentaje"] = round((cur / max(obj, 1)) * 100, 1) if obj > 0 else 0
            meta["restante"] = max(0, obj - cur)
            metas.append(meta)
        return metas
    except Exception as e:
        print(f"Error listando metas: {e}")
        return []

def agregar_aporte_meta(usuario_id, meta_nombre, monto):
    """Agrega un aporte a una meta."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False, "DB no disponible"
    try:
        docs = user_ref.collection("goals").where("nombre", "==", meta_nombre).limit(1).stream()
        docs_list = list(docs)
        if not docs_list:
            return False, f"No encontré la meta '{meta_nombre}'"

        meta_ref = docs_list[0].reference
        meta = docs_list[0].to_dict()
        nuevo_current = float(meta.get("current_amount", 0)) + float(monto)
        objetivo = float(meta.get("monto_objetivo", 0))
        completada = nuevo_current >= objetivo

        aporte_ref = meta_ref.collection("aportes").document()
        aporte_ref.set({
            "monto": float(monto),
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "created_at": firestore.SERVER_TIMESTAMP
        })

        meta_ref.update({"current_amount": nuevo_current, "completada": completada})
        pct = round((nuevo_current / max(objetivo, 1)) * 100, 1)
        return True, f"Aporte de ${float(monto):,.0f} registrado. Progreso: {pct}%"
    except Exception as e:
        return False, f"Error: {e}"

