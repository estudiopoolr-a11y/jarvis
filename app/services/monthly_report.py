"""
JARVIS Monthly Report - Envía un resumen mensual bonito a Discord.
Se ejecuta el día 1 de cada mes con el resumen del mes anterior.
"""
import os
import json
import requests
from datetime import datetime, timezone, timedelta
from calendar import monthrange

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


def obtener_datos_mes(usuario_id, year, month):
    """Obtiene todas las transacciones y presupuestos del mes."""
    db_ok = inicializar_firebase()
    if not db_ok or not db:
        return None

    # Transacciones del mes
    docs = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
    ingresos_total = 0.0
    gastos_total = 0.0
    gastos_por_cat = {}
    num_tx = 0

    for doc in docs:
        d = doc.to_dict()
        fecha = d.get("fecha", "")
        monto = float(d.get("monto", 0))
        tipo = d.get("tipo", "gasto")
        cat = d.get("categoria", "General")

        # Filtrar por mes
        if fecha.startswith(f"{year}-{month:02d}"):
            num_tx += 1
            if tipo == "ingreso":
                ingresos_total += monto
            else:
                gastos_total += monto
                gastos_por_cat[cat] = gastos_por_cat.get(cat, 0) + monto

    # Presupuestos
    docs_p = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
    presupuestos = {}
    for doc in docs_p:
        d = doc.to_dict()
        presupuestos[d.get("categoria")] = float(d.get("limite", 0))

    return {
        "ingresos": ingresos_total,
        "gastos": gastos_total,
        "balance": ingresos_total - gastos_total,
        "num_transacciones": num_tx,
        "gastos_por_categoria": gastos_por_cat,
        "presupuestos": presupuestos,
        "year": year,
        "month": month
    }


def generar_reporte_mes_anterior(usuario_id="iphone_user"):
    """Genera el reporte del mes anterior."""
    ahora = datetime.now(TZ)
    # Mes anterior
    if ahora.month == 1:
        year = ahora.year - 1
        month = 12
    else:
        year = ahora.year
        month = ahora.month - 1

    datos = obtener_datos_mes(usuario_id, year, month)
    if not datos:
        return None

    datos["mes_nombre"] = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][month-1]
    return datos


def enviar_a_discord(data):
    """Envía el reporte formateado a Discord."""
    if not data:
        return False

    embed = {
        "title": f"📊 Resumen de {data['mes_nombre']} {data['year']}",
        "color": 5025616,  # Verde Kebo
        "fields": [
            {
                "name": "💰 Balance",
                "value": f"```\n${data['balance']:,.0f}\n```",
                "inline": True
            },
            {
                "name": "📈 Ingresos",
                "value": f"```\n+${data['ingresos']:,.0f}\n```",
                "inline": True
            },
            {
                "name": "📉 Gastos",
                "value": f"```\n-${data['gastos']:,.0f}\n```",
                "inline": True
            }
        ],
        "footer": {"text": "🤖 JARVIS Monthly Report"}
    }

    # Top 5 categorías
    top_cats = sorted(data['gastos_por_categoria'].items(), key=lambda x: x[1], reverse=True)[:5]
    if top_cats:
        cat_text = ""
        for cat, monto in top_cats:
            pct = (monto / max(data['gastos'], 1)) * 100
            cat_text += f"**{cat}**: ${monto:,.0f} ({pct:.0f}%)\n"
        embed["fields"].append({
            "name": "📁 Top Categorías",
            "value": cat_text,
            "inline": False
        })

    # Presupuesto vs realidad
    if data['presupuestos']:
        pres_text = ""
        for cat, limite in data['presupuestos'].items():
            gastado = data['gastos_por_categoria'].get(cat, 0)
            pct = (gastado / max(limite, 1)) * 100 if limite > 0 else 0
            emoji = "✅" if pct <= 80 else "⚠️" if pct < 100 else "🚨"
            pres_text += f"{emoji} **{cat}**: ${gastado:,.0f}/${limite:,.0f} ({pct:.0f}%)\n"

        if pres_text:
            embed["fields"].append({
                "name": "🎯 Presupuestos",
                "value": pres_text[:1024],  # Límite Discord
                "inline": False
            })

    # Total transacciones
    embed["fields"].append({
        "name": "📋 Actividad",
        "value": f"{data['num_transacciones']} transacciones registradas",
        "inline": False
    })

    try:
        r = requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
        return r.status_code in [200, 204]
    except Exception as e:
        print(f"Error enviando reporte: {e}")
        return False


def main():
    """Punto de entrada principal."""
    datos = generar_reporte_mes_anterior("iphone_user")
    if datos:
        enviar_a_discord(datos)
        print(f"Reporte enviado: {datos['mes_nombre']} {datos['year']}")
    else:
        print("No se pudo generar el reporte")


if __name__ == "__main__":
    main()