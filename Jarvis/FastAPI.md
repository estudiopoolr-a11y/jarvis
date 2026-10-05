# FastAPI - API Principal de JARVIS

## Descripción
FastAPI es el framework utilizado para construir la API RESTful que sirve como backend de JARVIS. Proporciona endpoints para el widget de iOS, el webhook de Telegram y otras integraciones.

## Características
- **Alto rendimiento**: Basado en Starlette y Pydantic.
- **Validación automática**: Gracias a Pydantic.
- **Documentación interactiva**: Swagger UI y ReDoc incluidos.
- **Compatibilidad con ASYNC**: Soporte nativo para operaciones asíncronas.

## Estructura del Proyecto
- `app/main.py`: Punto de entrada de la aplicación.
- `app/api.py`: Configuración de la instancia FastAPI y ciclo de vida (lifespan).
- `app/routes/`: Contiene todos los routers de la API:
  - `app/routes/widgets.py`: Endpoints para el widget de iOS.
  - `app/routes/telegram.py`: Webhook para Telegram (serverless en Vercel).
  - `app/routes/comando.py`: Endpoint para comandos de acceso rápido.
  - Y otros módulos especializados (finanzas, presupuestos, etc.).

## Despliegue
La API está diseñada para desplegarse en plataformas serverless como **Vercel** mediante el uso de `@vercel/python`.

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] - Registro de cambios y roadmap.
- [[Jarvis/telegram_bot_webhook.md]] - Detalles de la integración con Telegram.
- [[Jarvis/Vercel.md]] - Información sobre el despliegue en Vercel.
- [[Jarvis/Índice Principal.md]] - Nodo central de la red de conocimiento.
- [[Jarvis/migracion_render_a_vercel.md]] - Guía de migración de Render a Vercel.