"""
JARVIS Daily Summary - Envía un resumen automático al canal de Discord vía webhook.
Se ejecuta vía cron job de Render cada 30 minutos.
Solo envía entre las 7am-12pm y 7pm-12am (hora Colombia UTC-5).
"""
import os
import json
import requests
from datetime import datetime, timezone, timedelta

# Zona horaria Colombia
TZ = timezone(timedelta(hours=-5))

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL") or "https://discordapp.com/api/webhooks/1544477914391904406/J4y5ycFy6e-AVHTDoN2-kRh-Su1Dt3ArUAePdOvIFbMTCjAuvKwwrvPqszE1yLeFtmO3"

# Firebase
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
    return db


def obtener_datos():
    """Obtiene balance, presupuestos y tareas de todos los usuarios."""
    if not db:
        inicializar_firebase()

    balance_data = {}
    try:
        docs = db.collection("finanzas").stream()
        for doc in docs:
            t = doc.to_dict()
            uid = t.get("usuario_id", "default")
            if uid not in balance_data:
                balance_data[uid] = {"ingresos": 0.0, "gastos": 0.0}
            monto = float(t.get("monto", 0))
            if t.get("tipo") == "ingreso":
                balance_data[uid]["ingresos"] += monto
            else:
                balance_data[uid]["gastos"] += monto
    except Exception as e:
        print(f"Error leyendo finanzas: {e}")

    presupuestos_data = {}
    try:
        docs = db.collection("presupuestos").stream()
        for doc in docs:
            d = doc.to_dict()
            uid = d.get("usuario_id", "default")
            cat = d.get("categoria")
            limite = float(d.get("limite", 0))
            presupuestos_data.setdefault(uid, {})[cat] = limite
    except Exception as e:
        print(f"Error leyendo presupuestos: {e}")

    tareas_data = {}
    try:
        docs = db.collection("tareas").where(filter=FieldFilter("completada", "==", False)).stream()
        for doc in docs:
            t = doc.to_dict()
            uid = t.get("usuario_id", "default")
            tareas_data.setdefault(uid, []).append(t)
    except Exception as e:
        print(f"Error leyendo tareas: {e}")

    return balance_data, presupuestos_data, tareas_data


def construir_mensaje(hora_actual: datetime) -> str:
    """Construye el mensaje del resumen."""
    balance, presupuestos, tareas = obtener_datos()

    if not balance:
        return "🤖 **JARVIS** | No hay datos registrados aún."

    saludo = "🌅 Buenos días" if hora_actual.hour < 12 else "🌆 Buenas tardes"
    fecha = hora_actual.strftime("%A %d de %B, %Y")
    hora = hora_actual.strftime("%I:%M %p")

    partes = [f"{saludo}, señor. {fecha} - {hora}", ""]

    for uid, data in balance.items():
        ingresos = data["ingresos"]
        gastos = data["gastos"]
        neto = ingresos - gastos

        partes.append(f"💰 **BALANCE GENERAL**")
        partes.append(f"• Ingresos: +${ingresos:,.0f}")
        partes.append(f"• Gastos: -${gastos:,.0f}")
        partes.append(f"• Neto: ${neto:,.0f}")
        partes.append("")

        # Presupuestos
        if uid in presupuestos and presupuestos[uid]:
            partes.append("🎯 **PRESUPUESTOS**")
            for cat, limite in presupuestos[uid].items():
                # Calcular gasto por categoría
                gasto_cat = 0.0
                try:
                    docs = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", str(uid))).where(filter=FieldFilter("categoria", "==", cat)).stream()
                    for d in docs:
                        if d.to_dict().get("tipo") == "gasto":
                            gasto_cat += float(d.to_dict().get("monto", 0))
                except Exception:
                    pass

                pct = (gasto_cat / limite * 100) if limite > 0 else 0
                barra = "█" * int(pct // 10) + "░" * (10 - int(pct // 10))
                estado = "🚨" if pct >= 100 else "⚠️" if pct >= 80 else "✅"
                partes.append(f"{estado} {cat}: {barra} {pct:.0f}% (${gasto_cat:,.0f}/${limite:,.0f})")
            partes.append("")

        # Tareas pendientes
        if uid in tareas and tareas[uid]:
            partes.append(f"📋 **TAREAS PENDIENTES ({len(tareas[uid])})**")
            for t in tareas[uid][:5]:
                prioridad = t.get("prioridad", "Media")
                emoji = "🔴" if prioridad == "Alta" else "🟡" if prioridad == "Media" else "🟢"
                partes.append(f"{emoji} {t.get('tarea')} (Vence: {t.get('fecha_limite', 'Pronto')})")
            if len(tareas[uid]) > 5:
                partes.append(f"  ...y {len(tareas[uid]) - 5} más")
        else:
            partes.append("✅ Sin tareas pendientes.")

        partes.append("")
        partes.append("_Sistemas operativos. JARVIS a la espera de instrucciones._")

    return "\n".join(partes)


def enviar_a_discord(mensaje: str):
    """Envía el mensaje al webhook de Discord."""
    payload = {
        "content": mensaje,
        "username": "JARVIS",
        "avatar_url": None
    }
    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 204:
            print(f"✅ Resumen enviado a las {datetime.now(TZ).strftime('%H:%M')}")
        else:
            print(f"⚠️ Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"❌ Error enviando: {e}")


def deberia_enviar(hora: datetime) -> bool:
    """Verifica si está en la ventana horaria activa (7am-12pm o 7pm-12am)."""
    h = hora.hour
    return (7 <= h < 12) or (19 <= h < 24)


def main():
    ahora = datetime.now(TZ)

    if not deberia_enviar(ahora):
        print(f"⏸️ Fuera de horario activo ({ahora.hour}:00). No se envía.")
        return

    if not db:
        inicializar_firebase()

    if not db:
        print("❌ No se pudo conectar a Firebase")
        return

    mensaje = construir_mensaje(ahora)
    enviar_a_discord(mensaje)


if __name__ == "__main__":
    main()
