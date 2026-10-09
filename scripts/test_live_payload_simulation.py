import requests  # Cargar librería requests para enviar el payload HTTP #


def ejecutar_simulacion_e2e():  # Función de simulación End-to-End #
    endpoint = "https://jarvis-two-pi-13.vercel.app/api/telegram/webhook"  # Endpoint activo del webhook #
    payload_telegram = {  # Construir objeto JSON simulando un mensaje real de Telegram #
        "update_id": 888888,  # ID único de actualización #
        "message": {  # Objeto contenedor del mensaje #
            "message_id": 5678,  # ID del mensaje #
            "from": {"id": 12345678, "first_name": "Jan"},  # Datos del usuario remitente #
            "chat": {"id": 12345678, "type": "private"},  # Identificador de chat privado #
            "text": "q cuentas tengo"  # Texto exacto enviado en las pruebas #
        }  # Cierre de objeto mensaje #
    }  # Cierre del payload #

    print("🚀 Enviando simulación E2E de consulta de cuentas a Vercel...")  # Imprimir progreso #
    try:  # Iniciar bloque defensivo de red #
        res = requests.post(endpoint, json=payload_telegram, timeout=15)  # Realizar petición POST al webhook #
        print(f"Respuesta Webhook ({res.status_code}): {res.json()}")  # Imprimir código de respuesta e informe JSON #
    except Exception as e:  # Capturar cualquier fallo de conexión HTTP #
        print(f"💥 Error al intentar conectar con Vercel: {e}")  # Imprimir mensaje de error #


if __name__ == "__main__":  # Punto de entrada principal #
    ejecutar_simulacion_e2e()  # Ejecutar la prueba E2E #