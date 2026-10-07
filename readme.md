# 🤖 JARVIS: Asistente Personal de Telegram, Centro Financiero & Agente Autónomo (Hermes)

JARVIS es un asistente inteligente híbrido desplegado en infraestructura serverless en **Vercel**. Integra un **Bot de Telegram** interactivo, **FastAPI** para servir un Dashboard Web en tiempo real, integración para Widgets de iOS y el motor **Hermes Agent** para capacidades de auto-mejora, memoria persistente a largo plazo y ciclo de aprendizaje autónomo.

---

## 🌟 Descripción General

JARVIS opera 24/7 combinando tres capas operativas:

1. **Flujo Determinístico (~90% de los casos):** Respuestas instantáneas (<10ms) y operaciones financieras precisas sin costo de tokens.
2. **Motor Hermes Agent (Auto-Mejora y Memoria):** Bucle de aprendizaje continuo (Closed Learning Loop), creación automática de habilidades (`skills/`), y contexto histórico con base de datos sqlite/FTS5.
3. **Flujo Generativo (Gemini API):** Procesamiento de lenguaje natural avanzado, análisis de voz/audio, visión computacional y fallback inteligente en modo lectura.

### Funcionalidades Clave

- **Finanzas Personales (Modelo Kebo en Firebase Firestore):** Control de cuentas, presupuestos mensuales (techos de gasto por periodo `YYYY-MM`), gastos/ingresos, transferencias, préstamos y análisis consolidado determinístico[cite: 3].
- **Hermes Agent Learning Loop:**
  - **Auto-mejora & Skills (`SKILL.md`):** Identifica patrones repetitivos o soluciones complejas y genera habilidades ejecutables de forma autónoma.
  - **Memoria Persistente FTS5:** Almacena reglas de usuario, preferencias y proyectos en `~/.hermes/` para recordar contexto entre sesiones sin depender del *context window* del LLM.
- **Bot de Telegram Interactivo:** Comandos, atención a notas de voz (TTS/STT con inferencia de miles), procesamiento de adjuntos e imágenes.
- **Dashboard Web & API para Widgets:** Interfaz visual interactiva y endpoints JSON optimizados (`/api/widget/dashboard`) para el widget de iPhone/Scriptable.
- **Proceso Único Asíncrono:** Servidor HTTP FastAPI y Bot de Discord conviven en el mismo ciclo de eventos (`asyncio`) para ejecutarse de forma continua en Render.

---

## 🏛️ Arquitectura del Sistema

```text
                               ┌────────────────────────────────────────┐
                               │             DISCORD / AUDIO            │
                               └──────────────────┬─────────────────────┘
                                                  │
                                                  ▼
                                         bot/events.py
                                                  │
                ┌─────────────────────────────────┴─────────────────────────────────┐
                │                                                                   │
                ▼                                                                   ▼
    [Parsers Determinísticos]                                            [Hermes Agent Loop]
   (modules/ai.py & modules/db.py)                                 (Memoria FTS5 / Skills ~/.hermes)
                │                                                                   │
                ├─► Mutaciones Directas Firestore                                  ├─► Carga de Preferencias/Reglas
                └─► Respuestas Instantáneas (<10ms)                                └─► Fallback/Modelado Generativo
                                                                                    (Gemini API - Solo Lectura)
```

### Métricas Financieras (Regla de No Mezclar)
- **Liquidez en Cuentas:** Suma real del saldo en bancos (`listar_cuentas`).
- **Presupuestos del Mes (`YYYY-MM`):** Techos de gasto por categoría (no restan del balance de cuentas).
- **Neto del Mes:** Ingresos minus gastos del periodo activo (`YYYY-MM`).
- **Histórico:** Acumulado global (nunca se compara contra presupuestos de un solo mes).

---

## 📁 Estructura del Proyecto

