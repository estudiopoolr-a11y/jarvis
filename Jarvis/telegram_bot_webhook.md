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
- `GET /api/telegram/health`: Diagnóstico de variables de entorno y conectividad con Telegram API (getMe).

## Función `despachar_respuesta_telegram()`

Nueva función en `app/routes/telegram.py` que encapsula el envío de respuestas a Telegram mediante `sendMessage`. **Refactorizada 2026-10-09** a **asíncrona** con `httpx.AsyncClient` e **impresiones explícitas `print()` para visibilidad en Vercel Live Logs**.

```python
async def despachar_respuesta_telegram(chat_id: int, texto: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("💥 [VERCEL CRITICAL] TELEGRAM_BOT_TOKEN NO EXISTE EN VARIABLES DE ENTORNO DE VERCEL")
        logger.error("❌ TELEGRAM_BOT_TOKEN ausente")
        return False

    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"

    # Intento 1: Formato Markdown enriquecido
    payload_markdown = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.post(endpoint, json=payload_markdown)
            print(f"📡 [VERCEL OUTBOUND] Intento 1 Markdown Status: {res.status_code} - Body: {res.text}")
            if res.status_code == 200:
                return True
        except Exception as e:
            print(f"⚠️ [VERCEL OUTBOUND] Excepción en Intento 1: {e}")

        # Intento 2: Fallback en Texto Plano si falla el Markdown
        payload_plano = {"chat_id": chat_id, "text": texto}
        try:
            res_plano = await client.post(endpoint, json=payload_plano)
            print(f"📡 [VERCEL OUTBOUND] Intento 2 Texto Plano Status: {res_plano.status_code} - Body: {res_plano.text}")
            return res_plano.status_code == 200
        except Exception as e:
            print(f"💥 [VERCEL OUTBOUND] Excepción en Intento 2: {e}")
            return False
```

**Características clave de la refactorización 2026-10-09:**
- ✅ **Asíncrona**: Usa `httpx.AsyncClient` en lugar de `requests` bloqueante.
- ✅ **Visibilidad Vercel**: Logs explícitos con prefijo `[VERCEL OUTBOUND]` aparecen en **Vercel Live Logs**.
- ✅ **Doble Fallback**: Markdown → Texto Plano automático.
- ✅ **Diagnóstico de entorno**: Detecta y loggea ausencia de `TELEGRAM_BOT_TOKEN` en variables de Vercel.

## Script `test_outbound_telegram.py`

Script autónomo en `scripts/test_outbound_telegram.py` para diagnóstico y validación de credenciales **pre-push**:

```bash
python scripts/test_outbound_telegram.py
```

Realiza `getMe` hacia la API de Telegram usando `TELEGRAM_BOT_TOKEN` del entorno (carga `.env` y `.env.local_vercel`).

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] - Registro de cambios y roadmap.
- [[Jarvis/arquitectura_atomic_design_bot.md]] - Documentación detallada del patrón Atomic Design aplicado.
- [[Jarvis/migracion_render_a_vercel.md]] - Guía de migración de Render a Vercel.
- [[Jarvis/diagnostico_error_500_webhook_telegram.md]] - Diagnóstico del error 500 en PowerShell y blindaje del webhook.
- [[app/core/atoms/formatters.py]] - Fuente de los átomos formateadores.
- [[app/core/molecules/cards.py]] - Fuente de las moléculas de tarjetas.
- [[app/core/organisms/finance_organism.py]] - Fuente del organismo de finanzas.
- [[Jarvis/diagnostico_despacho_outbound_telegram.md]] - Diagnóstico detallado del despacho outbound asíncrono y logs de Vercel.

## Fecha
2026-10-08 (actualizado con arquitectura Atomic Design)

## Actualización 2026-10-09 - Parser Ultradefensivo y Blindaje

A partir de 2026-10-09, el endpoint POST /api/telegram/webhook usa extracción segura con .get() multinivel para evitar KeyError:

`python
mensaje = cuerpo.get('message') or cuerpo.get('edited_message') or {}
chat = mensaje.get('chat', {})
chat_id = chat.get('id')
mensaje_texto = (mensaje.get('text') or '').strip()
`

Se creó `scripts/diagnostico_live_telegram.py` para getMe / getWebhookInfo / setWebhook con drop_pending_updates.
Se creó `scripts/test_live_payload_simulation.py` para prueba E2E del payload real.

Nota técnica: [[Jarvis/diagnostico_y_blindaje_webhook.md]]
Enlaces: [[Jarvis/estado_proyecto.md]] [[Índice Principal.md]]


## 2026-10-09 - Doble Fallback de Envío

`despachar_respuesta_telegram` implementa reintento automático:
- Intento 1: Markdown con parse_mode.
- Intento 2: Texto plano sin parse_mode si status_code != 200.

Garantiza entrega incluso ante rechazos de formato de Telegram.

Enlaces: [[FastAPI]] [[Vercel]] [[Atomic Design]]


## 2026-10-09 - Refactorización Asíncrona y Logs de Visibilidad Vercel

`despachar_respuesta_telegram` reescrita completamente:
- **httpx.AsyncClient** con timeout 10s para operaciones no bloqueantes.
- **Logs [VERCEL OUTBOUND]** explícitos con `print()` para debugging en **Vercel Live Logs**.
- **Validación de `TELEGRAM_BOT_TOKEN`** en entorno Vercel con log crítico visible.
- **set-webhook** también asíncrono con logs de visibilidad.

Script de diagnóstico pre-push: `scripts/test_outbound_telegram.py` valida credenciales vía `getMe` antes de desplegar.

Enlaces: [[FastAPI]] [[Vercel]] [[httpx]] [[Atomic Design]]