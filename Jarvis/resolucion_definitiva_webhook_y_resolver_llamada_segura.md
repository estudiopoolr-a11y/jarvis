# Resolución Definitiva Webhook Telegram y Wrapper resolver_llamada_segura

## Descripción
Nota técnica que documenta la solución definitiva del error persistente `object dict can't be used in 'await' expression` en el webhook de Telegram, implementando un **wrapper universal async/sync** (`resolver_llamada_segura`) y un mecanismo de **notificación de errores a Telegram** para evitar el silencio del bot.

## Problemas Identificados

### Problema 1: Excepción Persistente de Await en Dict
Los logs de Vercel reportaban repetidamente:
```
[VERCEL ERROR] Fallo critico en webhook: object dict can't be used in 'await' expression
```
Esto ocurría porque `analizar_intencion_mensaje()` es una función **síncrona** (`def`, no `async def`) que retorna un `dict`. Al aplicar `await` directamente sobre ella, Python lanzaba `TypeError`.

### Problema 2: Silencio Absoluto del Bot en Errores
Cuando ocurría una excepción en el procesamiento del webhook, el bot no notificaba al usuario. El mensaje se perdía sin rastro.

### Problema 3: Webhook Desalineado en Telegram API
En ocasiones, la URL registrada en Telegram API no coincidía con la URL real de producción en Vercel.

## Solución Aplicada

### 1. Wrapper Universal `resolver_llamada_segura()`

Función helper que maneja cualquier combinación de función sync/async y retorno sync/async:

```python
import inspect

async def resolver_llamada_segura(func, *args, **kwargs):
    if inspect.iscoroutinefunction(func):
        res = await func(*args, **kwargs)
    else:
        res = func(*args, **kwargs)

    if inspect.isawaitable(res):
        res = await res

    return res
```

**Uso en el webhook:**
```python
intent_data = await resolver_llamada_segura(analizar_intencion_mensaje, mensaje_texto)
respuesta = await resolver_llamada_segura(ejecutar_intencion_nlp, intent_data)
```

### 2. Notificación de Error en Telegram (Anti-Silencio)

Se agregó notificación explícita al usuario cuando ocurre una excepción:
```python
except Exception as e:
    print(f"[VERCEL ERROR] Fallo critico en webhook: {e}")
    if chat_id:
        await despachar_respuesta_telegram(chat_id, f"Error interno: {str(e)[:100]}")
    return {"status": "error_handled"}
```

### 3. Script de Registro Directo de Webhook

`scripts/register_telegram_webhook.py` garantiza que la URL del webhook esté correctamente registrada:
```bash
python scripts/register_telegram_webhook.py
# Resultado: {"ok": True, "result": True, "description": "Webhook is already set"}
```

## Verificación Local

```bash
# Prueba de carga del modulo
python -c "from app.routes.telegram import atender_telegram_webhook, resolver_llamada_segura; print('OK')"
# OK

# Prueba integral del flujo
python scripts/test_exhaustive_local.py
# ✅ PRUEBAS INTEGRADAS COMPLETADAS CON EXITO SIN EXCEPCIONES

# Tests unitarios
python -m unittest discover -v tests
# Ran 5 tests in ~27s — OK
```

## Estado de las Rutas FastAPI
```
  {'HEAD', 'GET'} /openapi.json
  {'HEAD', 'GET'} /docs
  {'HEAD', 'GET'} /docs/oauth2-redirect
  {'HEAD', 'GET'} /redoc
  {'GET'} /api/debug
  {'GET'} /debug
  {'GET'} /
  {'POST'} /api/telegram/webhook
  {'GET'} /api/telegram/health
  {'GET'} /api/telegram/set-webhook
```

## Impacto
- **Elimina** definitivamente `TypeError: object dict can't be used in 'await' expression`
- **Elimina** el silencio absoluto del bot ante errores
- **Garantiza** que el webhook esté registrado con la URL correcta de producción
- **Mantiene** compatibilidad con funciones síncronas y asíncronas indistintamente
- **Mejora** la experiencia del usuario con feedback inmediato ante fallos

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] — Bitácora de avances y registro de estado.
- [[Índice Principal.md]] — Nodo central de navegación.
- [[FastAPI]] — Framework API.
- [[Vercel]] — Infraestructura serverless.
- [[Telegram]] — Plataforma de mensajería.
- [[Python]] — Lenguaje de programación.