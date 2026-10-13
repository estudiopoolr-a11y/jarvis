# Integración del analizador consciente al webhook

El endpoint de [[Telegram]] en `app/routes/telegram.py` conserva como primera
etapa `procesar_intencion_natural`, el router determinístico que ejecuta las
operaciones existentes de [[Firebase]] y tareas. Solo cuando el router no
reconoce una solicitud se invoca `analizar_solicitud_consciente` desde
`modules/ai.py`, función asíncrona que usa el cliente común de [[Gemini API]].

El analizador produce una intención de alto nivel y parámetros. Para
`CONSULTAR_FINANZAS`, el webhook reutiliza el analizador detallado y ejecuta
solo las intenciones financieras que el ejecutor admite. Si la intención no
queda cerrada, incluidas tareas no reconocidas o una clasificación ambigua, la
consulta pasa al generador conversacional `pensar_respuesta`. Así, el webhook
no presenta acciones sin soporte como ejecutadas ni responde con textos
estáticos de inicialización.

Todas las llamadas pasan por `resolver_llamada_segura` para mantener
compatibilidad con funciones síncronas y asíncronas. El flujo funciona dentro
del despliegue [[FastAPI]] en [[Vercel]] sin alterar la configuración
Zero-Config.

Las pruebas de `tests/test_telegram_analizador_consciente.py` verifican la
prioridad del router determinístico, el fallback generativo para consultas
generales, tareas no reconocidas e intenciones financieras no cerradas, y la
ejecución de intenciones financieras admitidas.

Etiquetas: [[FastAPI]] [[Vercel]] [[Gemini API]] [[Python]] [[Telegram]]
