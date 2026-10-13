# Corrección de respuestas y fallback de Telegram

El webhook en [[app/routes/telegram.py]] conserva las respuestas del router
determinístico cuando reconoce y procesa una acción. Para mensajes no
reconocidos, consulta [[Gemini API]] mediante
`analizar_solicitud_consciente`.

Una intención financiera solo se ejecuta si el analizador detallado devuelve
una de las operaciones admitidas por `ejecutar_intencion_nlp`. Una intención
ambigua, desconocida o no financiera —incluidas tareas sin un ejecutor
reconocido— se deriva a `pensar_respuesta`, el generador conversacional de
Gemini. El flujo evita responder con frases estáticas de inicialización y no
afirma haber completado acciones no soportadas.

`resolver_llamada_segura` sigue envolviendo llamadas síncronas y asíncronas.
Las pruebas de `tests/test_telegram_analizador_consciente.py` cubren tanto los
casos determinísticos como las rutas de fallback.

Etiquetas: [[FastAPI]] [[Vercel]] [[Gemini API]] [[Telegram]] [[Python]]
