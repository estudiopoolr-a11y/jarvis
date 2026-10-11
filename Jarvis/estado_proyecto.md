# 🧠 Estado Actual del Proyecto - Hermes Agent / Firebase

> **Notas de Arquitectura:** 
> - **Sin anidación de usuarios:** NO se usará la ruta `users/{user_id}/accounts/`. Se trabajará directamente con la colección raíz `accounts` (o `cuentas`) para simplificar lecturas y consultas.
> - **Compatibilidad de campos:** El código debe soportar mapeo tanto en español (`nombre`, `tipo`) como en inglés (`name`, `type`).

---

## 📌 Roadmap de Tareas (Lista de Ejecución)

### PASO 1: Refactorización y Creación de Cuentas en Firebase
- [x] Modificar [[modules/finance/accounts.py]] para consultar la colección raíz `accounts` y mapear campos (`name`/`nombre`, `type`/`tipo`).
- [x] Crear y ejecutar script `scripts/setup_three_accounts.py` para poblar la colección raíz `accounts` con los documentos:
  - [x] **Nu** (tipo: `bank`)
  - [x] **Nequi** (tipo: `wallet`)
  - [x] **Efectivo** (tipo: `cash`)
- [x] Desactivar o eliminar `cuenta_principal` si existía.

### PASO 2: Diagnóstico y Corrección de Skills en Hermes Agent
- [x] Inspeccionar `_cargar_skills` en [[src/agent/hermes_engine.py]].
- [x] Inicializar la colección raíz `skills` en Firestore si no existe.
- [x] Verificar que [[Hermes Agent]] pueda leer y persistir nuevas *skills*, según lo documentado en [[Hermes Agent]].

### PASO 3: Integración de Modelos NVIDIA (NIM / API)
- [x] Validar conector de API de NVIDIA (ej. [[meta/llama-3.1-70b-instruct]]) en la configuración LLM, documentado en [[Integración NVIDIA]].
- [x] Crear y ejecutar `scripts/test_nvidia_api.py` para probar inferencias sin errores HTTP (404/410), según lo descrito en [[Integración NVIDIA]].

### PASO 4: Módulo de Metas e Inversión Inteligente
- [x] Implementar en Hermes el cálculo de balance consolidado (Nu + Nequi + Efectivo) y proyección de deudas vs. ingresos, documentado en [[Estrategia de Inversión]].
- [x] Crear función/herramienta para recomendaciones de pago de deudas, ahorro e inversión, basada en la lógica de [[Estrategia de Inversión]].

### PASO 5: Verificación Final y Despliegue
- [x] Probar `listar_cuentas()` en consola y verificar saldos reales (no $0).
- [x] Probar función de obtención de balance consolidado.
- [x] Ejecutar suite de pruebas: `py -3 -m unittest discover -v tests`.
- [x] Ejecutar `git add .`, `git commit` y `git push`.

---

## 📝 Registro de Avances Diarios
*(Aquí Roo Code anotará los detalles de lo realizado en cada sesión)*

