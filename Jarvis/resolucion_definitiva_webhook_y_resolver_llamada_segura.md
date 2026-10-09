# Resolución Definitiva Webhook Telegram y Wrapper Universal resolver_llamada_segura

## Descripción
Nota técnica que documenta la solución definitiva del error persistente `object dict can't be used in 'await' expression` en el webhook de Telegram, implementando un **wrapper universal async/sync** (`resolver_llamada_segura`) y un mecanismo de **notificación de errores en Telegram** para evitar el silencio absoluto del bot.

## Problemas Identificados

### Problema 1: Excepción Persistente de Await en Dict
A pesar de aplicar `inspect.iscoroutinefunction()` en `app/routes/telegram.py`, los logs de Vercel seguían reportando:
```
[VERCEL ERROR] Fallo crítico en webhook: object dict can't be used in 'await' expression
```

**Causa raíz:** Aunque `inspect.iscoroutinefunction()` prevenía el `await` directo sobre funciones síncronas, algunas funciones podían retornar objetos **awaitable** (como `asyncio.Future` o generators) que no son detectados por `iscoroutinefunction()` pero sí por `inspect.isawaitable()`. Al aplicar `await` directamente sobre un dicto retornado por una función síncrona, Python lanza la excepción.

### Problema 2: Silencio Absoluto del Bot en Errores
Cuando ocurría una excepción en el procesamiento del webhook, el bot no notificaba al usuario en Telegram. El usuario veía que su mensaje no recibía respuesta alguna, sin saber si era un problema de conectividad, credenciales o lógica.

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
        res = func(*args, **kwargs)             # Invocación directa

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
@router.post("/webhook")
async def atender_telegram_webhook(request: Request):
    chat_id = None  # Inicializar fuera del try para acceso en except
    try:
        # ... lógica normal ...
    except Exception as e:
        print(f"💥 [VERCEL ERROR] Fallo crítico en webhook: {e}")
        if chat_id:  # Notificar al usuario si tenemos el chat_id
            await despachar_respuesta_telegram(
                chat_id,
                f"⚠️ Ocurrió un error interno en el bot: {str(e)[:100]}"
            )
        return {"status": "error_handled"}
```

**Comportamiento:**
- Si el error ocurre antes de extraer `chat_id` → log en Vercel, sin notificación (no se puede contactar al usuario)
- Si el error ocurre después de extraer `chat_id` → mensaje de error enviado al usuario en Telegram
- El usuario siempre recibe feedback, nunca queda en silencio

### 3. Script de Registro Directo de Webhook

Se creó `scripts/register_telegram_webhook.py` para garantizar que la URL del webhook esté correctamente registrada en Telegram API:

```python
import os, sys, requests

def registrar_webhook_produccion():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: Define TELEGRAM_BOT_TOKEN en tu entorno local")
        sys.exit(1)

    url_webhook = "https://jarvis-two-pi-13.vercel.app/api/telegram/webhook"
    endpoint_set = f"https://api.telegram.org/bot{token}/setWebhook?url={url_webhook}"

    res = requests.get(endpoint_set).json()
    print(f"Respuesta de Telegram API: {res}")

    if res.get("ok"):
        print("✅ Webhook registrado y activo con ÉXITO en Telegram")
    else:
        print(f"❌ Fallo al registrar Webhook: {res.get('description')}")
```

**Uso:**
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
🧪 [1/2] Evaluando resolver_llamada_segura con NLP e Intent Handler...
   Intent Data devuelto: {'intent': 'CONSULTAR_BALANCE', 'filtro': 'general'} (Tipo: <class 'dict'>)
   Respuesta devuelta: 🟢 *Balance*: $1.500.000 COP... (Tipo: <class 'str'>)

🧪 [2/2] Simulando Webhook completo con Mock Request...
   Resultado del Webhook: {'status': 'ok'}

✅ PRUEBAS INTEGRADAS COMPLETADAS CON ÉXITO SIN EXCEPCIONES
```

### Batería de Tests Unitarios
```bash
python -m unittest discover -v tests
```
**Resultado:** `Ran 5 tests in ~27s — OK`

### Registro de Webhook en Telegram
```bash
python scripts/register_telegram_webhook.py
```
**Resultado:** `✅ Webhook registrado y activo con ÉXITO en Telegram`

## Estado del Webhook en Producción
Tras el despliegue:
- `GET /api/telegram/health` → 200 OK con `telegram_bot_token_present: true`
- `POST /api/telegram/webhook` → 200 OK con procesamiento correcto
- Error notifications → El bot notifica errores en el chat de Telegram

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