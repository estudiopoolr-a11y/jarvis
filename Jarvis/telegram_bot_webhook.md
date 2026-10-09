## Procedimiento de Activación del Webhook
- SetWebhook: `https://api.telegram.org/bot{TOKEN}/setWebhook?url={URL_WEBHOOK}`
- Verificación: `https://api.telegram.org/bot{TOKEN}/getWebhookInfo`
# Telegram Bot Serverless (Vercel Webhook) — Arquitectura Atomic Design

## Descripción
Implementación de la interfaz de comunicación con Telegram utilizando el modelo de **Webhooks** en lugar de Polling. Esta arquitectura es indispensable para el despliegue en entornos serverless como **Vercel**, donde no es posible mantener un proceso de escucha activo y persistente.

> **Nota de Arquitectura:** El bot opera bajo el patrón **Atomic Design** (<- ver [[Jarvis/arquitectura_atomic_design_bot.md]]). Las capas inferiores (`app/core/`) son reutilizables e independientes del handler de Telegram.

## Capas Atómicas Implementadas

### 1. Átomos (`app/core/atoms/formatters.py`)
Funciones primitivas e inmutables:
- `atomo_formatear_moneda()` — Formatea números a pesos colombianos COP.
- `atomo_obtener_emoji_estado()` — Retorna emoji semafórico según porcentaje.

### 2. Moléculas (`app/core/molecules/cards.py`)
Componentes ensamblados a partir de átomos:
- `molecula_tarjeta_balance()` — Tarjeta de balance consolidado.
- `molecula_tarjeta_presupuesto()` — Tarjeta por categoría presupuestal.

### 3. Organismos (`app/core/organisms/finance_organism.py`)
Módulos con lógica de negocio que orquestan moléculas y fuentes de datos:
- `OrganismoFinanzas` — Coordina consultas financieras y retorna tarjetas formateadas.

### 4. Plantillas (`app/core/templates/telegram_templates.py`)
Formatos estructurales reutilizables para respuestas de Telegram.

### 5. Página/Ruta (`app/routes/telegram.py`)
Consumidora de organismos y plantillas; punto de entrada ASGI.

## Flujo de Datos (Atomic Design)
```
Petición Telegram POST
  → Route (/api/telegram/webhook)
    → OrganismoFinanzas.obtener_resumen_organismo()
      → molecula_tarjeta_balance()
        → atomo_obtener_emoji_estado() + atomo_formatear_moneda()
      → Respuesta Markdown ensamblada
```

## Funcionamiento Técnico
El bot ya no "pregunta" a Telegram si hay mensajes nuevos. En su lugar, Telegram envía una petición HTTP POST al endpoint configurado cada vez que ocurre un evento.

### Flujo de Datos
1. **Telegram API** $\rightarrow$ `POST /api/telegram/webhook` $\rightarrow$ **FastAPI (Vercel)**.
2. El endpoint recibe el JSON, extrae el texto y el `chat_id`.
3. Se procesa la intención mediante el flujo de IA:
   - **NLP Local**: Parsers determinísticos rápidos.
   - **Hermes Agent**: Razonamiento ReAct vía LLM (Gemini/Nvidia).
4. La respuesta se envía mediante una petición asíncrona a `sendMessage` de la API de Telegram.

## Manejo Defensivo en Entornos Serverless
Para prevenir el infame error `FUNCTION_INVOCATION_FAILED` en los despliegues perezosos de Vercel:
- **Importaciones Diferidas (Lazy loading):** Todo componente pesado o ajeno que no deba romper el levantamiento de `FastAPI()` (como los motores de NLP o Gemini en `modules.ai`) se importará exclusivamente dentro de la propia función POST del webhook, y no en la parte superior del archivo.
- **Respuesta Resiliente (Fallback HTTP 200 OK):** Dado que Telegram bloquea automáticamente el webhook al detectar secuencias de estado 500, cualquier rama de excepción del manejo de red se atrapa e informa ignorando el estado, respondiendo artificialmente un `Response(status_code=200, content="OK")`.

## Endpoints
- `POST /api/telegram/webhook`: Punto de entrada para los eventos de Telegram.
- `GET /api/telegram/set-webhook`: Helper para registrar la URL del webhook en los servidores de Telegram.

## Función `despachar_respuesta_telegram()`

Nueva función en `app/routes/telegram.py` que encapsula el envío de respuestas a Telegram mediante `sendMessage`. Garantiza envío explícito vía HTTP POST con timeout de 8s y logging estructurado.

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

## Script `register_telegram_webhook.py`

Script autónomo en `scripts/register_telegram_webhook.py` para diagnóstico y re-registro del Webhook:

```bash
python scripts/register_telegram_webhook.py
```

Realiza `getWebhookInfo` y `setWebhook` hacia `https://jarvis-two-pi-13.vercel.app/api/telegram/webhook`.

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] - Registro de cambios y roadmap.
- [[Jarvis/arquitectura_atomic_design_bot.md]] - Documentación detallada del patrón Atomic Design aplicado.
- [[Jarvis/migracion_render_a_vercel.md]] - Guía de migración de Render a Vercel.
- [[Jarvis/diagnostico_error_500_webhook_telegram.md]] - Diagnóstico del error 500 en PowerShell y blindaje del webhook.
- [[app/core/atoms/formatters.py]] - Fuente de los átomos formateadores.
- [[app/core/molecules/cards.py]] - Fuente de las moléculas de tarjetas.
- [[app/core/organisms/finance_organism.py]] - Fuente del organismo de finanzas.

## Fecha
2026-10-08 (actualizado con arquitectura Atomic Design)

## Actualizaci�n 2026-10-09 - Parser Ultradefensivo y Blindaje

A partir de 2026-10-09, el endpoint POST /api/telegram/webhook usa extracci�n segura con .get() multinivel para evitar KeyError:

`python
mensaje = cuerpo.get('message') or cuerpo.get('edited_message') or {}
chat = mensaje.get('chat', {})
chat_id = chat.get('id')
mensaje_texto = (mensaje.get('text') or '').strip()
`"n
Se cre� scripts/diagnostico_live_telegram.py para getMe / getWebhookInfo / setWebhook con drop_pending_updates.
Se cre� scripts/test_live_payload_simulation.py para prueba E2E del payload real.

Nota t�cnica: [[Jarvis/diagnostico_y_blindaje_webhook.md]]
Enlaces: [[Jarvis/estado_proyecto.md]] [[�ndice Principal.md]]


## 2026-10-09 - Doble Fallback de Env�o

despachar_respuesta_telegram implementa reintento autom�tico:
- Intento 1: Markdown con parse_mode.
- Intento 2: Texto plano sin parse_mode si status_code != 200.

Garantiza entrega incluso ante rechazos de formato de Telegram.

Enlaces: [[FastAPI]] [[Vercel]] [[Atomic Design]]

