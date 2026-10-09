import asyncio  # Cargar módulo asyncio //
import inspect  # Cargar módulo inspect para validar corrutinas //
from app.routes.telegram import atender_telegram_webhook, resolver_llamada_segura  # Importar controlador y helper //
from modules.ai import analizar_intencion_mensaje  # Importar analizador //
from modules.intent_handler import ejecutar_intencion_nlp  # Importar ejecutor //


async def probar_flujo_definitivo():  # Función de prueba integral //
    print("🧪 [1/2] Evaluando resolver_llamada_segura con NLP e Intent Handler...")  # Imprimir paso 1 //
    texto = "q cuentas tengo"  # Texto exacto reportado en los logs //

    intent_data = await resolver_llamada_segura(analizar_intencion_mensaje, texto)  # Probar resolución de intención //
    print(f"   Intent Data devuelto: {intent_data} (Tipo: {type(intent_data)})")  # Imprimir resultado //

    respuesta = await resolver_llamada_segura(ejecutar_intencion_nlp, intent_data)  # Probar ejecución de respuesta //
    print(f"   Respuesta devuelta: {respuesta} (Tipo: {type(respuesta)})")  # Imprimir respuesta //

    print("\n🧪 [2/2] Simulando Webhook completo con Mock Request...")  # Imprimir paso 2 //
    class MockRequest:  # Clase falsa para simular la petición de FastAPI //
        async def json(self):  # Método asíncrono json() //
            return {  # Retornar payload simulado //
                "update_id": 99999,  # Update ID ficticio //
                "message": {  # Objeto mensaje //
                    "message_id": 100,  # ID del mensaje //
                    "chat": {"id": 8418729793},  # Chat ID de Telegram //
                    "text": "q cuentas tengo"  # Texto de consulta //
                }  # Cierre de objeto mensaje //
            }  # Cierre de payload //

    res = await atender_telegram_webhook(MockRequest())  # Invocar el controlador //
    print(f"   Resultado del Webhook: {res}")  # Imprimir respuesta del webhook //
    assert res == {"status": "ok"}, "El webhook debe retornar {'status': 'ok'}"  # Verificar aserción //
    print("\n✅ PRUEBAS INTEGRADAS COMPLETADAS CON ÉXITO SIN EXCEPCIONES")  # Confirmar éxito //


if __name__ == "__main__":  # Punto de entrada //
    asyncio.run(probar_flujo_definitivo())  # Ejecutar prueba //