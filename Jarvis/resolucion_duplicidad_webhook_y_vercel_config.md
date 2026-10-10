# Resolución de duplicidad en Webhook y limpieza de vercel.json

## Problema
Se estaba recibiendo duplicados de mensajes en Telegram porque el router de Telegram se incluía dos veces en `app/main.py`, generando a su vez dos manejadores que procesaban el mismo webhook.

## Solución aplicada
1. **Verificación y corrección** de `app/main.py`:
   * Se garantizó que el enrutador `telegram_router` se incluya **una sola vez** con la siguiente línea:
   ```python
   app.include_router(telegram_router, prefix="/api/telegram")
   ```
2. **Limpieza de `vercel.json`**:
   * Se eliminó el bloque legacy `builds` por completo y se dejó solo la sección de `routes` usando `rewrites`.
3. **Registro del webhook**:
   * El script `scripts/register_telegram_webhook.py` ahora limpia actualizaciones pendientes con `drop_pending_updates=true` y confirma que solo una URL esté registrada.

## Resultados
* Se elimina la duplicidad de respuestas en Telegram.
* Las advertencias de Vercel sobre configuración legacy desaparecen.
* Los logs se emiten de forma inmediata gracias a `PYTHONUNBUFFERED=1`.

## Enlaces obligatorios
- [[Jarvis/estado_proyecto.md]]
- [[Jarvis/resolucion_logging_unbuffered_y_despacho_telegram.md]]
- [[Jarvis/telegram_bot_webhook.md]]
- [[Juan/Arquitectura Paridad Python y Vercel]]
