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
