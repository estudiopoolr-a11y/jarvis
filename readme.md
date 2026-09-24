# 🤖 JARVIS: Asistente Personal de Discord & Centro de Control Financiero

JARVIS es un asistente inteligente híbrido desplegado en un único proceso asíncrono. Integra un **Bot de Discord** interactivo con **FastAPI** para servir un Dashboard Web en tiempo real y endpoints de integración para Widgets de iOS.

---

## 🌟 Descripción General

JARVIS opera 24/7 combinando un modelo de procesamiento híbrido:
1. **Flujo Determinístico (~90% de los casos):** Respuestas instantáneas (<10ms) y operaciones financieras precisas sin costo de tokens.
2. **Flujo Generativo (Gemini API):** Procesamiento de lenguaje natural, análisis de voz/audio, visión computacional y fallback inteligente.

### Funcionalidades Clave
- **Finanzas Personales (Modelo Kebo en Firebase Firestore):** Control de cuentas, presupuestos mensuales, gastos/ingresos, préstamos y análisis consolidado.
- **Bot de Discord Interactivo:** Comandos slash/prefijo, atención a notas de voz (TTS/STT), procesamiento de adjuntos e imágenes.
- **Dashboard Web & API para Widgets:** Interfaz visual interactiva y endpoints JSON optimizados (`/api/widget/dashboard`) para el widget de iPhone.
- **Proceso Único Asíncrono:** Servidor HTTP FastAPI y Bot de Discord conviven en el mismo ciclo de eventos (`asyncio`) para ejecutarse en el plan gratuito de Render.

---

## 📁 Estructura del Proyecto

```text
jarvis/
├── [`app/`](app)                         # Aplicación FastAPI (Servidor Web & API)
│   ├── [`app/api.py`](app/api.py)           # Instancia principal de FastAPI, ciclo de vida lifespan y /health
│   ├── [`app/main.py`](app/main.py)         # Entrypoint de FastAPI para Uvicorn
│   ├── [`app/routes/`](app/routes)         # Modulos de rutas (dashboard, widgets, kebo, admin, etc.)
│   └── [`app/templates/`](app/templates)   # Plantillas HTML del Dashboard
├── [`bot/`](bot)                         # Bot de Discord (events, handlers, services)
│   ├── [`bot/__init__.py`](bot/__init__.py) # Instancia de discord.Client / commands.Bot e intents
│   ├── [`bot/events.py`](bot/events.py)     # Eventos on_ready y on_message
│   ├── [`bot/events/`](bot/events)         # Lógica de mensajes, adjuntos, contextos y TTS
│   └── [`bot/handlers/`](bot/handlers)     # Manejadores de comandos por categoría
├── [`modules/`](modules)                 # Módulos de lógica de negocio y conectores
│   ├── [`modules/ai.py`](modules/ai.py)     # Enrutador de IA (determinístico + Gemini)
│   ├── [`modules/db.py`](modules/db.py)     # Interacción central con Firestore
│   ├── [`modules/finance/`](modules/finance)# Servicios financieros Kebo
│   └── [`modules/gemini/`](modules/gemini) # Integración con Google Gemini API
├── [`widgets/`](widgets)                 # Scripts para Widgets (iOS Scriptable / JS)
├── [`server.py`](server.py)               # Entrypoint unificado de producción
├── [`Procfile`](Procfile)                 # Configuración de despliegue para Render
├── [`requirements.txt`](requirements.txt) # Dependencias de Python
└── [`AGENTS.md`](AGENTS.md)               # Reglas y guías operativas del proyecto
```

---

## 🔑 Variables de Entorno Necesarias

Configura un archivo `.env` en la raíz del proyecto para desarrollo local, o define las variables en el panel de Render:

| Variable | Descripción | Requerido | Default |
|---|---|---|---|
| `DISCORD_TOKEN` | Token de Bot de Discord obtenido en el Discord Developer Portal | **Sí** | - |
| `GEMINI_API_KEY` | Clave API de Google Gemini (o `GEMINI_API_KEYS` separadas por coma) | **Sí** | - |
| `FIREBASE_CREDENTIALS` | JSON stringified de la cuenta de servicio de Firebase | **Sí** | - |
| `PORT` | Puerto HTTP donde escuchará Uvicorn en Render | No | `8080` |
| `DISCORD_WEBHOOK_URL` | Webhook para alertas y reportes automáticos | No | - |

---

## 💻 Instalación y Ejecución Local

### 1. Clonar el repositorio e instalar dependencias
```bash
git clone https://github.com/tu-usuario/jarvis.git
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
PORT=8080
```

### 3. Ejecutar el servidor unificado
```bash
python server.py
```
O usando Uvicorn directamente:
```bash
uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

Al iniciar verás en logs la confirmación del servidor FastAPI en `http://localhost:8080` y la conexión de [`on_ready`](bot/events.py:10) del Bot de Discord.

---

## ☁️ Despliegue en Render (Paso a Paso)

JARVIS está optimizado para ejecutarse en el plan **Free Web Service** de Render utilizando 1 sola instancia.

1. **Crear nuevo Web Service en Render:**
   - Conecta tu repositorio GitHub en Render.
   - Selecciona el tipo de servicio: **Web Service**.
   - Nombre: `jarvis-bot`.
   - Entorno: **Python 3**.

2. **Comandos de Configuración:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT` (o `python server.py`)

3. **Variables de Entorno en Render:**
   - Agrega `DISCORD_TOKEN`, `GEMINI_API_KEY`, `FIREBASE_CREDENTIALS` (o `FIREBASE_KEY`).
   - Render asigna automáticamente la variable `PORT`.

---

## 🔄 Estrategia Keep-Alive 24/7 (UptimeRobot)

Las instancias gratuitas de Render se suspenden tras 15 minutos de inactividad HTTP. Para mantener JARVIS activo 24/7 sin suspensiones:

1. Registra una cuenta en [UptimeRobot](https://uptimerobot.com/).
2. Crea un nuevo Monitor con las siguientes opciones:
   - **Monitor Type:** `HTTP(s)`
   - **Friendly Name:** `JARVIS Health Check`
   - **URL (or IP):** `https://tu-app-en-render.onrender.com/health`
   - **Monitoring Interval:** `Every 5 minutes`
3. Guarda el monitor. UptimeRobot realizará un ping HTTP `GET /health` cada 5 minutos, respondiendo HTTP 200 `{"status": "ok", "bot": "online"}` y evitando que Render suspenda la instancia.
