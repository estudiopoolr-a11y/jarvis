import asyncio  # Cargar módulo asyncio para pruebas asíncronas //
import inspect  # Cargar módulo inspect para validar corrutinas //
from app.routes.telegram import atender_telegram_webhook  # Importar controlador del Webhook //
from modules.ai import analizar_intencion_mensaje  # Importar analizador de intención //
from modules.intent_handler import ejecutar_intencion_nlp  # Importar enrutador NLP //


async def probar_flujo_completo():  # Función principal de prueba integrada //
    print("🧪 [1/3] Probando tipos de retorno de NLP e Intent Handler...")  # Imprimir paso 1 //
    texto_prueba = "Q cuentas tengo"  # Texto reportado en los logs de producción //

    # 1. Probar analizador //
    if inspect.iscoroutinefunction(analizar_intencion_mensaje):  # Evaluar si es asíncrona //
        intent_data = await analizar_intencion_mensaje(texto_prueba)  # Ejecutar asíncronamente //
    else:  # Si es síncrona //
        intent_data = analizar_intencion_mensaje(texto_prueba)  # Ejecutar síncronamente //
    print(f"   Resultado intent_data: {intent_data} (Tipo: {type(intent_data)})")  # Imprimir tipo devuelto //

    # 2. Probar ejecutor de intenciones //
    if inspect.iscoroutinefunction(ejecutar_intencion_nlp):  # Evaluar si es asíncrona //
        respuesta = await ejecutar_intencion_nlp(intent_data)  # Ejecutar asíncronamente //
    else:  # Si es síncrona //
        respuesta = ejecutar_intencion_nlp(intent_data)  # Ejecutar síncronamente //
    print(f"   Resultado respuesta: {respuesta} (Tipo: {type(respuesta)})")  # Imprimir tipo de respuesta //

    print("\n🧪 [2/3] Simulando petición Webhook completa con Mock Request...")  # Imprimir paso 2 //
    class MockRequest:  # Crear clase falsa para simular la petición de FastAPI //
        async def json(self):  # Método asíncrono json() //
            return {  # Retornar payload simulado de Telegram //
                "update_id": 11111,  # Update ID ficticio //
                "message": {  # Objeto mensaje //
                    "message_id": 99,  # Message ID ficticio //
                    "chat": {"id": 8418729793},  # Chat ID real reportado en Vercel Logs //
                    "text": "Q cuentas tengo"  # Texto exacto enviado por el usuario //
                }  # Cierre de objeto mensaje //
            }  # Cierre de diccionario payload //

    res_webhook = await atender_telegram_webhook(MockRequest())  # Invocar el webhook //
    print(f"   Resultado Webhook: {res_webhook}")  # Mostrar resultado del webhook //
    assert res_webhook == {"status": "ok"}, "El webhook debe devolver {'status': 'ok'}"  # Validar aserción //

    print("\n🧪 [3/3] Validando tipos de retorno de funciones NLP...")  # Imprimir paso 3 //
    print(f"   analizar_intencion_mensaje es coroutine: {inspect.iscoroutinefunction(analizar_intencion_mensaje)}")  # Reportar tipo //
    print(f"   ejecutar_intencion_nlp es coroutine: {inspect.iscoroutinefunction(ejecutar_intencion_nlp)}")  # Reportar tipo //
    print("\n✅ [3/3] Pruebas exhaustivas superadas con ÉXITO sin excepciones de await.")  # Imprimir confirmación //


if __name__ == "__main__":  # Punto de entrada del script //
    asyncio.run(probar_flujo_completo())  # Ejecutar el bucle de eventos asíncrono //