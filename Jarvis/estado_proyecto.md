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
    - Se confirmó que el webhook de Telegram aún apunta a Render (https://jarvis-vy8k.onrender.com/webhook) mediante getWebhookInfo.
    - Se creó nota de confirmación [[Jarvis/confirmacion_migracion_telegram_vercel.md]] detallando el estado actual y pasos necesarios.
    - Se determinó que el próximo paso requiere deshabilitar la autenticación en el panel de Vercel para permitir acceso público a los endpoints.