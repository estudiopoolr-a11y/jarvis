import os
import sys
from app.routes.telegram import despachar_respuesta_telegram

def probar_envio_directo():
    chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")
    if not chat_id:
        print("⚠️ TELEGRAM_TEST_CHAT_ID no configurado. Usando chat de prueba 12345678...")
        chat_id = 12345678

    print(f"🧪 Probando despachar_respuesta_telegram para chat {chat_id}...")
    exito = despachar_respuesta_telegram(int(chat_id), "🤖 *Prueba de Conexión JARVIS*\n\nSi lees esto, el despacho atómico funciona correctamente.")
    print(f"Resultado de envío: {'✅ ÉXITO' if exito else '❌ FALLO'}")

if __name__ == "__main__":
    probar_envio_directo()
