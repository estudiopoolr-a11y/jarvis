import os  # Cargar módulo OS para leer variables del sistema //
import sys  # Cargar módulo sys para manejo de salidas //
import requests  # Cargar librería requests para llamadas HTTP //

def registrar_webhook_produccion():  # Función para registrar el webhook oficial en Telegram //
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Extraer el token configurado en el entorno //
    if not token:  # Validar si la variable existe localmente //
        print("❌ Error: Define TELEGRAM_BOT_TOKEN en tu entorno local antes de ejecutar")  # Notificar falta //
        sys.exit(1)  # Salir con código de error //

    url_webhook = "https://jarvis-two-pi-13.vercel.app/api/telegram/webhook"  # Definir URL oficial de producción //
    endpoint_set = f"https://api.telegram.org/bot{token}/setWebhook?url={url_webhook}"  # Construir URL del comando setWebhook //

    print(f"📡 Vinculando Webhook de Telegram a: {url_webhook}...")  # Notificar acción //
    res = requests.get(endpoint_set).json()  # Enviar petición GET a Telegram API //
    print(f"Respuesta de Telegram API: {res}")  # Mostrar resultado de la vinculación //

    if res.get("ok"):  # Evaluar si Telegram confirmó el registro //
        print("✅ Webhook registrado y activo con ÉXITO en Telegram")  # Confirmar registro exitoso //
    else:  # Si ocurrió un problema en Telegram //
        print(f"❌ Fallo al registrar Webhook: {res.get('description')}")  # Mostrar descripción del error //


if __name__ == "__main__":  # Punto de entrada del script //
    registrar_webhook_produccion()  # Ejecutar rutina de registro //