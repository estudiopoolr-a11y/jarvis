# Parser NLP Telegram Intentions

Este módulo implementa la clasificación de intenciones para mensajes de texto plano enviados al bot de Telegram, permitiendo el registro rápido de finanzas y préstamos sin usar comandos `/`.

## Flujo de Procesamiento
1. **Gemini API**: El mensaje es enviado a Gemini con un prompt de sistema estricto para retornar un JSON.
2. **Fallback Regex**: Si la API falla o el JSON es inválido, se activa un motor de expresiones regulares para extraer entidades básicas.
3. **Intent Handler**: Las intenciones clasificadas se ejecutan mediante `modules/intent_handler.py` llamando a los servicios de base de datos.

## Intenciones Soportadas

| Intención | Descripción | Ejemplo de Texto | Esquema JSON Esperado |
| :--- | :--- | :--- | :--- |
| `REGISTRAR_PRESTAMO` | Registra deuda otorgada o recibida | "Le presté 50k a Carlos" | `{"intent": "REGISTRAR_PRESTAMO", "tipo": "prestado", "persona": "Carlos", "monto": 50000.0}` |
| `REGISTRAR_GASTO` | Registra un gasto en Kebo | "Gasté 15k en taxi con Nequi" | `{"intent": "REGISTRAR_GASTO", "monto": 15000.0, "categoria": "Transporte", "cuenta": "Nequi"}` |
| `ACTUALIZAR_CUENTA_KEBO` | Ajusta el saldo de una cuenta | "Ajustar saldo Nequi a 250mil" | `{"intent": "ACTUALIZAR_CUENTA_KEBO", "cuenta": "Nequi", "nuevo_saldo": 250000.0}` |
| `CONSULTAR_BALANCE` | Consulta resúmenes financieros | "Dame mi balance general" | `{"intent": "CONSULTAR_BALANCE", "filtro": "general"}` |
| `CONVERSACION_GENERAL` | Respuesta natural de JARVIS | "¿Cómo estás?" | `{"intent": "CONVERSACION_GENERAL"}` |

## Enlaces Wiki
- [[Jarvis/telegram_bot_webhook.md]] - Integración con el Webhook.
- [[Jarvis/modulo_prestamos_y_recordatorios.md]] - Lógica de préstamos.
- [[Jarvis/Módulo de Finanzas.md]] - Lógica de Kebo.
- [[Jarvis/estado_proyecto.md]] - Bitácora de implementación.
