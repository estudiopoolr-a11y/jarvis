"""Diagnóstico en vivo de la API de Telegram (Fase 2.1).

Verifica el token con getMe, inspecciona getWebhookInfo y re-registra
el webhook con drop_pending_updates=True para limpiar actualizaciones
atascadas que provocan bucles de reintento.

Uso:
    python scripts/diagnostico_live_telegram.py
"""

import os
import sys

import requests
from dotenv import load_dotenv


def ejecutar_diagnostico_live() -> None:
    """Ejecuta la rutina completa de diagnóstico contra Telegram API."""
    load_dotenv()

    # Configurar stdout para UTF-8 si es posible
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ ERROR CRÍTICO: TELEGRAM_BOT_TOKEN no configurado")
        sys.exit(1)

    url_base = f"https://api.telegram.org/bot{token}"

    # 1. Probar conectividad con getMe
    print("🔍 [1/3] Verificando credenciales del Bot con getMe...")
    try:
        bot_info = requests.get(f"{url_base}/getMe", timeout=10).json()
    except requests.RequestException as exc:
        print(f"❌ Fallo de red en getMe: {exc}")
        sys.exit(1)
    print(f"   Resultado getMe: {bot_info}")

    # 2. Consultar estado y errores en getWebhookInfo
    print("\n🔍 [2/3] Inspeccionando estado del Webhook con getWebhookInfo...")
    try:
        webhook_info = requests.get(f"{url_base}/getWebhookInfo", timeout=10).json()
    except requests.RequestException as exc:
        print(f"❌ Fallo de red en getWebhookInfo: {exc}")
        sys.exit(1)
    print(f"   Resultado getWebhookInfo: {webhook_info}")
    ultimo_error = webhook_info.get("result", {}).get("last_error_message")
    if ultimo_error:
        print(f"   ⚠️ Último error reportado por Telegram: {ultimo_error}")

    # 3. Re-registrar Webhook forzando flush de actualizaciones pendientes
    target_url = "https://jarvis-two-pi-13.vercel.app/api/telegram/webhook"
    print(f"\n🔗 [3/3] Re-registrando Webhook en {target_url}...")
    try:
        set_resp = requests.post(
            f"{url_base}/setWebhook",
            json={"url": target_url, "drop_pending_updates": True},
            timeout=10,
        ).json()
    except requests.RequestException as exc:
        print(f"❌ Fallo de red en setWebhook: {exc}")
        sys.exit(1)
    print(f"   Resultado setWebhook: {set_resp}")

    ok_general = (
        bot_info.get("ok") is True
        and webhook_info.get("ok") is True
        and set_resp.get("ok") is True
    )
    print("\n✅ DIAGNÓSTICO COMPLETO" if ok_general else "\n❌ DIAGNÓSTICO CON FALLOS")
    sys.exit(0 if ok_general else 1)


if __name__ == "__main__":
    ejecutar_diagnostico_live()
