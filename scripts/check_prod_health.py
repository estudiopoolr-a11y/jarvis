import requests  # Cargar librería de peticiones HTTP sincrónicas #
import sys  # Cargar módulo de sistema para manejo de código de salida #


def verificar_salud_remota():  # Función de auditoría del endpoint de salud en Vercel #
    url = "https://jarvis-two-pi-13.vercel.app/api/telegram/health"  # Definir la URL pública de producción #
    print(f"📡 Consultando endpoint de salud en {url}...")  # Imprimir mensaje de progreso #

    try:  # Iniciar bloque defensivo de red #
        resp = requests.get(url, timeout=10)  # Enviar petición GET con tiempo límite de 10 segundos #
        datos = resp.json()  # Convertir respuesta del servidor a estructura JSON #
        print(f"📊 Respuesta HTTP ({resp.status_code}): {datos}")  # Mostrar JSON devuelto por Vercel #

        token_ok = datos.get("telegram_bot_token_present")  # Extraer flag de presencia del token de Telegram #
        gemini_ok = datos.get("gemini_api_key_present")  # Extraer flag de presencia de la clave de Gemini #
        status_ok = datos.get("status") == "ok"  # Extraer estado general de la API #

        if token_ok and gemini_ok and status_ok:  # Confirmar la presencia de todas las claves requeridas #
            print("✅ ÉXITO TOTAL: Variables de entorno inyectadas y operativas en Vercel Serverless")  # Notificar éxito total #
        else:  # Si alguna variable aún no se ha inyectado #
            print(f"⚠️ ADVERTENCIA: Token Telegram: {token_ok} | Gemini Key: {gemini_ok}. Se requiere Redeploy en Vercel.")  # Informar estado incompleto #
    except Exception as e:  # Capturar cualquier fallo de conexión HTTP #
        print(f"💥 Error al intentar conectar con Vercel: {e}")  # Imprimir mensaje de error #


if __name__ == "__main__":  # Punto de entrada del script #
    verificar_salud_remota()  # Ejecutar la función de auditoría #