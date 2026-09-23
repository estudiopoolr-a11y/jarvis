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

# ==================== RECURRENTES (KEBO) ====================

# ==================== RECORDATORIOS POR VOZ (KEBO) ====================

def guardar_recordatorio(usuario_id, texto, dia, month=None, year=None, categoria="", monto=0):
    """Guarda un recordatorio único (no recurrente).

    texto: descripción del recordatorio (ej. "Pagar arriendo")
    dia: día del mes (1-31)
    categoria: categoría asociada (ej. "Arriendo")
    monto: monto asociado si aplica (ej. 1500000)
    """
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        ahora = datetime.now()
        if not year:
            year = str(ahora.year)
        if not month:
            month = f"{ahora.month:02d}"

        # Si el día ya pasó este mes, mover al siguiente
        dia_int = int(dia) if isinstance(dia, str) else dia
        if dia_int < ahora.day:
            # Avanzar al siguiente mes
            proximo = ahora.replace(day=1) + timedelta(days=32)
            year = str(proximo.year)
            month = f"{proximo.month:02d}"

        doc_ref = user_ref.collection("reminders").document()
        doc_ref.set({
            "text": texto,
            "day": dia_int,
            "month": month,
            "year": year,
            "categoria": categoria,
            "monto": float(monto),
            "done": False,
            "notified_at": None,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error guardando recordatorio: {e}")
        return None


def listar_recordatorios(usuario_id, pendientes=True):
    """Lista recordatorios pendientes o todos."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("reminders").stream()
        result = []
        for d in docs:
            data = d.to_dict()
            if pendientes and data.get("done"):
                continue
            data["_id"] = d.id
            result.append(data)
        result.sort(key=lambda x: (int(x.get("year", 0)), int(x.get("month", 0)), int(x.get("day", 1))))
        return result
    except Exception:
        return []


def obtener_recordatorios_hoy(usuario_id):
    """Obtiene los recordatorios que tocan hoy."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        ahora = datetime.now()
        hoy = ahora.day
        mes_actual = f"{ahora.month:02d}"
        year_actual = str(ahora.year)

        docs = user_ref.collection("reminders").where("done", "==", False).stream()
        result = []
        for d in docs:
            data = d.to_dict()
            if data.get("day") == hoy:
                # Coincide con mes actual O es mensual (month="*")
                if data.get("month") in [mes_actual, "*"] and data.get("year") in [year_actual, "*"]:
                    data["_id"] = d.id
                    result.append(data)
        return result
    except Exception:
        return []


def marcar_recordatorio_hecho(usuario_id, reminder_id):
    """Marca un recordatorio como completado."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return False
    try:
        user_ref.collection("reminders").document(reminder_id).update({
            "done": True,
            "done_at": firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception:
        return False


def guardar_recurrente(usuario_id, nombre, monto, frecuencia, dia, cuenta_nombre="Efectivo", categoria_nombre="General"):
    """Crea un gasto/ingreso recurrente."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        cuenta_ref = user_ref.collection("accounts").where("nombre", "==", cuenta_nombre).limit(1).stream()
        cuenta_list = list(cuenta_ref)
        cuenta_id = cuenta_list[0].id if cuenta_list else None
        cat_id = crear_categoria(usuario_id, categoria_nombre)

        doc_ref = user_ref.collection("recurring").document()
        doc_ref.set({
            "nombre": nombre,
            "monto": float(monto),
            "frecuencia": frecuencia,
            "dia": int(dia),
            "account_id": cuenta_id,
            "category_id": cat_id,
            "activo": True,
            "ultima_ejecucion": None,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error guardando recurrente: {e}")
        return None

def listar_recurrentes(usuario_id="default"):
    """Lista todos los recurrentes activos."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("recurring").where("activo", "==", True).stream()
        return [{**d.to_dict(), "_id": d.id} for d in docs]
    except Exception as e:
        print(f"Error listando recurrentes: {e}")
        return []

def ejecutar_recurrentes(usuario_id="default"):
    """Ejecuta los recurrentes que tocan hoy."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        hoy = datetime.now()
        dia_hoy = hoy.day
        dia_semana = hoy.weekday()

        recurrentes = listar_recurrentes(usuario_id)
        ejecutados = []

        for rec in recurrentes:
            frecuencia = rec.get("frecuencia", "monthly")
            dia_rec = int(rec.get("dia", 1))
            cuenta_id = rec.get("account_id")
            nombre = rec.get("nombre")
            monto = float(rec.get("monto", 0))

            toca = False
            if frecuencia == "monthly" and dia_hoy == dia_rec:
                toca = True
            elif frecuencia == "weekly" and dia_semana == dia_rec:
                toca = True

            if toca and cuenta_id:
                year = str(hoy.year)
                month = f"{hoy.month:02d}"
                fecha = hoy.strftime("%Y-%m-%d")

                tx_ref = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").document()
                tx_ref.set({
                    "type": "expense",                              # Kebo: type en inglés
                    "amount": monto,                                 # Kebo: amount en inglés
                    "account_id": cuenta_id,
                    "description": f"🔁 {nombre} (recurrente)",     # Kebo: description en inglés
                    "status": "cleared",                            # Kebo: status
                    "tags": ["recurrente"],                          # Kebo: tags
                    "date": fecha,                                   # Kebo: date en inglés
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "recurring_id": rec["_id"]
                })

                user_ref.collection("accounts").document(cuenta_id).update({
                    "balance": firestore.Increment(-monto)
                })
                user_ref.collection("recurring").document(rec["_id"]).update({
                    "ultima_ejecucion": firestore.SERVER_TIMESTAMP
                })
                ejecutados.append(nombre)

        return ejecutados
    except Exception as e:
        print(f"Error ejecutando recurrentes: {e}")
        return []

