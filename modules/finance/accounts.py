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


# ==================== CUENTAS (KEBO) ====================

def listar_cuentas(usuario_id="default"):
    """Lista todas las cuentas del usuario (estilo Kebo).
    Incluye: nombre, type, currency, institution, bank_last4, balance, icon, color.
    """
    db = get_db()
    if not db:
        return []
    try:
        docs = db.collection("accounts").stream()
        cuentas = []
        for d in docs:
            data = d.to_dict()
            # Compatibilidad: viejo (tipo/icono) -> nuevo (type/icon)
            # Compatibilidad de campos (Kebo: nombre/institution/bank_last4 vs legacy: name/bank/type)
            nombre = data.get("nombre")
            if not nombre:
                nombre = data.get("name") or ""

            institution = data.get("institution")
            if not institution:
                institution = data.get("bank") or ""

            bank_last4 = data.get("bank_last4")
            if not bank_last4:
                bank_last4 = data.get("bank_last4") or data.get("bankLast4") or ""

            tipo_kebo = data.get("type") or data.get("tipo") or "cash"

            cuentas.append({
                "_id": d.id,
                "nombre": nombre,
                "type": tipo_kebo,  # Kebo: type
                "currency": data.get("currency", "COP"),  # Kebo: currency
                "institution": institution,  # Kebo: institution
                "bank_last4": bank_last4,  # Kebo: bank_last4
                "balance": float(data.get("balance", 0)),
                "icon": data.get("icon") or data.get("icono") or "💵",  # Kebo: icon
                "color": data.get("color", "#10b981"),
                # Alias legacy
                "tipo": tipo_kebo,
                "icono": data.get("icon") or data.get("icono") or "💵",
            })
        return cuentas
    except Exception as e:
        print(f"Error listando cuentas: {e}")
        return []

def crear_cuenta(usuario_id, nombre, tipo="cash", balance=0, icono="💵", color="#10b981",
                 currency="COP", institution="", bank_last4=""):
    """Crea una nueva cuenta con metadata estilo Kebo.
    tipo: cash | savings | checking | credit | investment
    """
    db = get_db()
    if not db:
        return None
    try:
        doc_ref = db.collection("accounts").document()
        doc_ref.set({
            "nombre": nombre,
            "type": tipo,                          # Campo Kebo: 'type' en inglés
            "currency": currency,                  # Campo Kebo: moneda base
            "institution": institution,            # Campo Kebo: banco (Bancolombia, Davivienda, etc.)
            "bank_last4": bank_last4,              # Campo Kebo: últimos 4 dígitos
            "balance": float(balance),
            "icon": icono,                         # Campo Kebo: 'icon' en inglés
            "color": color,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error creando cuenta: {e}")
        return None

def actualizar_balance_cuenta(usuario_id, cuenta_id, delta):
    """Suma delta al balance de una cuenta."""
    db = get_db()
    if not db:
        return
    try:
        db.collection("accounts").document(cuenta_id).update({
            "balance": firestore.Increment(delta)
        })
    except Exception as e:
        print(f"Error actualizando balance: {e}")

def renombrar_cuenta(usuario_id, cuenta_id_o_nombre, nuevo_nombre):
    """Renombra una cuenta existente buscando por ID o por nombre exacto/parcial."""
    db = get_db()
    if not db:
        return False, "No se pudo obtener la referencia de la base de datos."
    try:
        accounts_ref = db.collection("accounts")
        # Primero intentamos buscar por ID directo
        doc_ref = accounts_ref.document(cuenta_id_o_nombre)
        doc = doc_ref.get()
        
        target_id = None
        if doc.exists:
            target_id = cuenta_id_o_nombre
        else:
            # Buscar por nombre (case-insensitive o parcial)
            docs = accounts_ref.stream()
            for d in docs:
                data = d.to_dict()
                if cuenta_id_o_nombre.lower() in data.get("nombre", "").lower():
                    target_id = d.id
                    break
        
        if not target_id:
            return False, f"No se encontró la cuenta '{cuenta_id_o_nombre}'."
            
        accounts_ref.document(target_id).update({
            "nombre": nuevo_nombre
        })
        return True, f"Cuenta renombrada exitosamente a '{nuevo_nombre}'."
    except Exception as e:
        print(f"Error renombrando cuenta: {e}")
        return False, f"Error al renombrar cuenta: {e}"