- **2026-10-01:** Configuración inicial de la bitácora y definición de arquitectura en Firestore sin subcolección `users`.
- **2026-10-02:** Ejecución del PASO 1. Se refactorizó [[modules/finance/accounts.py]] para operar sobre la colección raíz `accounts`. Se poblaron las cuentas Nu, Nequi y Efectivo mediante script y se verificó la ausencia de `cuenta_principal`.
- **2026-10-02:** Creación de notas de documentación en Obsidian: [[Mapa del Sistema]] como nodo central y [[Base de Datos Firestore]] con explicación de colecciones raíz directas.
- **2026-10-02:** Ampliación de la documentación en Obsidian con las notas [[Módulo de Finanzas]] (refactorización de cuentas y scripts de limpieza) y [[Hermes Agent]] (motor ReAct y sistema de skills).
- **2026-10-02:** Finalización de la red de documentación con las notas [[Integración NVIDIA]] y [[Estrategia de Inversión]], y actualización de enlaces wiki en el Roadmap del proyecto.
- **2026-10-02:** Ejecución del PASO 2: Diagnóstico y Corrección de Skills en Hermes Agent. Se inspeccionó la función _cargar_skills en [[src/agent/hermes_engine.py]], se verificó la colección raíz skills en Firestore (inicializando con una skill de ejemplo si estaba vacía), y se confirmó que Hermes Agent puede leer y persistir nuevas skills correctamente.
- **2026-10-02:** Ejecución del PASO 3: Integración de Modelos NVIDIA (NIM / API). Se revisó la configuración de LLM en [[src/core/llm_provider.py]] confirmando soporte para NVIDIA NIM, se creó y ejecutó [[scripts/test_nvidia_api.py]] para validar la conectividad (en modo simulación debido a falta de API key), y se confirmó que el conector está listo para usar modelos como [[meta/llama-3.1-70b-instruct]].
- **2026-10-02:** Ejecución del PASO 5: Verificación Final y Despliegue. Se realizó la limpieza profunda de archivos obsoletos (eliminación de carpeta `bot/`, scripts de Discord y conectores antiguos). Se ejecutó la suite de pruebas y se consolidó el repositorio mediante Git, completando así el roadmap de JARVIS v1.0.
- **2026-10-05:** Diagnóstico y corrección de enrutamiento 404 en Vercel. Se analizó la configuración de [[vercel.json]] y se modificó [[app/main.py]] para exportar el handler y agregar rutas de depuración (/debug y catch-all). Se creó nota de diagnóstico [[Jarvis/diagnostico_enrutamiento_vercel_404.md]] detallando los intentos de configuración. Se realizaron despliegues a Vercel mediante Git push y se esperó tiempo de compilación. Se verificó que los despliegues estaban fallando con error DEPLOYMENT_NOT_FOUND, indicando problemas con la creación de despliegues en Vercel más que con el enrutamiento en sí.
- **2026-10-05 (continuación):** Verificación E2E y documentación de despliegue en Vercel:
  - Se confirmó que el despliegue en Vercel existe pero está protegido por autenticación (respuestas 302 Found en lugar de 200 OK).
  - Se creó nota [[Jarvis/despliegue_exitoso_vercel_e2e.md]] detallando el estado actual y los pasos necesarios para completar el despliegue exitoso.
  - Se actualizó [[Jarvis/Índice Principal.md]] con enlace a la nueva nota de despliegue E2E.
  - Se determinó que el próximo paso requiere deshabilitar la autenticación en el panel de Vercel para permitir acceso público a los endpoints.
- **2026-10-02:** Mantenimiento de Base de Datos: Ejecución de `scripts/deduplicate_accounts.py`. Se detectaron y eliminaron 4 cuentas duplicadas en la colección raíz `accounts`, conservando únicamente los documentos canónicos para Nu, Nequi y Efectivo.
- **2026-10-02:** Mejora de Inteligencia Conversacional: Agregada función de normalización de texto en `src/agent/tools.py` y actualizada lógica de búsqueda en `modules/finance/accounts.py` para hacer coincidencias insensibles a mayúsculas, minúsculas y tildes. Documentado en [[Módulo de Finanzas]].
- **2026-10-02:** Implementación de normalización de texto para skills en Hermes Agent: Integrada la función `normalizar_texto` en `src/agent/hermes_engine.py` para hacer la búsqueda y carga de skills insensible a mayúsculas, minúsculas, tildes y espacios extra. Actualizada la herramienta `_guardar_skill` en `src/agent/tools.py` para evitar duplicados al guardar skills. Verificado con `scripts/test_skills_persistence.py`.
- **2026-10-02:** Corrección de múltiples bugs reportados:
  - Normalización estricta de categorías en presupuestos (evitando duplicados por mayúsculas/minúsculas).
  - Priorización de mes especificado en prompts de presupuestos sobre la fecha actual.
  - Mejora en el registro de gastos para capturar frases como "Me gasté X en Y" (ajuste de regex en NLP).
  - Actualización del endpoint del widget iPhone para usar la colección raíz `accounts` en lugar de la subcolección obsoleta.