```plaintext
├── .github/
│   └── workflows/
│       ├── daily-summary.yml
│       ├── test.yml
│       └── weekly-summary.yml
├── app/
│   ├── router/
│   │   └── __init__.py
│   ├── routes/
│   │   ├── kebo/
│   │   │   ├── __init__.py
│   │   │   ├── accounts.py
│   │   │   ├── budgets.py
│   │   │   ├── export.py
│   │   │   ├── reports.py
│   │   │   ├── seed.py
│   │   │   └── transactions.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── comando.py
│   │   ├── cron.py
│   │   ├── dashboard.py
│   │   ├── memory.py
│   │   ├── prestamos.py
│   │   ├── telegram.py
│   │   └── widgets.py
│   ├── services/
│   │   ├── daily_summary/
│   │   │   ├── __main__.py
│   │   │   ├── builder.py
│   │   │   ├── collector.py
│   │   │   ├── firebase_init.py
│   │   │   └── sender.py
│   │   ├── __init__.py
│   │   ├── daily_summary.py
│   │   ├── monthly_report.py
│   │   └── reminders.py
│   ├── templates/
│   │   └── dashboard.html
│   ├── __init__.py
│   ├── api.py
│   └── main.py
├── dataconnect/
│   ├── connector/
│   │   ├── connector.yaml
│   │   └── queries.gql
│   ├── schema/
│   │   ├── schema.gql
│   │   └── schema.sql
│   └── dataconnect.yaml
├── docs/
│   ├── api-endpoints.md
│   ├── architecture.md
│   └── database-schema.md
├── Jarvis/
│   ├── .obsidian/
│   │   ├── app.json
│   │   ├── appearance.json
│   │   └── workspace.json
│   ├── configuracion_paso_a_paso_telegram_vercel.md
│   ├── confirmacion_migracion_telegram_vercel.md
│   ├── telegram_bot_webhook.md
├── modules/
│   ├── finance/
│   │   ├── transactions/
│   │   │   ├── recent.py
│   ├── sql/
│   └── ai.py
├── scripts/
│   ├── check_cuenta_principal.py
│   ├── setup_three_accounts.py
├── tests/
│   ├── __init__.py
├── widgets/
│   └── jarvis_widget.js
├── .env
├── README.md
```---

## 🔑 Variables de Entorno Necesarias

Configura un archivo `.env` en la raíz del proyecto para desarrollo local, o define las variables en el panel de Render:

| Variable | Descripción | Requerido | Default |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Token del Bot de Telegram obtenido en @BotFather | **Sí** | - |
| `GEMINI_API_KEY` | Clave API de Google Gemini (o `GEMINI_API_KEYS` separadas por coma) | **Sí** | - |
| `FIREBASE_CREDENTIALS` | JSON stringified de la cuenta de servicio de Firebase | **Sí** | - |
| `HERMES_STORAGE_PATH` | Ruta para persistencia de base de datos sqlite y skills | No | `~/.hermes` |
| `PORT` | Puerto HTTP donde escuchará Uvicorn en desarrollo local | No | `8080` |
| `VERCEL_URL` | URL de producción en Vercel (ej. jarvis-two-pi-13.vercel.app) | No | - |
| `DISCORD_WEBHOOK_URL` | Webhook para alertas y reportes automáticos | No | - |

---

## 💻 Instalación y Ejecución Local

### 1. Clonar el repositorio e instalar dependencias
```bash
git clone [https://github.com/tu-usuario/jarvis.git](https://github.com/tu-usuario/jarvis.git)
cd jarvis
python -m venv .venv

# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variables de entorno
Crea un archivo `.env` en la raíz:
```env
TELEGRAM_BOT_TOKEN=tu_token_de_telegram
GEMINI_API_KEY=tu_gemini_api_key
FIREBASE_CREDENTIALS={"type": "service_account", ...}
PORT=8080
VERCEL_URL=jarvis-two-pi-13.vercel.app
```

### 3. Ejecutar la suite de pruebas unitarias[cite: 3]
Antes de iniciar, verifica que los parsers determinísticos y regex pasen los tests[cite: 3]:
```bash
python -m unittest discover -v tests
```

### 4. Ejecutar el servidor unificado
```bash
python server.py
```
O usando Uvicorn directamente:
```bash
uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

