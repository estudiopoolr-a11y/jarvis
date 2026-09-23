"""app/services/daily_summary/sender.py - Envía mensajes al webhook de Discord."""

import requests
from datetime import datetime

def enviar_a_discord(webhook_url: str, mensaje: str):
    """Envía el mensaje al webhook de Discord."""
    payload = {
        "content": mensaje,
        "username": "JARVIS",
        "avatar_url": None
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 204:
            print(f"✅ Resumen enviado a las {datetime.now().strftime('%H:%M')}")
        else:
            print(f"⚠️ Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"❌ Error enviando: {e}")

def deberia_enviar(hora: datetime) -> bool:
    """Verifica si está en la ventana horaria activa (7am-12pm o 7pm-12am)."""
    h = hora.hour
    return (7 <= h < 12) or (19 <= h < 24)