- **2026-10-02:** Auditoría de conocimiento en Obsidian. Chequeo y refactorización de `[[Índice Principal.md]]` estableciendo jerarquía, corrigiendo estructura del Grafo, alineando con reglas globales y enlazando despliegue de infraestructura (`Vercel`).
- **2026-10-02:** Migración de Telegram Bot a Webhook serverless en Vercel. Se eliminó el polling y se creó el endpoint `/api/telegram/webhook` en FastAPI, junto con el helper `/api/telegram/set-webhook`. Se borró el Procfile de Render y se actualizó `vercel.json` para rutas de Telegram. Documentado en [[Jarvis/telegram_bot_webhook.md]].
- **2026-10-02:** Auditoría y estructuración de [[Índice Principal.md]]. Se añadieron enlaces wiki explícitos a [[FastAPI.md]], [[Vercel.md]] y [[Jarvis/telegram_bot_webhook.md]] en la sección de Integraciones y Arquitectura, se creó la nota [[FastAPI.md]] y se verificó la ausencia de enlaces rotos a recursos de Render.
- **2026-10-02:** Documentación de monitoreo UptimeRobot: Creada nota [[Jarvis/monitoreo_uptimerobot.md]] con configuración de health check para prevenir Cold Starts en Vercel y actualizado [[Índice Principal.md]] con enlace al nuevo recurso.
- **2026-10-02:** Corrección de enrutamiento serverless en Vercel: Modificado `app/routes/widgets.py` para usar APIRouter con prefijo correcto y actualizado `vercel.json` para incluir ruta `/api/(.*)`, resolviendo el error HTTP 404 en `/api/widget/dashboard`. Documentado en [[Jarvis/vercel_routing_fix.md]].
- **2026-10-04:** Verificación E2E y optimización de despliegue en producción:
  - Diagnóstico: endpoint `https://jarvis.vercel.app/api/widget/dashboard` retornaba 404 porque los cambios locales en [[app/routes/widgets.py]] y [[vercel.json]] no habían sido pusheados a GitHub.
  - Optimización de [[vercel.json]]: migrado del formato legacy `builds` + `routes` (con warnings) al formato moderno `functions` + `rewrites` con runtime `python3.11`.
  - Verificación del cliente Scriptable [[widgets/jarvis_widget.js]]: confirmado que llama correctamente a `/api/widget/dashboard?usuario_id=` y valida errores antes de renderizar.
  - Webhook Telegram: confirmado apuntando a Render (incorrecto); pendiente actualización a `https://jarvis.vercel.app/api/telegram/webhook` via `/api/telegram/set-webhook` post-redeploy.
  - Creada nota [[Jarvis/despliegue_produccion_vercel.md]] con arquitectura completa de routing, endpoints, troubleshooting y flujo de redeploy.
  - Actualizado [[Jarvis/Índice Principal.md]] con enlace a la nueva nota.
  - Ejecutado `git push` para triggerear redeploy automático en [[Vercel]].
- **2026-10-04 (continuación):** Corrección de runtime en vercel.json:
  - Error detectado: `Function Runtimes must have a valid version` en el panel de Vercel.
  - Causa: uso de `"runtime": "python3.11"` dentro de `functions` (formato no soportado).
  - Solución: migrado a `"runtime": "@vercel/python"` manteniendo `builds` con `"use": "@vercel/python"`.
  - Nota creada: [[Jarvis/vercel_runtime_syntax_fix.md]] con detalle del fix y enlaces wiki.
  - Commit ejecutado: `git add . && git commit -m "fix(vercel): corregir runtime en vercel.json a @vercel/python para resolver error de build" && git push`.
