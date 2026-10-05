# Índice Principal

Bienvenido a la red de conocimiento de **JARVIS**.

Desde aquí puedes navegar a todos los componentes principales, arquitecturas y registros de estado.

## Entidades Core
- [[Módulo de Finanzas.md|Módulo de Finanzas]] - Gestión de cuentas transacciones y presupuestos.
- [[Hermes Agent.md|Hermes Agent]] - Motor de orquestación (ReAct) e inteligencia conversacional.
- [[Base de Datos Firestore.md|Firestore]] - Gestión de bases de datos y persistencia.

## Integraciones y Arquitectura
- [[Integración NVIDIA.md|NVIDIA NIM]] - Conectores hacia modelos LLM de NVIDIA.
- [[Estrategia de Inversión.md|Inversión y Metas]] - Lógica algorítmica para pago de deudas y proyecciones.
- [[FastAPI.md|FastAPI]] - API principal alojada en servidor web.
- [[Vercel.md|Vercel]] - Infraestructura para serverless deployment.
- [[Jarvis/telegram_bot_webhook.md|Telegram Bot Webhook]] - Integración serverless con Telegram vía Vercel.
- [[Jarvis/monitoreo_uptimerobot.md|Monitoreo UptimeRobot]] - Monitoreo de salud de la API y prevención de Cold Starts.
- [[Jarvis/vercel_routing_fix.md|Fix de Routing Vercel]] - Corrección de enrutamiento serverless para resolver HTTP 404.
- [[Jarvis/despliegue_produccion_vercel.md|Despliegue en Producción Vercel]] - Verificación E2E, arquitectura de routing, widget Scriptable y estado del webhook Telegram.
- [[Jarvis/vercel_runtime_syntax_fix.md|Fix de Runtime en vercel.json]] - Corrección del error "Function Runtimes must have a valid version" usando @vercel/python.
- [[Jarvis/confirmacion_despliegue_e2e.md|Confirmación Despliegue E2E]] - Verificación final del webhook de Telegram y endpoint del widget tras redeploy.
- [[Jarvis/resolucion_conflicto_vercel_builds.md|Resolución de Conflicto Builds vs Functions]] - Limpieza de vercel.json para resolver incompatibilidad de propiedades.
- [[Jarvis/diagnostico_enrutamiento_vercel_404.md|Diagnóstico de Enrutamiento Vercel 404]] - Análisis detallado de los intentos de corrección de errores 404 en Vercel y configuración de serverless functions.
- [[Jarvis/despliegue_exitoso_vercel_e2e.md|Despliegue Exitoso Vercel y Verificación E2E]] - Documentación del despliegue exitoso en Vercel y validación de endpoints tras resolver autenticación.

## Gestión del Royecto
- [[estado_proyecto.md|Estado del Proyecto]] - Bitácora de avances, roadmap y logs diarios.
- [[Jarvis/confirmacion_migracion_telegram_vercel.md|Confirmación Final Migración Telegram a Vercel]] - Validación E2E y re-registro de webhook tras migración a Vercel.
- [[Jarvis/migracion_oficial_webhook_telegram.md|Migración Oficial Webhook Telegram]] - Documentación detallada de la migración definitiva de webhook de Telegram desde Render a Vercel.
- [[Jarvis/migracion_render_a_vercel.md|Migración Render a Vercel]] - Guía completa de la migración de infraestructura desde Render.com a Vercel.
- [[Mapa del Sistema.md|Mapa del Sistema]] - Nodo de navegación alternativo (Legado).

## Protocolos Auxiliares
- [[Protocolo_Obsidian_Agentes.md|Protocolo Obsidian]] - Refiere al documento principal de reglas de actualización (si existe) y se rige por las directrices del proyecto.
