# Recuperación del Webhook de Telegram (9 Octubre 2026)

## Causa Raíz

El 9 de octubre de 2026, el bot de Telegram dejó de responder a los mensajes de los usuarios. La causa fue la **falta de invocación explícita a `sendMessage`** en el handler del webhook (`app/routes/telegram.py`).

El flujo anterior procesaba la intención pero **no enviaba la respuesta de vuelta al chat de Telegram**, rompiendo la comunicación bidireccional. El webhook recibía el evento, ejecutaba la lógica atómica, pero la respuesta nunca llegaba al usuario.

## Solución Aplicada

### 1. Función `despachar_respuesta_telegram()` en `app/routes/telegram.py`

Implementada función dedicada para enviar respuestas a Telegram mediante `sendMessage`:

- Envío explícito vía HTTP POST a `https://api.telegram.org/bot{TOKEN}/sendMessage`
- Timeout de 8 segundos para evitar bloqueos
- Logging estructurado con `logger.error`
- Manejo de excepción de conectividad

```python
def despachar_respuesta_telegram(chat_id: int, texto: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN ausente en la ejecución")
        return
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    try:
        requests.post(endpoint, json=payload, timeout=8)
    except Exception as e:
        logger.error(f"❌ Error al enviar respuesta a Telegram: {e}")
```

### 2. Handler del Webhook Simplificado (`atender_telegram_webhook`)

- Parseo del JSON entrante
- Extracción de `chat_id`, `mensaje_texto`, `user_id`
- Procesamiento vía `analizar_intencion_mensaje()` + `ejecutar_intencion_nlp()`
- Envío explícito con `despachar_respuesta_telegram(chat_id, respuesta)`
- Respuesta HTTP 200 OK siempre a Telegram para confirmar recepción

### 3. Script de Registro `scripts/register_telegram_webhook.py`

Script autónomo para diagnóstico y re-registro del Webhook:

```bash
python scripts/register_telegram_webhook.py
```

Ejecuta:
1. `getWebhookInfo` para consultar estado actual
2. `setWebhook` hacia `https://jarvis-two-pi-13.vercel.app/api/telegram/webhook`

## Verificación

- Tests unitarios: 5/5 PASSING
- Webhook re-registrado en Telegram API
- Comunicación bidireccional restablecida

## Referencias

- [[Jarvis/telegram_bot_webhook.md]] - Especificación actualizada
- [[Jarvis/estado_proyecto.md]] - Bitácora de avances
- [[Índice Principal.md]] - Navegación central