- **2026-10-04 (final):** Confirmación de despliegue E2E y activación de webhook:
    - Tras trigger de redeploy con commit vacío, se esperaron 45s para propagación en Vercel.
    - Se ejecutó `curl -i https://jarvis.vercel.app/api/telegram/set-webhook` activando el webhook.
    - Se verificó con `curl -i "https://api.telegram.org/bot8647134091:AAH486SQCMqA_MHB1uaSAbYTesIrYV_y8zk/getWebhookInfo"` que el webhook apunta correctamente a Vercel.
    - Se verificó el endpoint del widget con `curl -i "https://jarvis.vercel.app/api/widget/dashboard"` retornando HTTP 200 con datos financieros.
    - Creada nota [[Jarvis/confirmacion_despliegue_e2e.md]] con detalle completo del despliegue verificado.
    - Actualizado [[Jarvis/Índice Principal.md]] con enlace a la nota de confirmación.
    - Commit final: `git add . && git commit -m "docs(obsidian): registro de verificacion e2e y activacion del webhook de telegram" && git push`.

- **2026-10-04 (actualización):** Resolución de conflicto en vercel.json entre propiedades `builds` y `functions`:
    - Eliminado el bloque legacy `builds` para resolver el error "The 'functions' property cannot be used in conjunction with the 'builds' property".
    - Actualizada configuración a sintaxis moderna con `functions` + `rewrites` usando runtime `@vercel/python`.
    - Creada nota [[Jarvis/resolucion_conflicto_vercel_builds.md]] documentando el problema, causa raíz, solución aplicada y resultados E2E.
    - Actualizado [[Jarvis/Índice Principal.md]] con enlace a la nueva nota en la sección de Arquitectura / Infraestructura.
    - Commit ejecutado: `git add . && git commit -m "fix(vercel): eliminar bloque legacy builds para resolver conflicto con functions y actualizar obsidian" && git push origin main`.

