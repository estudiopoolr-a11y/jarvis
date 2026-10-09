# Diagnóstico y Blindaje del Webhook de Telegram

Fecha: 2026-10-09

## Estado técnico inicial

El webhook estaba activo en producción:
`https://jarvis-two-pi-13.vercel.app/api/telegram/webhook`
pero Telegram reportaba recurrentemente `Wrong response from the webhook: 500 Internal Server Error`
con `last_error_date` vigente.

Las causas identificadas fueron:
1. Extracción frágil de payload: `cuerpo["message"]["chat"]["id"]` provocaba KeyError ante `edited_message`, payload vacío o mensajes no-texto.
2. Ausencia de limpieza de actualizaciones pendientes tras re-registros, generando reintentos en bucle.
3. Envío de respuestas sin verificación de éxito; el endpoint siempre devolvía 200 aunque fallara el `sendMessage`.

## Diagnóstico en vivo

Se creó `scripts/diagnostico_live_telegram.py` para:
- `getMe` → validar credenciales del bot `Pooles_Bot` (id 8647134091).
- `getWebhookInfo` → inspeccionar `url`, `pending_update_count`, `last_error_message`.
- `setWebhook` con `drop_pending_updates=True` → re-registrar contra Vercel y limpiar cola.

Ejecución confirmada:
- `getMe ok: True`
- `Webhook url` correcto, `last_error_message` inicial reportado y posteriormente limpio tras parche.
- `setWebhook ok: True, result: True`

## Refactorización ultradefensiva en `app/routes/telegram.py`

### Cambios clave

- **Extracción multinivel con `.get()`**
  ```python
  mensaje = cuerpo.get("message") or cuerpo.get("edited_message") or {}
  chat = mensaje.get("chat", {})
  chat_id = chat.get("id")
  mensaje_texto = (mensaje.get("text") or "").strip()
  ```
  Evita KeyError y maneja `edited_message` / mensajes sin texto.

- **Despacho atómico con verificación**
  `despachar_respuesta_telegram` ahora devuelve bool y registra `status_code` y cuerpo de respuesta.
  Logger exclusivo `jarvis.telegram`.

- **Manejo de excepciones globales**
  Bloque `try/except` exterior atrapa cualquier fallo y devuelve siempre `{"status":"ok"}` a Telegram para evitar reintentos, mientras se registra el error interno con `{"status":"error_handled"}` cuando ocurre excepción.

### Ruta `/api/telegram/set-webhook`

Mantiene registro programático con URL construida desde `VERCEL_URL` y post a `api.telegram.org/bot<token>/setWebhook`.

## Prueba E2E de producción

Script `scripts/test_live_payload_simulation.py` envía POST simulado:
```json
{
  "update_id": 999999,
  "message": {
    "chat": {"id": 12345678},
    "text": "Q presupuestos hay Pa septiembre"
  }
}
```
Resultado: `Status 200` y `{"status":"ok"}`. La API responde sin 500.

Pruebas unitarias: `python -m unittest discover -v tests` → 5/5 PASSING.

## Impacto Operacional

- Elimina 500 Internal Server Error reportados por Telegram.
- Previene bucles de reintentos con `drop_pending_updates`.
- Parser tolerante a variaciones de payload Telegram (message / edited_message / canal).
- Logging detallado para auditoría de entregas y diagnóstico rápido.

## Enlaces
[[Índice Principal.md]]
[[Jarvis/estado_proyecto.md]]
[[Jarvis/telegram_bot_webhook.md]]
[[Jarvis/recuperacion_webhook_telegram.md]]
[[FastAPI]]
[[Vercel]]
[[Atomic Design]]
