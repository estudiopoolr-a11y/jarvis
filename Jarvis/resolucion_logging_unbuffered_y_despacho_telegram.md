# Resolución Logging Forzado y Guardas en Despacho Telegram

## Descripción
Nota técnica que documenta la implementación de `flush=True` en todas las impresiones de consola y la validación obligatoria contra texto vacío en `despachar_respuesta_telegram`, asegurando que las salidas a Vercel Logs sean siempre visibles y que nunca se envíe un texto vacío a Telegram API.

## Causa Raíz

### Problema 1: Falta de Visibilidad en Vercel Logs
Las impresiones de consola con `logging.getLogger` a menudo no se mostraron inmediatamente o se retrasaron en los *Live Logs* de Vercel Serverless Functions, dificultando la depuración en tiempo real.

### Problema 2: Envío de Texto Vacío a Telegram API
Si `respuesta` era un diccionario vacío o `None`, Telegram API respondía con error 400 (`Bad Request: text is empty`), haciendo que el bot pareciera "enfermo" sin dar ninguna pista del error.

## Solución Aplicada

### 1. `flush=True` en Todas las Impresiones de Consola

Se agregó el parámetro `flush=True` a todas las llamadas `print()` en `app/routes/telegram.py`, forzando la escritura inmediata en la salida estándar:

```python
print("📡 [VERCEL OUTBOUND] Intento 1 Markdown Status: {res.status_code}", flush=True)
```

**Ventajas:**
- Las trayzas de depuración aparecen al instante en los *Live Logs* de Vercel.
- No hay retraso por bufferización del sistema.
- Es compatible con cualquier handler de logging de Python.

### 2. Validación Obligatoria Contra Texto Vacío en `despachar_respuesta_telegram()`

Se agregó una verificación al inicio de `despachar_respuesta_telegram()` para asegurar que `texto` nunca sea vacío o nulo:

```python
# Guarda defensiva: Evitar enviar texto vacío que causa error 400 en Telegram API #
if not texto or str(texto).strip() == "":  # Validar si el texto está vacío #
    texto = "🤖 JARVIS procesó tu consulta, pero no se generó un texto de respuesta válido."  # Mensaje de respaldo #
```

**Ventajas:**
- Telegram API nunca responde con error 400 por texto vacío.
- El usuario siempre recibe un mensaje informativo en lugar de un silencio absoluto.
- El sistema mantiene la resiliencia ante fallos de generación de lenguaje natural.

## Verificación

### Prueba de Impresión con Flush
```bash
python -c "import sys; print('Prueba de flujo', flush=True)"
```
**Resultado:** La salida aparece al instante en consola.

### Prueba de Guardado Contra Texto Vacío
```python
from app.routes.telegram import despachar_respuesta_telegram
# Simular llamada con texto vacío
result = despachar_respuesta_telegram(12345, "")
# Retorna True y registra el mensaje de respaldo en Vercel Logs
```

### Batería de Tests Unitarios
```bash
python -m unittest discover -v tests
```
**Resultado:** `Ran 5 tests in ~60s — OK`

### Despliegue en Producción
- `GET /api/telegram/health` → `200 OK` con `telegram_bot_token_present: true`
- `POST /api/telegram/webhook` → `200 OK` + procesamiento correcto

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] — Bitácora de avances y registro de estado.
- [[Índice Principal.md]] — Nodo central de navegación.
- [[FastAPI]] — Framework API.
- [[Vercel]] — Infraestructura serverless.
- [[Telegram]] — Plataforma de mensajería.
- [[Python]] — Lenguaje de programación.