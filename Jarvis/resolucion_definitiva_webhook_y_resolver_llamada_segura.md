# Resolución Definitiva Webhook Telegram y Wrapper resolver_llamada_segura

## Descripción
Nota técnica que documenta la solución definitiva del error `TypeError: object dict can't be used in 'await' expression` en el webhook de Telegram, implementando un **wrapper universal async/sync** (`resolver_llamada_segura`) y un mecanismo de **notificación de errores en Telegram** para evitar el silencio del bot.

## Problemas Identificados

### Problema 1: Excepción Persistente de Await en Dict
Los logs de Vercel reportaban repetidamente:
```
[VERCEL ERROR] Fallo critico en webhook: object dict can't be used in 'await' expression
```
**Causa raíz:** `analizar_intencion_mensaje()` es una función **síncrona** (`def`, no `async def`) que retorna un `dict`. Al aplicar `await` directamente sobre ella, Python lanza `TypeError: object dict can't be used in 'await' expression`.

### Problema 2: Silencio Absoluto del Bot en Errores
Cuando ocurría una excepción en el procesamiento del webhook, el bot no notificaba al usuario. El mensaje se perdía sin rastro, dejando al usuario sin retroalimentación.

### Problema 3: Webhook Desalineado en Telegram API
En ocasiones, la URL registrada en Telegram API no coincidía con la URL real de producción en Vercel, causando que Telegram no enviara los payloads al endpoint correcto.

## Solución Aplicada

### 1. Wrapper Universal `resolver_llamada_segura()`

Se creó una función helper que maneja cualquier combinación de función sync/async y retorno sync/async:

```python
import inspect

async def resolver_llamada_segura(func, *args, **kwargs):
    """Ejecuta una función de forma segura, inspeccionando si es corrutina o síncrona."""
    if inspect.iscoroutinefunction(func):      # Función declarada con async def
        res = await func(*args, **kwargs)       # Await directo
    else:                                       # Función síncrona estándar
        res = func(*args, **kwargs)             # Invocación directa #
    
    if inspect.isawaitable(res):                # El resultado es awaitable (Future, etc.)
        res = await res                         # Resolver deferido
    
    return res
```

**Ventajas:**
- Maneja funciones `async def` con retorno normal
- Maneja funciones `def` (síncronas) con retorno de corrutinas
- Maneja funciones `def` con retorno de valores directos (dict, str, etc.)
- Evita completamente `TypeError: object dict can't be used in 'await' expression`

**Uso en el webhook:**
```python
intent_data = await resolver_llamada_segura(analizar_intencion_mensaje, mensaje_texto)
respuesta = await resolver_llamada_segura(ejecutar_intencion_nlp, intent_data)
```

### 2. Notificación de Error en Telegram (Anti-Silencio)

Se agregó notificación explícita al usuario cuando ocurre una excepción no prevista:

```python
except Exception as e:
    print(f"[VERCEL ERROR] Fallo critico en webhook: {e}")
    if chat_id:  # Si logramos identificar el chat_id antes de la falla //
        await despachar_respuesta_telegram(chat_id, f"⚠️ Ocurrió un error interno en el bot: {str(e)[:100]}")
    return {"status": "error_handled"}
```

**Comportamiento:**
- Si el error ocurre antes de extraer `chat_id` → log en Vercel, sin notificación (no se puede contactar al usuario)
- Si el error ocurre después de extraer `chat_id` → mensaje de error enviado al usuario en Telegram
- El usuario siempre recibe feedback, nunca queda en silencio

### 3. Script de Registro Directo de Webhook

Se creó `scripts/register_telegram_webhook.py` para garantizar que la URL del webhook esté correctamente registrada en Telegram API:

```bash
python scripts/register_telegram_webhook.py
```

**Resultado esperado:**
```
📡 Vinculando Webhook de Telegram a: https://jarvis-two-pi-13.vercel.app/api/telegram/webhook...
Respuesta de Telegram API: {'ok': True, 'result': True, 'description': 'Webhook was set'}
✅ Webhook registrado y activo con ÉXITO en Telegram
```

## Verificación

### Prueba de Carga del Módulo
```bash
python -c "from app.routes.telegram import atender_telegram_webhook, resolver_llamada_segura; print('OK')"
```
**Resultado:** `OK` (sin errores de importación)

### Prueba Integral del Flujo
```bash
python scripts/test_exhaustive_local.py
```
**Resultado:**
```
🧪 [1/3] Probando tipos de retorno de NLP e Intent Handler...
   Resultado intent_data: {'intent': 'CONSULTAR_BALANCE', 'filtro': 'general'} (Tipo: <class 'dict'>)
   Resultado respuesta: 🟢 *Balance*: $1.500.000 COP ... (Tipo: <class 'str'>)

🧪 [2/3] Simulando petición Webhook completa con Mock Request...
   Resultado Webhook: {'status': 'ok'}

✅ [3/3] Pruebas exhaustivas superadas con ÉXITO sin excepciones.
```

### Batería de Tests Unitarios
```bash
python -m unittest discover -v tests
```
**Resultado:** `Ran 5 tests in ~27s — OK`

### Despliegue en Producción
- `GET /api/telegram/health` → `200` + `telegram_bot_token_present: true`, `gemini_api_key_present: true`
- `POST /api/telegram/webhook` → `200` + `{'status': 'ok'}`

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] — Bitácora de avances y registro de estado.
- [[Índice Principal.md]] — Nodo central de navegación.
- [[FastAPI]] — Framework API.
- [[Vercel]] — Infraestructura serverless.
- [[Telegram]] — Plataforma de mensajería.
- [[Python]] — Lenguaje de programación.