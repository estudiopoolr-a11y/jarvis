# Configuración Paso a Paso del Webhook de Telegram en Vercel

## 🎯 Objetivo
Activar y verificar la conexión del bot de Telegram con el endpoint de FastAPI en Vercel.

## 🔧 Pasos Técnicos

### 1. Verificación de Variables de Entorno en Vercel
- Accede al panel de Vercel (**Settings -> Environment Variables**)
- Asegúrate de que estén configuradas:
  - `TELEGRAM_BOT_TOKEN`: El token oficial brindado por BotFather.
  - `VERCEL_URL`: `https://jarvis-two-pi-13.vercel.app` (o tu dominio personalizado)

### 2. Activación del Webhook en Telegram
Ejecuta en la terminal de PowerShell (o cualquier shell compatible):

```powershell
$TOKEN = "TU_TELEGRAM_BOT_TOKEN"
$WEBHOOK_URL = "https://jarvis-two-pi-13.vercel.app/api/telegram/webhook"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TOKEN/setWebhook?url=$WEBHOOK_URL" -Method Get
```

### 3. Verificación de Enlace Correcto
Ejecuta el siguiente comando para confirmar que el webhook apunta a Vercel:

```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TOKEN/getWebhookInfo" -Method Get
```

### 4. Prueba de Simulación en PowerShell (Sintaxis Sanitizada)
Para probar el endpoint sin errores de sintaxis, usa esta cadena JSON directa:

```powershell
$jsonPayload = '{"update_id": 99999999, "message": {"message_id": 105, "date": 1790337400, "chat": {"id": 12345678, "type": "private"}, "from": {"id": 12345678, "first_name": "Jan"}, "text": "hola jarvis"}}'
Invoke-RestMethod -Uri "https://jarvis-two-pi-13.vercel.app/api/telegram/webhook" -Method POST -ContentType "application/json" -Body $jsonPayload
```

## 📚 Enlaces Relacionados
- [[Jarvis/telegram_bot_webhook.md]] - Descripción técnica del endpoint y arquitectura serverless.
- [[Jarvis/migracion_render_a_vercel.md]] - Guía de migración de infraestructura desde Render a Vercel.
- [[Jarvis/estado_proyecto.md]] - Bitácora de avances y registro de configuraciones finales.

## ✅ Estado Actual (2026-10-06)
- [x] Webhook activado y verificado en Telegram
- [x] Endpoint en Vercel responde correctamente a pruebas POST
- [x] Variables de entorno confirmadas en el panel de Vercel
- [x] Guía de configuración paso a paso creada

## 📝 Próximos Pasos
- [ ] Documentar cómo deshabilitar la autenticación en Vercel para permitir acceso público a endpoints.
- [ ] Crear un script de prueba automatizado para validar el webhook.
- [ ] Implementar monitoreo de estado del webhook en UptimeRobot.

> *Última actualización: 2026-10-06*