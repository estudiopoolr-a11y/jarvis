# Índice Principal

Bienvenido a la red de conocimiento de **JARVIS**.

Desde aquí puedes navegar a todos los componentes principales, arquitecturas y registros de estado.

## Entidades Core
- [[Módulo de Finanzas.md|Módulo de Finanzas]] - Gestión de cuentas transacciones y presupuestos.
- [[modulo_prestamos_y_recordatorios.md|Módulo de Préstamos y Recordatorios]] - Gestión de deudas y alertas de vencimiento.
- [[Hermes Agent.md|Hermes Agent]] - Motor de orquestación (ReAct) e inteligencia conversacional.
- [[Base de Datos Firestore.md|Firestore]] - Gestión de bases de datos y persistencia.
- [[arquitectura_atomic_design_bot.md|Atomic Design Bot]] - Arquitectura de 5 capas (Atoms, Molecules, Organisms, Templates, Routes).
- [[limpieza_y_estructura_simplificada.md|Limpieza y Estructura Simplificada]] - Purga de código legado y topología final.

## Integraciones y Arquitectura
- [[Integración NVIDIA.md|NVIDIA NIM]] - Conectores hacia modelos LLM de NVIDIA.
- [[Estrategia de Inversión.md|Inversión y Metas]] - Lógica algorítmica para pago de deudas y proyecciones.
- [[FastAPI.md|FastAPI]] - API principal alojada en servidor web.
- [[Vercel.md|Vercel]] - Infraestructura para serverless deployment.
- [[Jarvis/telegram_bot_webhook.md|Telegram Bot Webhook]] - Integración serverless con Telegram vía Vercel (con arquitectura Atomic Design).
- [[Jarvis/parser_nlp_telegram_intentions.md|Parser NLP Telegram]] - Clasificación de intenciones en lenguaje natural para Telegram.
- [[Jarvis/monitoreo_uptimerobot.md|Monitoreo UptimeRobot]] - Monitoreo de salud de la API y prevención de Cold Starts.
- [[Jarvis/vercel_routing_fix.md|Fix de Routing Vercel]] - Corrección de enrutamiento serverless para resolver HTTP 404.
- [[Jarvis/configuracion_paso_a_paso_telegram_vercel.md|Guía de Configuración Telegram Webhook en Vercel]] - Procedimiento paso a paso para activar y verificar el webhook de Telegram en Vercel.
- [[Jarvis/despliegue_produccion_vercel.md|Despliegue en Producción Vercel]] - Verificación E2E, arquitectura de routing, widget Scriptable y estado del webhook Telegram.
- [[Jarvis/vercel_runtime_syntax_fix.md|Fix de Runtime en vercel.json]] - Corrección del error "Function Runtimes must have a valid version" usando @vercel/python.
- [[Jarvis/confirmacion_despliegue_e2e.md|Confirmación Despliegue E2E]] - Verificación final del webhook de Telegram y endpoint del widget tras redeploy.
- [[Jarvis/resolucion_conflicto_vercel_builds.md|Resolución de Conflicto Builds vs Functions]] - Limpieza de vercel.json para resolver incompatibilidad de propiedades.
- [[Jarvis/diagnostico_enrutamiento_vercel_404.md|Diagnóstico de Enrutamiento Vercel 404]] - Análisis detallado de los intentos de corrección de errores 404 en Vercel y configuración de serverless functions.
- [[Jarvis/despliegue_exitoso_vercel_e2e.md|Despliegue Exitoso Vercel y Verificación E2E]] - Documentación del despliegue exitoso en Vercel y validación de endpoints tras resolver autenticación.
- [[Jarvis/resolucion_function_invocation_failed_vercel.md|Resolución FUNCTION_INVOCATION_FAILED en Vercel]] - Diagnóstico y corrección del colapso durante Cold Start en Vercel.
- [[Jarvis/integracion_widget_scriptable_vercel.md|Integración Widget Scriptable Vercel]] - Conexión del widget de iOS al endpoint de dashboard en Vercel.
- [[Jarvis/guia_uso_telegram_y_widget_datos.md|Guía de Uso Telegram y Widget]] - Manual de comandos y funcionamiento de datos reales.

## Gestión del Royecto
- [[estado_proyecto.md|Estado del Proyecto]] - Bitácora de avances, roadmap y logs diarios.
- [[Jarvis/confirmacion_migracion_telegram_vercel.md|Confirmación Final Migración Telegram a Vercel]] - Validación E2E y re-registro de webhook tras migración a Vercel.
- [[Jarvis/migracion_oficial_webhook_telegram.md|Migración Oficial Webhook Telegram]] - Documentación detallada de la migración definitiva de webhook de Telegram desde Render a Vercel.
- [[Jarvis/migracion_render_a_vercel.md|Migración Render a Vercel]] - Guía completa de la migración de infraestructura desde Render.com a Vercel.
- [[Mapa del Sistema.md|Mapa del Sistema]] - Nodo de navegación alternativo (Legado).
- [[Jarvis/diagnostico_error_500_webhook_telegram.md|Diagnóstico Error 500 Webhook Telegram]] - Diagnóstico y solución de excepciones HTTP 500 en endpoint de Telegram en Vercel.


## Protocolos Auxiliares
- [[Protocolo_Obsidian_Agentes.md|Protocolo Obsidian]] - Refiere al documento principal de reglas de actualización (si existe) y se rige por las directrices del proyecto.
