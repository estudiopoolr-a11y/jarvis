"""app/services/daily_summary/__main__.py - Punto de entrada para el resumen diario."""

from datetime import datetime
from app.services.daily_summary.firebase_init import get_db
from app.services.daily_summary.collector import obtener_datos
from app.services.daily_summary.builder import construir_mensaje
from app.services.daily_summary.sender import enviar_a_discord, deberia_enviar

TZ = datetime.now().astimezone().tzinfo
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1544477914391904406/J4y5ycFy6e-AVHTDoN2-kRh-Su1Dt3ArUAePdOvIFbMTCjAuvKwwrvPqszE1yLeFtmO3"

def main():
    ahora = datetime.now(TZ)

    if not deberia_enviar(ahora):
        print(f"⏸️ Fuera de horario activo ({ahora.hour}:00). No se envía.")
        return

    db = get_db()
    if not db:
        print("❌ No se pudo conectar a Firebase")
        return

    balance, presupuestos, tareas = obtener_datos(db)
    mensaje = construir_mensaje(db, ahora, balance, presupuestos, tareas)
    enviar_a_discord(WEBHOOK_URL, mensaje)

if __name__ == "__main__":
    main()