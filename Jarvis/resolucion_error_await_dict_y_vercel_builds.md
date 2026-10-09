# Resolución Error Await Dict y Migración Zero-Config Vercel

## Descripción
Nota técnica que documenta la resolución del error `TypeError: object dict can't be used in 'await' expression` en el webhook de Telegram y la migración de `vercel.json` a la estructura Zero-Config para eliminar advertencias de build en Vercel.

## Causas Identificadas

### Causa 1: Bloque Legacy "builds" en vercel.json
El archivo `vercel.json` contenía un bloque `"builds": [...]` junto con `"routes": [...]`, lo que generaba advertencias de incompatibilidad en el motor serverless de Vercel. El formato legacy usa `builds` + `routes` pero el motor moderno requiere solo `rewrites` para funciones serverless Python.

### Causa 2: Excepción TypeError en `await` de función síncrona
En `app/routes/telegram.py`, las líneas 63-64 aplicaban `await` directamente a `analizar_intencion_mensaje()`:

```python
intent_data = await analizar_intencion_mensaje(mensaje_texto)  # ERROR: es síncrona
respuesta = await ejecutar_intencion_nlp(intent_data)  # OK: es asíncrona
```

Sin embargo, `analizar_intencion_mensaje()` en `modules/ai.py` es una **función síncrona** (def, no async def). Al aplicar `await` sobre una función síncrona que retorna un `dict`, Python lanza:

```
TypeError: object dict can't be used in 'await' expression
```

## Solución Aplicada

### 1. Migración Zero-Config de vercel.json
Se eliminó el bloque legacy `builds` y se simplifica a solo `rewrites`:

```json
{
  "version": 2,
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "app/main.py"
    }
  ]
}
```

Esto permite que Vercel detecte automáticamente el runtime Python sin configuración de build.

### 2. Inspección Dinámica de Corrutinas en app/routes/telegram.py
Se implementó verificación con `inspect.iscoroutinefunction()` antes de cada llamada a funciones NLP:

```python
import inspect

# Verificar si analizar_intencion_mensaje es corrutina
if inspect.iscoroutinefunction(analizar_intencion_mensaje):
    intent_data = await analizar_intencion_mensaje(mensaje_texto)
else:
    intent_data = analizar_intencion_mensaje(mensaje_texto)

# Verificar si ejecutar_intencion_nlp es corrutina
if inspect.iscoroutinefunction(ejecutar_intencion_nlp):
    respuesta = await ejecutar_intencion_nlp(intent_data)
else:
    respuesta = ejecutar_intencion_nlp(intent_data)
```

### 3. Validación de Tipo de Respuesta
Se agregó blindaje para garantizar que `respuesta` sea siempre un string antes de enviarlo a Telegram:

```python
if isinstance(respuesta, dict):
    respuesta = respuesta.get("text") or respuesta.get("message") or str(respuesta)
elif not isinstance(respuesta, str):
    respuesta = str(respuesta)
```

### 4. Script de Diagnóstico Integral
Se creó `scripts/test_exhaustive_local.py` que simula el flujo completo:
- Valida tipos de retorno de `analizar_intencion_mensaje` y `ejecutar_intencion_nlp`
- Simula payload de Telegram con MockRequest
- Verifica que el webhook responda `{"status": "ok"}` sin excepciones

**Resultado de verificación:**
```
🧪 [1/3] Probando tipos de retorno de NLP e Intent Handler...
   Resultado intent_data: {'intent': 'CONSULTAR_BALANCE', ...} (Tipo: <class 'dict'>)
   Resultado respuesta: 🟢 *Balance*: $1.500.000 COP ... (Tipo: <class 'str'>)

🧪 [2/3] Simulando petición Webhook completa con Mock Request...
   Resultado Webhook: {'status': 'ok'}

✅ [3/3] Pruebas exhaustivas superadas con ÉXITO sin excepciones de await.
```

## Verificación de Tipos
```python
inspect.iscoroutinefunction(analizar_intencion_mensaje)  # False (síncrona)
inspect.iscoroutinefunction(ejecutar_intencion_nlp)       # True (asíncrona)
```

## Impacto
- Elimina `TypeError: object dict can't be used in 'await' expression` en el webhook de producción.
- Elimina advertencias de build en Vercel al usar formato Zero-Config.
- El webhook responde correctamente con `{"status": "ok"}` ante cualquier tipo de payload.
- El sistema mantiene compatibilidad con funciones síncronas y asíncronas indistintamente.

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] — Bitácora de avances y registro de estado.
- [[Índice Principal.md]] — Nodo central de navegación.
- [[FastAPI]] — Framework API.
- [[Vercel]] — Infraestructura serverless.
- [[Telegram]] — Plataforma de mensajería.
- [[Python]] — Lenguaje de programación.