import os  # Cargar módulo del sistema para acceder a variables de entorno #
import sys  # Cargar módulo de sistema para manejo de salidas #
import requests  # Cargar librería de peticiones HTTP #
from dotenv import load_dotenv  # Cargar librería para variables de entorno locales #

load_dotenv()  # Cargar variables desde el archivo .env si existe #
load_dotenv(".env.local_vercel")  # Cargar variables de Vercel como fallback para validación local #


def verificar_salida_telegram():  # Función de verificación local de credenciales y despacho #
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Extraer el token configurado en las variables de entorno #
    if not token:  # Validar presencia del token de Telegram #
        print("❌ ERROR LOCAL: TELEGRAM_BOT_TOKEN no está definido en el entorno local (.env ni .env.local_vercel)")  # Notificar error local #
        sys.exit(1)  # Salir con código de fallo #

    url_get_me = f"https://api.telegram.org/bot{token}/getMe"  # Construir URL de verificación de Bot #
    resp_me = requests.get(url_get_me).json()  # Realizar petición de verificación a Telegram API #
    print(f"🤖 Diagnóstico de Bot en Telegram: {resp_me}")  # Imprimir respuesta de credenciales #

    if not resp_me.get("ok"):  # Evaluar si el token fue rechazado por Telegram #
        print("❌ ERROR: El TELEGRAM_BOT_TOKEN es inválido o fue revocado")  # Notificar token inválido #
        sys.exit(1)  # Salir con código de error #
    else:  # Si las credenciales son válidas #
        print("✅ Credenciales de Telegram validadas correctamente")  # Confirmar credenciales operativas #


if __name__ == "__main__":  # Bloque de entrada del script #
    verificar_salida_telegram()  # Ejecutar rutina de verificación #