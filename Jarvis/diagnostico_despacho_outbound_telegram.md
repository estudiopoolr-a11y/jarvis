# Diagnóstico de Despacho Outbound y Refactorización Asíncrona de Telegram

## Descripción
Nota técnica que documenta el diagnóstico y la refactorización integral del mecanismo de salida (*outbound dispatch*) del bot de Telegram en [[Vercel]], resolviendo problemas de visibilidad de logs y bloqueos síncronos mediante el uso de [[httpx]].AsyncClient.

## Problema Identificado
1. **Falta de visibilidad en Vercel Logs:** Los logs estructurados con `logging.getLogger` en ocasiones no se imprimen de forma directa o inmediata en los *Live Logs* de Vercel Serverless Functions.
2. **Operaciones de red bloqueantes:** El uso previo de `requests.post()` bloqueaba el hilo de ejecución en entornos serverless ASGI.
3. **Incertidumbre en credenciales:** Dificultad para saber desde Vercel si el fallo de entrega se debía a un `TELEGRAM_BOT_TOKEN` ausente, inválido o a rechazo de formato Markdown por parte de Telegram API.

## Solución Aplicada

### 1. Despacho Asíncrono no bloqueante
Se reescribió `despachar_respuesta_telegram()` en [[app/routes/telegram.py]] usando `httpx.AsyncClient`:

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    # Intento 1: Markdown
    res = await client.post(endpoint, json=payload_markdown)
    print(f"📡 [VERCEL OUTBOUND] Intento 1 Markdown Status: {res.status_code} - Body: {res.text}")
    if res.status_code == 200:
        return True

    # Intento 2: Fallback Texto Plano
    res_plano = await client.post(endpoint, json=payload_plano)
    print(f"📡 [VERCEL OUTBOUND] Intento 2 Texto Plano Status: {res_plano.status_code} - Body: {res_plano.text}")
    return res_plano.status_code == 200
```

### 2. Logs de Visibilidad Directa en Vercel
Se incorporaron trazas explícitas mediante `print()` con prefijos semánticos rastreables:
- `📥 [VERCEL INBOUND]`: Payload recibido en el webhook.
- `🔍 [VERCEL PROCESSING]`: Extracción de `chat_id` y contenido procesado.
- `📡 [VERCEL OUTBOUND]`: Intentos 1 y 2 hacia la API de Telegram con código de estado HTTP y cuerpo de respuesta.
- `💥 [VERCEL CRITICAL]`: Ausencia de variable de entorno `TELEGRAM_BOT_TOKEN`.
- `💥 [VERCEL ERROR]`: Fallos de ejecución en el webhook.

### 3. Script de Diagnóstico Local Pre-Push
Se implementó `scripts/test_outbound_telegram.py` para validar credenciales locales y remotas antes de cualquier push:

```bash
python scripts/test_outbound_telegram.py
```

Resultado verificado:
```
🤖 Diagnóstico de Bot en Telegram: {'ok': True, 'result': {'id': 8647134091, 'is_bot': True, 'first_name': 'Jarvis-Asistente', 'username': 'Pooles_Bot', ...}}
✅ Credenciales de Telegram validadas correctamente
```

## Verificación de Variables en Vercel
Para asegurar la correcta entrega en producción:
1. Acceder al panel de Vercel: **Project -> Settings -> Environment Variables**.
2. Verificar que `TELEGRAM_BOT_TOKEN` esté configurada para el entorno **Production**.

## Enlaces Wiki
- [[Jarvis/telegram_bot_webhook.md]] - Arquitectura del webhook de Telegram.
- [[Jarvis/estado_proyecto.md]] - Bitácora de avances y registro de estado.
- [[Índice Principal.md]] - Nodo central de navegación.
- [[FastAPI]]
- [[Vercel]]
- [[Telegram]]
- [[Python]]
- [[httpx]]
