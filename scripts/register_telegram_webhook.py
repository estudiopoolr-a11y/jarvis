#!/usr/bin/env python3
"""
Script de diagnóstico y re-registro de Webhook en Telegram API.
Vincula el endpoint de Vercel con el bot de Telegram.
"""
import os
import sys
import requests


def redefinir_webhook_telegram():
    """Función principal para re-registrar el Webhook."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN no configurado en entorno")
        sys.exit(1)

    url_base = f"https://api.telegram.org/bot{token}"
    target_webhook = "https://jarvis-two-pi-13.vercel.app/api/telegram/webhook"

    print("📡 Consultando estado actual del Webhook en Telegram...")
    info_resp = requests.get(f"{url_base}/getWebhookInfo").json()
    print(f"Estado actual: {info_resp}")

    print(f"🔗 Registrando nuevo Webhook hacia: {target_webhook}")
    set_resp = requests.post(f"{url_base}/setWebhook", json={"url": target_webhook}).json()
    print(f"Resultado del registro: {set_resp}")


if __name__ == "__main__":
    redefinir_webhook_telegram()