Al iniciar verás en los logs la confirmación de FastAPI en `http://localhost:8080`, la sincronización del motor Hermes Agent y la conexión del Bot de Discord.

---

## 🧠 Integración de Hermes Agent (Auto-Mejora)

Hermes Agent le otorga a JARVIS un flujo de aprendizaje autónomo:

### Bucle de Aprendizaje (Closed Loop)
1. **Creación de Skills:** Cuando ejecutas un procedimiento recurrente (ej: despliegues, limpieza de datos, análisis de recibos), Hermes estructura un archivo en `skills/<nombre_skill>.md`.
2. **Consultar Habilidades en Discord:** Puedes preguntarle a JARVIS directamente en el chat:
   > `@Jarvis ¿qué habilidades o skills has aprendido hasta me de hoy?`
3. **Memoria Contextual:** Hermes consulta automáticamente tus preferencias de trabajo guardadas previa ejecución de cualquier script o comando.

---

## 🚀 Tareas Pendientes & Futuras Mejoras (Roadmap)

### 📌 Finanzas & Modelo Kebo
- [ ] **Suscripciones y Gastos Recurrentes:** Módulo para programar alertas de pago automático antes del vencimiento de facturas.
- [ ] **Exportación de Reportes:** Endpoint para descargar estados financieros en CSV y PDF con gráficos mensuales.
- [ ] **Categorización por Machine Learning:** Clasificador automático para comprobantes/facturas adjuntados como imágenes en Discord.

### 🤖 Motor Hermes & Inteligencia Autónoma
- [ ] **Sincronización Cloud para SQLite/FTS5:** Respaldo automático de la base de datos de memoria (`~/.hermes/`) hacia un bucket S3/Firebase Storage para evitar pérdidas en reinicios de dynos de Render.
- [ ] **Ejecución Segura de Scripts (Sandboxing):** Aislamiento de ejecución para código autogenerado por el módulo de skills.
- [ ] **Memoria Episódica Multimodal:** Extensión del índice FTS5 para buscar contexto visual (OCR de tickets guardados) e histórico de audio.

### 🌐 Dashboard, API & Widgets
- [ ] **Autenticación JWT en Dashboard:** Módulo de inicio de sesión con Discord OAuth2 para restringir el acceso al panel web.
- [ ] **Soporte para Interactive Widgets (iOS 17+):** Endpoints interactivos para marcar transacciones o crear gastos rápidos desde la pantalla de inicio de iPhone.
- [ ] **WebSockets en Tiempo Real:** Actualizaciones en tiempo real del Dashboard visual cuando se registra una transacción desde Discord.

---

## 🚀 Despliegue en Vercel (Serverless)

JARVIS está configurado para desplegarse en **Vercel** mediante **Serverless Functions**.

1. **Crear proyecto en Vercel:**
   - Conecta tu repositorio GitHub.
   - Framework: **Other** (funciones serverless).

2. **Comandos de construcción:**
   - `pip install -r requirements.txt`

3. **Variables de entorno en Vercel:**
   - `DISCORD_TOKEN`, `GEMINI_API_KEY`, `FIREBASE_CREDENTIALS`.

4. **Endpoint base para el Widget:**
   - `https://jarvis-two-pi-13.vercel.app/api/widget/dashboard`

---

## 🔄 Estrategia Keep-Alive 24/7 (UptimeRobot)

Para evitar que Vercel suspenda la instancia por inactividad HTTP:

1. Crea un monitor en [UptimeRobot](https://uptimerobot.com/).
2. Configura:
   - **Monitor Type:** `HTTP(s)`
   - **URL:** `https://tu-app-en-vercel.vercel.app/health`
   - **Interval:** `Every 5 minutes`
3. Responde HTTP 200 `{"status": "ok", "bot": "online"}` garantizando un tiempo de actividad continuo.