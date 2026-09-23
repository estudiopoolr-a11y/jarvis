"""
JARVIS Daily Summary - Envía un resumen automático al canal de Discord vía webhook.
Se ejecuta vía cron job de Render cada 30 minutos.
Solo envía entre las 7am-12pm y 7pm-12am (hora Colombia UTC-5).
"""

# Este archivo delega las responsabilidades a los submódulos.

from app.services.daily_summary.__main__ import main

if __name__ == "__main__":
    main()
