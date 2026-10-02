# 🤖 JARVIS: Asistente Personal de Discord, Centro Financiero & Agente Autónomo (Hermes)

JARVIS es un asistente inteligente híbrido desplegado en un único proceso asíncrono en **Render.com**. Integra un **Bot de Discord** interactivo, **FastAPI** para servir un Dashboard Web en tiempo real, integración para Widgets de iOS y el motor **Hermes Agent** para capacidades de auto-mejora, memoria persistente a largo plazo y ciclo de aprendizaje autónomo.

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
- **Bot de Discord Interactivo:** Comandos slash/prefijo, atención a notas de voz (TTS/STT con inferencia de miles), procesamiento de adjuntos e imágenes.
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

```text
jarvis/
├── app/                         # Aplicación FastAPI (Servidor Web & API)
│   ├── app/api.py               # Instancia principal de FastAPI, ciclo de vida lifespan y /health
│   ├── app/main.py              # Entrypoint de FastAPI para Uvicorn
│   ├── app/routes/              # Módulos de rutas (dashboard, widgets, kebo, admin)
│   └── app/templates/           # Plantillas HTML del Dashboard
├── bot/                         # Bot de Discord (events, handlers, services)
│   ├── bot/__init__.py          # Instancia de discord.Client / commands.Bot e intents
│   ├── bot/events.py            # Eventos on_ready y on_message
│   ├── bot/events/              # Lógica de mensajes, adjuntos, contextos y TTS
│   └── bot/handlers/            # Manejadores de comandos por categoría
├── modules/                     # Módulos de lógica de negocio y conectores
│   ├── modules/ai.py            # Enrutador de IA (determinístico + Hermes + Gemini)
│   ├── modules/db.py            # Interacción central con Firestore y contexto
│   ├── modules/finance/         # Servicios financieros Kebo
│   └── modules/gemini/          # Integración con Google Gemini API
├── skills/                      # Habilidades (.md / .py) auto-generadas por Hermes Agent
├── tests/                       # Suite de pruebas unitarias automatizadas (unittest/pytest)[cite: 3]
│   └── test_parsers.py          # Cobertura de parsers determinísticos y regex[cite: 3]
├── widgets/                     # Scripts para Widgets (iOS Scriptable / JS)
├── server.py                    # Entrypoint unificado de producción
├── Procfile                     # Configuración de despliegue para Render
├── requirements.txt             # Dependencias de Python
└── AGENTS.md                    # Reglas y guías operativas del agente
```

---

## 🔑 Variables de Entorno Necesarias

Configura un archivo `.env` en la raíz del proyecto para desarrollo local, o define las variables en el panel de Render:

| Variable | Descripción | Requerido | Default |
|---|---|---|---|
| `DISCORD_TOKEN` | Token del Bot de Discord obtenido en el Discord Developer Portal | **Sí** | - |
| `GEMINI_API_KEY` | Clave API de Google Gemini (o `GEMINI_API_KEYS` separadas por coma) | **Sí** | - |
| `FIREBASE_CREDENTIALS` | JSON stringified de la cuenta de servicio de Firebase | **Sí** | - |
| `HERMES_STORAGE_PATH` | Ruta para persistencia de base de datos sqlite y skills | No | `~/.hermes` |
| `PORT` | Puerto HTTP donde escuchará Uvicorn en Render | No | `8080` |
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
DISCORD_TOKEN=tu_token_de_discord
GEMINI_API_KEY=tu_gemini_api_key
FIREBASE_CREDENTIALS={"type": "service_account", ...}
PORT=8080
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

## ☁️ Despliegue en Render (Paso a Paso)

JARVIS está optimizado para ejecutarse en el plan **Free Web Service** de Render utilizando 1 sola instancia.

1. **Crear nuevo Web Service en Render:**
   - Conecta tu repositorio GitHub en Render.
   - Nombre: `jarvis-bot`.
   - Entorno: **Python 3**.

2. **Comandos de Configuración:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`

3. **Variables de Entorno en Render:**
   - Configura `DISCORD_TOKEN`, `GEMINI_API_KEY`, y `FIREBASE_CREDENTIALS`.

---

## 🔄 Estrategia Keep-Alive 24/7 (UptimeRobot)

Para evitar que Render suspenda la instancia por inactividad HTTP:

1. Crea un monitor en [UptimeRobot](https://uptimerobot.com/).
2. Configura:
   - **Monitor Type:** `HTTP(s)`
   - **URL:** `https://tu-app-en-render.onrender.com/health`
   - **Interval:** `Every 5 minutes`
3. Responde HTTP 200 `{"status": "ok", "bot": "online"}` garantizando un tiempo de actividad continuo.