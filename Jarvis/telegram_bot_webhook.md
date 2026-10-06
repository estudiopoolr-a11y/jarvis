## Procedimiento de Activación del Webhook
- SetWebhook: `https://api.telegram.org/bot{TOKEN}/setWebhook?url={URL_WEBHOOK}`
- Verificación: `https://api.telegram.org/bot{TOKEN}/getWebhookInfo`
# Telegram Bot Serverless (Vercel Webhook)

## Descripción
Implementación de la interfaz de comunicación con Telegram utilizando el modelo de **Webhooks** en lugar de Polling. Esta arquitectura es indispensable para el despliegue en entornos serverless como **Vercel**, donde no es posible mantener un proceso de escucha activo y persistente.

## Funcionamiento Técnico
El bot ya no "pregunta" a Telegram si hay mensajes nuevos. En su lugar, Telegram envía una petición HTTP POST al endpoint configurado cada vez que ocurre un evento.

### Flujo de Datos
1. **Telegram API** $\rightarrow$ `POST /api/telegram/webhook` $\rightarrow$ **FastAPI (Vercel)**.
2. El endpoint recibe el JSON, extrae el texto y el `chat_id`.
3. Se procesa la intención mediante el flujo de IA:
   - **NLP Local**: Parsers determinísticos rápidos.
   - **Hermes Agent**: Razonamiento ReAct vía LLM (Gemini/Nvidia).
4. La respuesta se envía mediante una petición asíncrona a `sendMessage` de la API de Telegram.

## Endpoints
- `POST /api/telegram/webhook`: Punto de entrada para los eventos de Telegram.
- `GET /api/telegram/set-webhook`: Helper para registrar la URL del webhook en los servidores de Telegram.

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] - Registro de cambios y roadmap.
- [[Jarvis/arquitectura_backend.md]] - Detalles de la estructura del servidor.
- [[Jarvis/migracion_render_a_vercel.md]] - Guía de migración de Render a Vercel.
- [[Jarvis/diagnostico_error_500_webhook_telegram.md]] - Diagnóstico del error 500 en PowerShell y blindaje del webhook.

## Fecha
2026-10-06
