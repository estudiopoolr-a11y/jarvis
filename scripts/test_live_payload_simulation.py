"""Prueba E2E en vivo: simula el payload exacto de la captura (Fase 2.3).

Envía un POST real contra Vercel con la frase
"Q presupuestos hay Pa septiembre" y valida respuesta 200 {"status": "ok"}.

Uso:
    python scripts/test_live_payload_simulation.py
"""

import sys

import requests


def simular_envio_captura() -> None:
    """Simula el mensaje de la captura de pantalla contra producción."""
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    url_vercel = "https://jarvis-two-pi-13.vercel.app/api/telegram/webhook"
    payload_simulado = {
        "update_id": 999999,
        "message": {
            "message_id": 1234,
            "from": {"id": 12345678, "first_name": "Jan"},
            "chat": {"id": 12345678, "type": "private"},
            "text": "Q presupuestos hay Pa septiembre",
        },
    }

    print("📡 Enviando simulación de payload de captura a Vercel...")
    try:
        resp = requests.post(url_vercel, json=payload_simulado, timeout=10)
    except requests.RequestException as exc:
        print(f"❌ Fallo de red contra Vercel: {exc}")
        sys.exit(1)

    print(f"Respuesta de Vercel (Status {resp.status_code}): {resp.json()}")

    exitoso = resp.status_code == 200 and resp.json().get("status") == "ok"
    print("✅ SIMULACIÓN EXITOSA" if exitoso else "❌ SIMULACIÓN FALLIDA")
    sys.exit(0 if exitoso else 1)


if __name__ == "__main__":
    simular_envio_captura()