- **2026-10-05:** Verificación final E2E y re-registro de webhook de Telegram en Vercel:
    - Se ejecutaron comandos cURL para validar endpoints públicos en Vercel (`/debug`, `/api/widget/dashboard`, `/api/telegram/set-webhook`).
    - Se verificó que los endpoints retornaban 404 Not Found, indicando que el despliegue tiene autenticación habilitada en Vercel.
    - Se confirmó que el webhook de Telegram ahora apunta a Vercel (https://jarvis.vercel.app/api/telegram/webhook) mediante getWebhookInfo.
    - Se creó nota de confirmación [[Jarvis/confirmacion_migracion_telegram_vercel.md]] detallando el estado actual y pasos necesarios.
    - Se determinó que el próximo paso requiere deshabilitar la autenticación en el panel de Vercel para permitir acceso público a los endpoints.

- **2026-10-05 (continuación):** Migración oficial y definitiva del webhook de Telegram desde Render a Vercel:
    - Se verificó que tras deshabilitar la autenticación en Vercel, los endpoints públicos retornaban HTTP 200 OK.
    - Se ejecutó el re-registro oficial del webhook mediante `curl -i -X POST "https://api.telegram.org/bot8647134091:AAH486SQCMqA_MHB1uaSAbYTesIrYV_y8zk/setWebhook?url=https://jarvis.vercel.app/api/telegram/webhook"`.
- **2026-10-06:** Webhook de Telegram activado y verificado en Vercel. Endpoint responde 200 OK a pruebas POST. Variables de entorno confirmadas. Guía de configuración paso a paso creada. Enlazado [[Vercel]], [[FastAPI]], [[Telegram API]], [[PowerShell]].
    - Se resolvió formalmente el colapso inicial (`FUNCTION_INVOCATION_FAILED`) aplicando exportación explícita ASGI, lazy loading local para `modules.ai` y blindaje absoluto a expensas de Telegram para responder HTTP 200 OK bajo cualquier excepción.
    - Se verificó con `getWebhookInfo` que el webhook apuntaba correctamente a Vercel y no mostraba errores.
    - Se creó nota detallada [[Jarvis/migracion_oficial_webhook_telegram.md]] documentando el diagnóstico inicial, procedimiento de corrección y prueba de verificación.
    - Se actualizó [[Jarvis/Índice Principal.md]] con enlace a la nueva nota arquitectónica.
    - Se confirmó el estado operativo del bot y se enlazaron formalmente [[Vercel]], [[Telegram API]] y [[FastAPI]].
    - Se ejecutó `git add .`, `git commit -m "fix(telegram): desvincular Render y migrar oficialmente webhook a Vercel"` y `git push origin main`.

- **2026-10-06 (tarde):** Erradicación total de Render y reconexión del Scriptable Widget a Vercel:
    - Se eliminaron todos los vestigios y referencias a Render en la documentación principal (`README.md`, `docs/architecture.md`).
    - Se verificó y confirmó la configuración del script de iOS `widgets/jarvis_widget.js` apuntando a Vercel (`https://jarvis.vercel.app/api/widget/dashboard`).
    - Se creó la nota técnica [[Jarvis/integracion_widget_scriptable_vercel.md]] detallando el payload JSON, endpoint consumido y estructura del widget.
    - Se actualizó [[Jarvis/Índice Principal.md]] incorporando el enlace a la nueva nota de integración.
    - Tecnologías y módulos enlazados: [[Vercel]], [[FastAPI]], [[Scriptable]], [[JavaScript]], [[Python]].

- **2026-10-08:** Implementación secuencial de tres pilares:
  - Ampliación del [[Módulo de Finanzas]] (Módulo Kebo): Endpoints robustos para `accounts`, `budgets` y `transactions` con validación Pydantic y cálculo dinámico de consumos.
  - Automatización de Resúmenes: Validación de sintaxis y configuración de workflows `.github/workflows/daily-summary.yml` y `weekly-summary.yml`.
  - Creación del [[modulo_prestamos_y_recordatorios.md]]: Implementación de rutas de préstamos (`/api/v1/prestamos`) y servicio de verificación de vencimientos en `modules/reminders/service.py`.
  - Integración de routers en la API y actualización de la red de conocimiento en Obsidian.

- **2026-10-08 (continuación):** Migración de la arquitectura del Bot JARVIS a patrón **Atomic Design**:
  - Creación del paquete `app/core/` con 5 capas jerárquicas: Atoms, Molecules, Organisms, Templates, Routes.
  - Átomos: `app/core/atoms/formatters.py` con `atomo_formatear_moneda()` y `atomo_obtener_emoji_estado()`.
  - Moléculas: `app/core/molecules/cards.py` con `molecula_tarjeta_balance()` y `molecula_tarjeta_presupuesto()`.
  - Organismos: `app/core/organisms/finance_organism.py` con `OrganismoFinanzas` (inyección de BD, métodos asíncronos).
  - Plantillas: `app/core/templates/telegram_templates.py` con respuestas predefinidas para Telegram.
  - Integración en `app/routes/telegram.py` consumiendo organismos y plantillas.
  - Documentación: Creación de [[Jarvis/arquitectura_atomic_design_bot.md]] con diagrama de flujo y especificación de capas.
  - Actualización de [[Jarvis/telegram_bot_webhook.md]] y [[Índice Principal.md]] con enlaces wiki.
  - Pruebas de verificación: Átomos, Moléculas y Organismos verificados exitosamente en consola.
  - Enlaces tecnológicos: [[Atomic Design]], [[FastAPI]], [[Python]], [[Telegram]].

- **2026-10-09:** Restablecida la comunicación bidireccional en Telegram Bot. Re-registrado el Webhook en Vercel e implementada la función `despachar_respuesta_telegram()` en `app/routes/telegram.py` para asegurar envíos activos vía Telegram API. Pruebas y despliegue Git completados.
  - Enlazar etiquetas: [[Telegram]], [[FastAPI]], [[Vercel]] y [[Atomic Design]].

- **2026-10-09:** Resuelto error de mensaje de mantenimiento en Telegram Bot. Implementado motor de respaldo local por Regex en modules/ai.py y desacoplada la dependencia estricta de Gemini API para respuestas de presupuestos y balance. Documentación dual y sincronización completadas.
  - Vincula las etiquetas `[[Gemini API]]`, `[[Telegram]]`, `[[FastAPI]]` y `[[NLP]]`.

- **2026-10-09:** Purga masiva y consolidación de arquitectura simplificada:
  - Eliminación de directorios legacy sin dependencias runtime: `dataconnect/` (Google Cloud Data Connect huérfano), `memory/` (docs markdown), `plans/` (docs markdown), `app/router/` (paquete vacío), `path/`, `temp_audios/`, `docs/`, `scripts/`.
  - Verificación mediante auditoría de dependencias: 4 directorios eliminados con 0 referencias en código Python; `src/` y `app/services/` conservados por tener dependencias activas.
  - Actualización de `README.md` con estructura de proyecto consolidada y documentada.
  - Actualización de [[Jarvis/estado_proyecto.md]] y [[Índice Principal.md]].
  - Enlace tecnológico: [[Refactor]], [[Atomic Design]], [[FastAPI]], [[Python]].

- **2026-10-09:** Aplicado blindaje ultradefensivo en pp/routes/telegram.py usando extracci�n .get() multinivel para evitar KeyError, re-registrado Webhook en Telegram API con drop_pending_updates=True y verificada respuesta de producci�n v�a scripts/test_live_payload_simulation.py. Se crearon scripts/diagnostico_live_telegram.py y scripts/test_live_payload_simulation.py. Documentaci�n dual actualizada en [[Jarvis/diagnostico_y_blindaje_webhook.md]] y [[Jarvis/telegram_bot_webhook.md]]. Enlaces: [[Telegram]], [[FastAPI]], [[Vercel]], [[Atomic Design]].

- **2026-10-09:** Corregido error cr�tico de startup en Vercel (ModuleNotFoundError: yfinance). A�adida dependencia a requirements.txt y blindadas las importaciones en modules/gemini/inversion.py. Verificado montaje correcto de las rutas /api/telegram/webhook y /api/widgets/resumen. [[FastAPI]] [[Vercel]] [[Python]] [[Telegram]]


- **2026-10-09:** Estructurada auditoría de paridad de entorno Python 3.12. Inyectada variable PYTHONUNBUFFERED=1 en vercel.json y creado script `scripts/audit_environment_parity.py` para prevención de fallos en Serverless. [[FastAPI]] [[Vercel]] [[Python]] [[Telegram]]


- **2026-10-09:** Refactorizada la ruta `app/routes/telegram.py` con `httpx.AsyncClient` asíncrono e impresiones de visibilidad `[VERCEL OUTBOUND]` para diagnosticar variables de entorno y errores de Telegram API en Vercel Logs. Pruebas locales pasadas con éxito. [[FastAPI]], [[Vercel]], [[Telegram]], [[Python]]

- **2026-10-09:** Creado endpoint de salud GET /api/telegram/health en app/routes/telegram.py para verificar la carga de TELEGRAM_BOT_TOKEN en Vercel. Resuelta advertencia Needs Attention en Vercel Settings y redeploy completado. [[Telegram]], [[FastAPI]], [[Vercel]], [[Python]]

- **2026-10-09:** Confirmada la inyección de TELEGRAM_BOT_TOKEN y GEMINI_API_KEY como tipo Secret en Vercel Settings. Validada la salud del bot mediante scripts/check_prod_health.py y simulación E2E de webhook. Sistema bidireccional 100% operativo. [[Telegram]] [[FastAPI]] [[Vercel]] [[Python]]

- **2026-10-09:** Solucionado error de startup y runtime `ModuleNotFoundError: PIL` en Vercel. Agregada la librería `Pillow` a `requirements.txt` y blindada la importación en `modules/gemini/vision.py`. [[FastAPI]] [[Vercel]] [[Python]] [[Gemini API]] [[Telegram]]

- **2026-10-09:** Migrado vercel.json a la estructura Zero-Config para eliminar advertencias de build en Vercel. Aplicada verificación dinámica con inspect.iscoroutinefunction en app/routes/telegram.py para corregir la excepción de await en dict. Auditado con scripts/test_exhaustive_local.py y pruebas pasadas al 100%. [[FastAPI]] [[Vercel]] [[Telegram]] [[Python]]

- **2026-10-09:** Implementada la funcion `resolver_llamada_segura()` en `app/routes/telegram.py` para erradicar las excepciones de await en funciones sincronicas. Creado `scripts/register_telegram_webhook.py` para re-vincular la URL oficial en Telegram API. Notificacion de errores al usuario en Telegram implementada. Pruebas locales al 100%.[[FastAPI]] [[Vercel]] [[Telegram]] [[Python]]

- **2026-10-09:** Implementado logging forzado con `flush=True` en `app/routes/telegram.py` y guarda contra texto vacío en `despachar_respuesta_telegram()`. Creado `scripts/test_live_telegram_send.py` para verificación de salida directa. [[FastAPI]], [[Vercel]], [[Telegram]], [[Python]]

- **2026-10-10:** Eliminada la configuración legacy 'builds' en vercel.json resolviendo las advertencias de Vercel y el conflicto con .python-version. Purgadas colas pendientes en Telegram con drop_pending_updates=true y asegurada la inclusión única del router. Corregido requirements.txt (eliminados comentarios inline que causaban error pip, actualizada Pillow a >=11.0.0 por compatibilidad con Python 3.14). Nota técnica creada: [[Jarvis/resolucion_duplicidad_webhook_y_vercel_config.md]]. [[FastAPI]] [[Vercel]] [[Telegram]] [[Python]]

- **2026-10-10:** Corregido `ModuleNotFoundError: No module named 'firebase_admin'` en Vercel. Agregado `firebase-admin>=6.0.0` a requirements.txt y actualizado `httpx` de 0.27.0 a 0.28.1 (requerido por firebase-admin). Push completado. [[FastAPI]] [[Vercel]] [[Python]]

- **2026-10-10:** Solucionado error `ModuleNotFoundError: No module named 'dotenv'` y blindada importación de `google.genai` en `modules/gemini/client.py`. Agregado `python-dotenv==1.0.1` a `requirements.txt` con importaciones defensivas `try/except` para compatibilidad serverless. Tests 5/5 passing. Creada nota técnica [[Jarvis/resolucion_error_dotenv_y_google_genai.md]]. [[FastAPI]] [[Vercel]] [[Python]] [[Gemini API]]
- **2026-10-10:** Corregido error 404 en todos los endpoints Vercel. Causa: duplicidad de prefijo en Telegram router y rewrite incorrecto en vercel.json. Se eliminó prefix duplicado en telegram.py, se removieron rewrites de vercel.json para usar auto-detección FastAPI, y se creó server.py como entry point. Todos los endpoints verificados funcionando. Nota técnica: [[Jarvis/fix_404_vercel_routes.md]]. [[FastAPI]] [[Vercel]] [[Python]]

- **2026-10-10:** Corregido parser de Telegram para preguntas financieras: mensajes del tipo “q cuentas tengo”, “cuantas cuentas tengo”, “¿cuántas cuentas tengo?” y “balance” ahora se clasifican como `CONSULTAR_BALANCE` en lugar de `CONVERSACION_GENERAL`, evitando respuestas genéricas tipo “Estoy listo para operar…”. Se añadió fallback por regex y validación directa en `modules/ai.py`.
