# 脥ndice Principal

Bienvenido a la red de conocimiento de **JARVIS**.

Desde aqu铆 puedes navegar a todos los componentes principales, arquitecturas y registros de estado.

## Entidades Core
- [[M贸dulo de Finanzas.md|M贸dulo de Finanzas]] - Gesti贸n de cuentas transacciones y presupuestos.
- [[modulo_prestamos_y_recordatorios.md|M贸dulo de Pr茅stamos y Recordatorios]] - Gesti贸n de deudas y alertas de vencimiento.
- [[Hermes Agent.md|Hermes Agent]] - Motor de orquestaci贸n (ReAct) e inteligencia conversacional.
- [[Base de Datos Firestore.md|Firestore]] - Gesti贸n de bases de datos y persistencia.
- [[arquitectura_atomic_design_bot.md|Atomic Design Bot]] - Arquitectura de 5 capas (Atoms, Molecules, Organisms, Templates, Routes).
- [[limpieza_y_estructura_simplificada.md|Limpieza y Estructura Simplificada]] - Purga de c贸digo legado y topolog铆a final.

## Integraciones y Arquitectura
- [[Integraci贸n NVIDIA.md|NVIDIA NIM]] - Conectores hacia modelos LLM de NVIDIA.
- [[Estrategia de Inversi贸n.md|Inversi贸n y Metas]] - L贸gica algor铆tmica para pago de deudas y proyecciones.
- [[FastAPI.md|FastAPI]] - API principal alojada en servidor web.
- [[Vercel.md|Vercel]] - Infraestructura para serverless deployment.
- [[Jarvis/telegram_bot_webhook.md|Telegram Bot Webhook]] - Integraci贸n serverless con Telegram v铆a Vercel (con arquitectura Atomic Design).
- [[Jarvis/parser_nlp_telegram_intentions.md|Parser NLP Telegram]] - Clasificaci贸n de intenciones en lenguaje natural para Telegram.
- [[Jarvis/monitoreo_uptimerobot.md|Monitoreo UptimeRobot]] - Monitoreo de salud de la API y prevenci贸n de Cold Starts.
- [[Jarvis/vercel_routing_fix.md|Fix de Routing Vercel]] - Correcci贸n de enrutamiento serverless para resolver HTTP 404.
- [[Jarvis/configuracion_paso_a_paso_telegram_vercel.md|Gu铆a de Configuraci贸n Telegram Webhook en Vercel]] - Procedimiento paso a paso para activar y verificar el webhook de Telegram en Vercel.
- [[Jarvis/despliegue_produccion_vercel.md|Despliegue en Producci贸n Vercel]] - Verificaci贸n E2E, arquitectura de routing, widget Scriptable y estado del webhook Telegram.
- [[Jarvis/vercel_runtime_syntax_fix.md|Fix de Runtime en vercel.json]] - Correcci贸n del error "Function Runtimes must have a valid version" usando @vercel/python.
- [[Jarvis/confirmacion_despliegue_e2e.md|Confirmaci贸n Despliegue E2E]] - Verificaci贸n final del webhook de Telegram y endpoint del widget tras redeploy.
- [[Jarvis/resolucion_conflicto_vercel_builds.md|Resoluci贸n de Conflicto Builds vs Functions]] - Limpieza de vercel.json para resolver incompatibilidad de propiedades.
- [[Jarvis/diagnostico_enrutamiento_vercel_404.md|Diagn贸stico de Enrutamiento Vercel 404]] - An谩lisis detallado de los intentos de correcci贸n de errores 404 en Vercel y configuraci贸n de serverless functions.
- [[Jarvis/despliegue_exitoso_vercel_e2e.md|Despliegue Exitoso Vercel y Verificaci贸n E2E]] - Documentaci贸n del despliegue exitoso en Vercel y validaci贸n de endpoints tras resolver autenticaci贸n.
- [[Jarvis/resolucion_function_invocation_failed_vercel.md|Resoluci贸n FUNCTION_INVOCATION_FAILED en Vercel]] - Diagn贸stico y correcci贸n del colapso durante Cold Start en Vercel.
- [[Jarvis/integracion_widget_scriptable_vercel.md|Integraci贸n Widget Scriptable Vercel]] - Conexi贸n del widget de iOS al endpoint de dashboard en Vercel.
- [[Jarvis/guia_uso_telegram_y_widget_datos.md|Gu铆a de Uso Telegram y Widget]] - Manual de comandos y funcionamiento de datos reales.

## Gesti贸n del Royecto
- [[estado_proyecto.md|Estado del Proyecto]] - Bit谩cora de avances, roadmap y logs diarios.
- [[Jarvis/confirmacion_migracion_telegram_vercel.md|Confirmaci贸n Final Migraci贸n Telegram a Vercel]] - Validaci贸n E2E y re-registro de webhook tras migraci贸n a Vercel.
- [[Jarvis/migracion_oficial_webhook_telegram.md|Migraci贸n Oficial Webhook Telegram]] - Documentaci贸n detallada de la migraci贸n definitiva de webhook de Telegram desde Render a Vercel.
- [[Jarvis/migracion_render_a_vercel.md|Migraci贸n Render a Vercel]] - Gu铆a completa de la migraci贸n de infraestructura desde Render.com a Vercel.
- [[Mapa del Sistema.md|Mapa del Sistema]] - Nodo de navegaci贸n alternativo (Legado).
- [[Jarvis/diagnostico_error_500_webhook_telegram.md|Diagn贸stico Error 500 Webhook Telegram]] - Diagn贸stico y soluci贸n de excepciones HTTP 500 en endpoint de Telegram en Vercel.
- [[Jarvis/recuperacion_webhook_telegram.md|Recuperaci贸n Webhook Telegram]] - Diagn贸stico y soluci贸n de la desvinculaci贸n del Webhook el 2026-10-09.


## Protocolos Auxiliares
- [[Protocolo_Obsidian_Agentes.md|Protocolo Obsidian]] - Refiere al documento principal de reglas de actualizaci贸n (si existe) y se rige por las directrices del proyecto.

- [[Jarvis/diagnostico_y_blindaje_webhook.md|Diagn髎tico y Blindaje Webhook 2026-10-09]] - Correcci髇 ultradefensiva con .get() multinivel, scripts de diagn髎tico y verificaci髇 E2E en Vercel.


- [[Jarvis/resolucion_error_yfinance_startup.md|Resoluci髇 Error yfinance Startup 2026-10-09]] - Correcci髇 ModuleNotFoundError y blindaje de importaciones para Vercel.


- [[Jarvis/resolucion_fallo_envio_markdown_telegram.md|Resoluci髇 Fallo Env韔 Markdown Telegram 2026-10-09]] - Doble fallback Markdown -> Texto Plano.

