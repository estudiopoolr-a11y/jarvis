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

# ==================== PRÉSTAMOS (KEBO) ====================

def registrar_prestamo(usuario_id, persona, monto, fecha=None, nota=""):
    """Registra un préstamo (dinero que diste y esperas recuperar).

    Los préstamos NO se cuentan como gasto del mes: son un activo
    (por cobrar). El balance los considera hasta que se pagan.

    Args:
        usuario_id: ID del usuario
        persona: A quién le prestaste (ej: "Juan Pérez")
        monto: Cuánto le prestaste
        fecha: Fecha del préstamo (YYYY-MM-DD). Default: hoy
        nota: Nota opcional (motivo, plazo, etc.)

    Returns:
        ID del préstamo creado, o None si falla
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        if not fecha:
            fecha = datetime.now().strftime("%Y-%m-%d")
        doc_ref = user_ref.collection("loans").document()
        doc_ref.set({
            "persona": persona,
            "monto": float(monto),              # Alias para compatibilidad
            "monto_original": float(monto),
            "monto_pagado": 0.0,
            "monto_pendiente": float(monto),
            "fecha": fecha,
            "nota": nota,
            "status": "pendiente",   # pendiente | pagado | parcial
            "pagos": [],             # lista de {monto, fecha}
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error registrando préstamo: {e}")
        return None


def registrar_pago_prestamo(usuario_id, prestamo_id, monto_pago, fecha=None):
    """Registra un pago (parcial o total) de un préstamo.

    Si el pago completa el monto pendiente, marca el préstamo como 'pagado'.

    Returns:
        dict con info del préstamo actualizado, o None si falla
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        if not fecha:
            fecha = datetime.now().strftime("%Y-%m-%d")
        prestamo_ref = user_ref.collection("loans").document(prestamo_id)
        doc = prestamo_ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        nuevo_pagado = float(data.get("monto_pagado", 0)) + float(monto_pago)
        pendiente_original = float(data.get("monto_original", 0))
        nuevo_pendiente = max(0.0, pendiente_original - nuevo_pagado)
        nuevo_status = "pagado" if nuevo_pendiente <= 0.01 else "parcial"

        pagos = list(data.get("pagos", []))
        pagos.append({"monto": float(monto_pago), "fecha": fecha})

        prestamo_ref.update({
            "monto_pagado": nuevo_pagado,
            "monto_pendiente": nuevo_pendiente,
            "status": nuevo_status,
            "pagos": pagos,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        return {
            "id": prestamo_id,
            "monto_pagado": nuevo_pagado,
            "monto_pendiente": nuevo_pendiente,
            "status": nuevo_status,
        }
    except Exception as e:
        print(f"Error registrando pago: {e}")
        return None


def listar_prestamos(usuario_id="default", solo_pendientes=False):
    """Lista préstamos. Por defecto todos; con solo_pendientes=True, solo los no pagados.

    Returns:
        Lista de dicts con info del préstamo + campo '_id'
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("loans").stream()
        result = []
        for d in docs:
            data = d.to_dict()
            if solo_pendientes and data.get("status") == "pagado":
                continue
            data["_id"] = d.id
            result.append(data)
        # Más recientes primero
        result.sort(key=lambda x: x.get("fecha", ""), reverse=True)
        return result
    except Exception as e:
        print(f"Error listando préstamos: {e}")
        return []


def obtener_total_por_cobrar(usuario_id="default"):
    """Suma de todo lo pendiente por cobrar.

    Returns:
        float con el total pendiente
    """
    prestamos = listar_prestamos(usuario_id, solo_pendientes=True)
    total = sum(float(p.get("monto_pendiente", 0)) for p in prestamos)
    return total


def eliminar_prestamo(usuario_id, prestamo_id):
    """Elimina un préstamo (y su historial de pagos)."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        user_ref.collection("loans").document(prestamo_id).delete()
        return True
    except Exception as e:
        print(f"Error eliminando préstamo: {e}")
        return False

