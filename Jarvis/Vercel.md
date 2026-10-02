# Vercel - Infraestructura Serverless para JARVIS

## Descripción
Vercel es la plataforma elegida para el despliegue serverless de JARVIS, alojando la aplicación FastAPI como una Función Serverless. Esta elección elimina la necesidad de servidores tradicionales y optimiza el uso de recursos.

## Configuración
- **Framework**: `@vercel/python` para construir la imagen de despliegue.
- **Archivo de configuración**: `vercel.json` en la raíz del proyecto.
- **Entrypoint**: `app/main.py` (instancia FastAPI).

## Rutas Específicas
- `/api/telegram/webhook`: Endpoint para recibir eventos de Telegram (Webhook).
- `/api/telegram/set-webhook`: Helper para registrar la URL del webhook en Telegram.
- `/`: Health check y endpoints generales de la API.

## Ventajas
- **Escalado automático**: Se escala a cero cuando no hay tráfico.
- **Despliegues rápidos**: Integración directa con GitHub.
- **Funciones aisladas**: Cada ruta puede comportarse como una función independiente (aunque actualmente se usa un solo entrypoint).

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] - Registro de cambios y roadmap.
- [[Jarvis/FastAPI.md]] - Detalles de la API principal.
- [[Jarvis/telegram_bot_webhook.md]] - Integración específica de Telegram.
- [[Jarvis/Índice Principal.md]] - Nodo central de la red de conocimiento.