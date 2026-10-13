# Integración del analizador consciente al webhook

El endpoint de [[Telegram]] en `app/routes/telegram.py` conserva como primera
etapa `procesar_intencion_natural`, el router determinístico que ejecuta las
operaciones existentes de [[Firebase]] y tareas. Solo cuando el router no
reconoce una solicitud se invoca `analizar_solicitud_consciente` desde
`modules/ai.py`, función asíncrona que usa el cliente común de [[Gemini API]].

El analizador produce una intención de alto nivel y parámetros. Para
`CONSULTAR_FINANZAS`, el webhook reutiliza el analizador detallado y el
ejecutor de intenciones existentes. `CONSULTA_GENERAL` se responde con
Gemini. Una solicitud de tareas no reconocida recibe una respuesta explícita:
el repositorio no tiene un ejecutor genérico de tareas en Notion, y el webhook
no afirma que una acción sin soporte se haya completado.

Todas las llamadas pasan por `resolver_llamada_segura` para mantener
compatibilidad con funciones síncronas y asíncronas. El flujo funciona dentro
del despliegue [[FastAPI]] en [[Vercel]] sin alterar la configuración
Zero-Config.

Las pruebas de `tests/test_telegram_analizador_consciente.py` verifican la
prioridad del router determinístico, los tres caminos de fallback y que no se
simule la ejecución de tareas no reconocidas.

Etiquetas: [[FastAPI]] [[Vercel]] [[Gemini API]] [[Python]] [[Telegram]]
