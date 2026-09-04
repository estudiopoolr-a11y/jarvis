"""
JARVIS Reminders - Sistema de recordatorios para pagos recurrentes y personalizados.
Detecta pagos que tocan hoy y envía recordatorio a Discord.
"""
import os
import requests
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=-5))
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL") or "https://discordapp.com/api/webhooks/1544477914391904406/J4y5ycFy6e-AVHTDoN2-kRh-Su1Dt3ArUAePdOvIFbMTCjAuvKwwrvPqszE1yLeFtmO3"

import firebase_admin
from firebase_admin import credentials, initialize_app, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

db = None


def inicializar_firebase():
    global db
    if not firebase_admin._apps:
        firebase_json_str = (
            os.getenv("FIREBASE_CREDENTIALS") or
            os.getenv("FIREBASE_CREDENTIALS_JSON") or
            os.getenv("FIREBASE_KEY") or
            os.getenv("FIREBASE_SERVICE_ACCOUNT")
        )
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")

        if firebase_json_str:
            firebase_json_str = firebase_json_str.strip()
            if (firebase_json_str.startswith("'") and firebase_json_str.endswith("'")) or \
               (firebase_json_str.startswith('"') and firebase_json_str.endswith('"')):
                firebase_json_str = firebase_json_str[1:-1].strip()
            with open(cred_path, "w", encoding="utf-8") as f:
                f.write(firebase_json_str)
            cred = credentials.Certificate(cred_path)
            initialize_app(cred)

        if not firebase_admin._apps and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            initialize_app(cred)

    if firebase_admin._apps:
        db = firestore.client()
        return True
    return False


def obtener_pagos_hoy(usuario_id="iphone_user"):
    """Detecta qué pagos recurrentes tocan hoy."""
    if not inicializar_firebase() or not db:
        return []

    ahora = datetime.now(TZ)
    dia_hoy = ahora.day

    try:
        # Estructura Kebo: users/{userId}/recurring
        docs = db.collection("users").document(usuario_id).collection("recurring").where("activo", "==", True).stream()
        pagos_hoy = []
        for doc in docs:
            d = doc.to_dict()
            dia_rec = int(d.get("dia", 1))
            if dia_rec == dia_hoy:
                pagos_hoy.append({
                    "nombre": d.get("nombre", ""),
                    "monto": float(d.get("monto", 0)),
                    "frecuencia": d.get("frecuencia", "monthly"),
                    "categoria": d.get("categoria_id", "")
                })
        return pagos_hoy
    except Exception as e:
        print(f"Error obteniendo pagos: {e}")
        return []


def obtener_recordatorios_personalizados(usuario_id="iphone_user"):
    """Obtiene recordatorios únicos personalizados del usuario."""
    if not inicializar_firebase() or not db:
        return []

    ahora = datetime.now(TZ)
    recordatorios = []

    try:
        docs = db.collection("recordatorios").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        for doc in docs:
            d = doc.to_dict()
            fecha = d.get("fecha", "")
            if fecha == ahora.strftime("%Y-%m-%d") and not d.get("completado", False):
                recordatorios.append({
                    "titulo": d.get("titulo", ""),
                    "descripcion": d.get("descripcion", "")
                })
        return recordatorios
    except Exception:
        return []


def enviar_recordatorio_discord(pagos, recordatorios):
    """Envía recordatorio a Discord."""
    if not pagos and not recordatorios:
        return False

    embed = {
        "title": f"🔔 Recordatorio del día {datetime.now(TZ).strftime('%d/%m')}",
        "color": 16776960,  # Amarillo
        "fields": []
    }

    if pagos:
        pagos_text = ""
        for p in pagos:
            pagos_text += f"📅 **{p['nombre']}**: ${p['monto']:,.0f}\n"
        embed["fields"].append({
            "name": "💸 Pagos recurrentes de hoy",
            "value": pagos_text,
            "inline": False
        })

    if recordatorios:
        rec_text = ""
        for r in recordatorios:
            rec_text += f"📌 **{r['titulo']}**: {r['descripcion']}\n"
        embed["fields"].append({
            "name": "🎯 Recordatorios personalizados",
            "value": rec_text,
            "inline": False
        })

    embed["footer"] = {"text": "🤖 JARVIS Reminder"}

    try:
        r = requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
        return r.status_code in [200, 204]
    except Exception as e:
        print(f"Error enviando recordatorio: {e}")
        return False


def main():
    """Punto de entrada - ejecutar vía cron diario."""
    pagos = obtener_pagos_hoy("iphone_user")
    recordatorios = obtener_recordatorios_personalizados("iphone_user")

    if pagos or recordatorios:
        enviar_recordatorio_discord(pagos, recordatorios)
        print(f"Enviado: {len(pagos)} pagos + {len(recordatorios)} recordatorios")
    else:
        print("Sin recordatorios para hoy")


if __name__ == "__main__":
    main()