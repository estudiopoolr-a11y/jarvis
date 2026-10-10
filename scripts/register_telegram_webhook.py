import os  # Importar módulo os para lectura de variables de entorno #
import sys  # Importar módulo sys para control de salidas de error #
import requests  # Importar librería requests para llamadas HTTP #

def purgar_y_registrar_webhook():  # Función para resetear y registrar el webhook #
  token = os.getenv(
      "TELEGRAM_BOT_TOKEN"
  )  # Extraer el token del bot desde el entorno local #
  if not token:  # Validar existencia de la credencial #
    print(
        "❌ Error: TELEGRAM_BOT_TOKEN no definido en el entorno local."
    )  # Mensaje de error #
    sys.exit(1)  # Salir con código de error #

  url_webhook = "https://jarvis-two-pi-13.vercel.app/api/telegram/webhook"  # URL oficial de producción en Vercel #
  endpoint_set = f"https://api.telegram.org/bot{token}/setWebhook?url={url_webhook}&drop_pending_updates=true"  # Configurar Webhook y purgar eventos acumulados #

  print(
      f"📡 Purgando colas pendientes y registrando Webhook en: {url_webhook}..."
  )  # Imprimir progreso #
  res = requests.get(endpoint_set).json()  # Enviar petición GET a Telegram API #
  print(f"Respuesta de Telegram API: {res}", flush=True)  # Mostrar respuesta #

  if res.get(
      "ok"
  ):  # Evaluar si la operación fue exitosa según la respuesta de Telegram #
    print(
        "✅ Webhook purgado, re-registrado y activo con ÉXITO en Telegram."
    )  # Confirmación de éxito #
  else:  # Si la API retorna un fallo #
    print(
        f"❌ Fallo al registrar Webhook: {res.get('description')}"
    )  # Mostrar descripción del error #

if __name__ == "__main__":  # Punto de entrada principal del script #
  purgar_y_registrar_webhook()  # Ejecutar rutina de purga y registro #