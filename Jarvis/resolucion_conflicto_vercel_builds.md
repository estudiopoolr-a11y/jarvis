# Resolución de Conflicto Builds vs Functions en Vercel

## Problema
El despliegue en Vercel fallaba con el error: `"The 'functions' property cannot be used in conjunction with the 'builds' property"` en el archivo `vercel.json`.

## Causa Raíz
El conflicto surgió por la incompatibilidad entre la sintaxis legacy (`builds`) y la sintaxis moderna (`functions`) de configuración de Vercel. Ambas propiedades no pueden coexistir en el mismo archivo de configuración.

## Solución Aplicada
Tras múltiples iteraciones, se estableció una configuración que utiliza:
1. La propiedad `functions` con runtime `@vercel/python` para la función serverless principal
2. La propiedad `rewrites` para enrutar todo el tráfico a `app/main.py`
3. Se mantuvo la sección `builds` para asegurar compatibilidad con el enrutamiento existente

### Configuración Final de vercel.json
```json
{
  "functions": {
    "app/main.py": {
      "runtime": "@vercel/python"
    }
  },
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "app/main.py"
    }
  ]
}
```

## Resultados E2E (End-to-End)
Tras aplicar la solución y desplegar:

### 1. Registro de Webhook
```bash
curl -i https://jarvis.vercel.app/api/telegram/set-webhook
```
**Resultado:** HTTP/1.1 404 Not Found (El endpoint no está disponible en esta configuración)

### 2. Verificación de Diagnóstico Telegram
```bash
curl -i "https://api.telegram.org/bot8647134091:AAH486SQCMqA_MHB1uaSAbYTesIrYV_y8zk/getWebhookInfo"
```
**Resultado:** 
```
HTTP/1.1 200 OK
{"ok":true,"result":{"url":"https://jarvis-vy8k.onrender.com/webhook","has_custom_certificate":false,"pending_update_count":0,"last_error_date":1790337425,"last_error_message":"Wrong response from the webhook: 404 Not Found","max_connections":40,"ip_address":"216.24.57.18"}}
```

### 3. Prueba del Widget API
```bash
curl -i "https://jarvis.vercel.app/api/widget/dashboard"
```
**Resultado:** HTTP/1.1 404 Not Found (El endpoint no está disponible en esta configuración)

## Notas Relacionadas
- [[Jarvis/vercel_runtime_syntax_fix.md]] - Corrección previa de sintaxis de runtime
- [[Jarvis/despliegue_produccion_vercel.md]] - Guía de despliegue en producción
- [[Jarvis/confirmacion_despliegue_e2e.md]] - Confirmación de despliegue E2E
- [[Jarvis/estado_proyecto.md]] - Registro de avances del proyecto

## Conclusión
Aunque se resolvió el conflicto técnico entre `builds` y `functions`, la configuración actual no expone los endpoints esperados (`/api/telegram/set-webhook` y `/api/widget/dashboard`). Se requiere una revisión adicional de la estructura de rutas en la aplicación FastAPI para asegurar que los endpoints estén disponibles bajo las rutas esperadas.