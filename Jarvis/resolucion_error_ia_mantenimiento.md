# Resolución de Error de Mantenimiento en Telegram Bot

## Causa Raíz

El mensaje *"Hola, recibí tu mensaje pero mis servicios de IA están en mantenimiento. Intenta nuevamente en un momento"* ocurría cuando la función `analizar_intencion_mensaje()` en `modules/ai.py` fallaba al comunicarse con la API de Google Gemini. Esto sucedía debido a:

1. **Variable `GEMINI_API_KEY` ausente o no cargada en Vercel**: La SDK `google.generativeai` no podía inicializarse sin la clave API.
2. **Error en la importación/inicialización de la SDK**: Fallos al importar `google.genai` cuando la clave no estaba configurada.
3. **Falla en el parsing del JSON devuelto**: Si la API retornaba un JSON no parseable, el manejo de excepciones no controlado provocaba el mensaje de mantenimiento en lugar de activar el fallback por Regex.

## Solución Aplicada

### 1. Refactorización de `modules/ai.py`

- Implementado `_gemini_api_disponible()` para verificar la presencia de `GEMINI_API_KEY` antes de intentar llamar a la API.
- El flujo ahora tiene **detección prioritaria por Regex** antes de intentar la API: saludos, consultas de presupuestos, cuentas y saldos se detectan directamente por expresiones regulares.
- Los patrones específicos de intención (`REGISTRAR_PRESTAMO`, `REGISTRAR_GASTO`, `ACTUALIZAR_CUENTA_KEBO`) se evalúan **before** las consultas genéricas de balance, evitando que `"saldo"` en comandos como `"Ajustar saldo Nequi a 100k"` interrumpa el patrón correcto.
- El `_fallback_regex_parsing()` funciona de manera autónoma cuando la API está desconfigurada, retornando la intención correcta sin depender de la API.

### 2. Actualización de `modules/intent_handler.py`

- Vinculada la intención `CONSULTAR_BALANCE` con la capa atómica `OrganismoFinanzas` para obtener tarjetas de balance formateadas.
- Implementado manejo de `respuesta_directa` en los datos de intención para respuestas precalculadas.
- Mejorado el logging y las respuestas de fallback con mensajes útiles en lugar de menciones a mantenimiento.

### 3. Integración en `app/routes/telegram.py`

- Implementado `procesar_texto_libre_telegram()` que coordina `analizar_intencion_mensaje()` y `ejecutar_intencion_nlp()`.
- Reemplazado el fallback al template `mantenimiento` por un mensaje útil: *"Recibí tu mensaje. Usa /balance o /ayuda para ver los comandos disponibles."*
- Flujo defensivo: cualquier excepción en el procesamiento NLP responde con un mensaje informativo en lugar de romper la experiencia del usuario.

### 4. Documentación

- Actualizado `[[Jarvis/telegram_bot_webhook.md]]` con el nuevo flujo defensivo por Regex.
- Actualizado `[[Jarvis/parser_nlp_telegram_intentions.md]]` con la lógica de desacoplamiento de Gemini API.
- Actualizado `[[app/core/templates/telegram_templates.md]]`: el template `mantenimiento` ahora contiene un mensaje útil en lugar del mensaje original de estado de mantenimiento.

## Resultado

- El bot ya no muestra el mensaje de mantenimiento para consultas cotidianas cuando la API de Gemini no está disponible.
- Las consultas de presupuestos (`presupuestos`), saldos (`saldo`, `balance`), y saludos (`hola`, `buenas`) se detectan correctamente mediante Regex incluso sin la API.
- Las intenciones financieras (`REGISTRAR_PRESTAMO`, `REGISTRAR_GASTO`, `ACTUALIZAR_CUENTA_KEBO`) funcionan mediante el fallback Regex.
- La experiencia del usuario es mantenida con mensajes orientados a acciones útiles (`/balance`, `/ayuda`) en lugar de estados de mantenimiento.