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



# 🤖 Guía Operativa para Asistentes de IA (AGENTS.md)

> **Versión**: v3.2 (2026-09-17)
> **Documentación viva**: ver carpeta `docs/` para arquitectura, esquema de BD y API.

Este documento define la arquitectura, convenciones y reglas operativas para cualquier agente de IA (Claude, Gemini, Cursor, Copilot) que colabore en el proyecto **JARVIS**.

---

## 🏛️ Arquitectura del Sistema

JARVIS funciona 24/7 en modo híbrido:

| Modo | Cuándo | Costo | Latencia |
|---|---|---|---|
| **Determinístico** | 90% de mensajes | $0 | <10ms |
| **Generativo** | Cuando ningún parser coincide | Tokens Gemini | <3s |

### Servicios en producción (Render.com)

| Servicio | Archivo | Función |
|---|---|---|
| **Background Worker** | `jarvis_discord.py` | Bot Discord persistente |
| **Web Service** | `server.py` → `app/main.py` | FastAPI + Dashboard |

### Flujo de mensajes

```text
Discord → bot/events.py:on_message
       → procesar_intencion_natural() [modules/ai.py]
       → parsers determinísticos
       → respuesta directa
       → si no hay match: pensar_respuesta() → Gemini
```

Para más detalle, consultar [`docs/architecture.md`](docs/architecture.md).

---

## 🗄️ Base de Datos

Motor: Firebase Firestore, modelo Kebo, con raíz `users/{userId}/`.

```text
users/{userId}/
├── accounts/{accountId}
├── categories/{categoryId}/subcategories/{subcategoryId}
├── budgets/{YYYY-MM}/items/{budgetItemId}
├── transactions/{YYYY-MM}/items/{transactionId}
├── goals/{goalId}
├── recurring/{recurringId}
└── reminders/{reminderId}
```

Reglas críticas:

1. Los periodos usan dos dígitos: `2026-09`, nunca `2026-9`.
2. Un presupuesto es un **techo mensual**, no dinero separado; nunca se resta de `accounts.balance`.
3. Un presupuesto solo se compara con gastos del mismo periodo `YYYY-MM`.
4. El contexto para Gemini debe distinguir `LIQUIDEZ_CUENTAS`, `MES_ACTUAL`, `PRESUPUESTOS_MES` e `HISTORICO`.
5. No guardar tokens, contraseñas ni credenciales bancarias en Firestore o Git.

El esquema completo está en [`docs/database-schema.md`](docs/database-schema.md).

---

## ⚠️ Reglas para agentes

### 1. Preservar parsers determinísticos

- **Nunca** reemplazar parsers de `modules/ai.py` por llamadas directas al LLM.
- Todo parser nuevo debe tener pruebas en `tests/test_parsers.py`.
- Las mutaciones de Firestore deben ejecutarse solamente mediante flujo determinístico explícito.
- Gemini opera en modo de solo lectura y nunca debe afirmar que modificó datos.

### 2. Imports a nivel de módulo

Evitar imports dentro de bloques condicionales porque pueden causar `UnboundLocalError`:

```python
# Correcto
import re

def buscar(texto):
    return re.search(r"...", texto)
```

### 3. Notas de voz

Con `es_audio=True`, un monto menor que 1000 puede representar miles de COP: `150` → `$150,000`.

### 4. Categorías

Usar `_coincidir_categoria()` o `_cat_exacta()` de `modules/db.py`. La comparación tolera acentos, mayúsculas y puntuación, priorizando coincidencia exacta antes de parcial.

### 5. Consultas financieras

- `q categorias hay` debe listar categorías, cuentas y presupuestos, no caer a Gemini.
- `dame un analisis financiero` debe usar el periodo actual por defecto.
- `deja lo que sobra` no crea ni modifica presupuestos automáticamente.
- `ajustar mi balance a los presupuestos` debe explicar que son conceptos diferentes y no mutar saldos.
- No comparar techos de septiembre con gastos históricos.

### 6. Tono

Respuestas directas pero amables:

- No regañar ni contradecir de forma condescendiente.
- Si falta información, explicar qué dato falta.
- En frases ambiguas, ofrecer una interpretación y un comando concreto.

### 7. Windows y UTF-8

```bash
PYTHONIOENCODING=utf-8 py -3 script.py
```

En Python:

```python
sys.stdout.reconfigure(encoding="utf-8")
```

### 8. Cambios en documentación

Cuando cambien arquitectura, esquema o rutas:

1. Actualizar el Markdown correspondiente en `docs/`.
2. Actualizar `AGENTS.md` si cambia una regla operativa.
3. Actualizar tests y ejecutar la suite.
4. Mantener `TODO.md` alineado con el estado real.

---

## 🧪 Verificación

```bash
py -3 -m unittest tests.test_parsers -v
```

Las rutas FastAPI se documentan en [`docs/api-endpoints.md`](docs/api-endpoints.md).

---

## 📚 Archivos de contexto

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/database-schema.md`](docs/database-schema.md)
- [`docs/api-endpoints.md`](docs/api-endpoints.md)
- [`TODO.md`](TODO.md)
- [`README.md`](README.md)


# 📋 JARVIS - Lista de Tareas y Hoja de Ruta (TODO List)

> **Documento vivo para desarrolladores y agentes de IA (Claude, Gemini, Antigravity, Cursor, Copilot).**  
> Última actualización: Septiembre 2026

---

## 🧭 Visión General del Proyecto

JARVIS es un asistente ejecutivo y financiero personal integrado con Discord, FastAPI y Google Gemini, respaldado por Firebase Firestore (modelo Kebo).  
Está desplegado 24/7 en **Render.com** mediante dos servicios independientes:
1. **Background Worker** (`jarvis_discord.py`): Bot de Discord 24/7.
2. **Web Service** (`server.py`): API REST y Dashboard HTML.

### Flujo Central de Mensajes
```
Mensaje Discord / Audio
       │
       ▼
bot/events.py (limpieza de menciones)
       │
       ├──> ¿Es intención determinística? ──> procesar_intencion_natural() ──> [Firestore directo] ──> Respuesta inmediata
       │                                                                                                    │
       └──> No (complejo / conversacional) ───────────────────────────────────────────────────────────────┘
                     │
                     ▼
             pensar_respuesta() con contexto financiero inyectado ──> Gemini API (con rotación de keys) ──> Respuesta
```

---

## 📊 Estado Actual del Tablero

### 🟢 1. Completado Recientemente (Septiembre 2026 - v3.1)

- [x] **CRUD Completo de Presupuestos en Firestore (Kebo Style)**:
  - `establecer_presupuesto_mes`: Creación y actualización múltiple por mes (`users/{userId}/budgets/{YYYY-MM}/items`).
  - `modificar_presupuesto_mes`: Edición de montos de presupuestos existentes.
  - `renombrar_presupuesto_mes`: Renombramiento de categoría manteniendo el presupuesto.
  - `eliminar_presupuesto_mes`: Eliminación de presupuesto individual.
  - `eliminar_todos_presupuestos_mes`: Borrado masivo de todos los presupuestos de un mes.
- [x] **Inferencia de Miles en Notas de Voz**:
  - `es_audio=True` transmitido desde `bot/events.py` a `procesar_intencion_natural`.
  - Montos `< 1000` en contexto de presupuesto se normalizan automáticamente multiplicando por 1,000 (ej: `150` -> `$150,000`).
- [x] **Parser Bidireccional de Lenguaje Natural**:
  - Reconocimiento de categorías antes del monto (`mamá 150.000`) y después del monto (`150 para mamá`).
  - Limpieza agresiva de muletillas, saludos (`hola yerbis`), conectores y nombres de meses.
- [x] **Búsqueda Difusa de Categorías**:
  - Función `_coincidir_categoria` en `modules/db.py` insensible a tildes, mayúsculas y puntuación.
- [x] **Consulta de Dinero y Balance Inmediata**:
  - Detección determinística para consultas como `@Jarvis cuanto dinero tengo disponible` o `cuanta plata tengo`.
- [x] **Corrección de Scoping en Python**:
  - Eliminación de imports locales redundantes (`import re`) dentro de bloques condicionales que producían `UnboundLocalError`.

---

### 🟡 2. Tareas Inmediatas / Próximo Sprint (Alta Prioridad)

- [x] **Limpieza de Documentos Corruptos en Firestore**:
  - *Contexto*: Pruebas anteriores con el parser viejo crearon documentos con nombres como `"Hola, Yerbis. Yerbis, Puedes Poner"` y `"Mamá Deudas,"`.
  - *Implementado*: Script `scripts/cleanup_budgets_sep2026.py` ejecutado con éxito. Estado final:
    - Casa: $150,000
    - Mamá: $150,000
    - Deudas: $205,000
    - Sin documentos corruptos.
- [x] **Suite de Pruebas Unitarias Automatizadas (`tests/`)**:
  - *Contexto*: El parser determinístico tiene múltiples regex y stop-words que deben verificarse contra regresiones.
  - *Acción*: Crear `tests/test_parsers.py` con `pytest` cubriendo:
    - `_parse_presupuesto_multiple` (texto y notas de voz con y sin conectores).
    - `_parse_editar_presupuesto` (cambios de monto).
    - `_parse_renombrar_presupuesto` (cambios de nombre de categoría).
    - `_parse_borrar_presupuesto` (individual y masivo `todos`).
    - `_coincidir_categoria` (tildes, mayúsculas, substrings).
- [x] **Confirmación para Borrado Masivo**:
  - *Contexto*: Si un usuario dice `borra todos los presupuestos de septiembre`, se eliminan sin confirmación previa.
  - *Implementado*: Se guarda una confirmación por usuario durante cinco minutos. El bot solo ejecuta `eliminar_todos_presupuestos_mes` al recibir `confirmar presupuestos`; `cancelar presupuestos` la elimina.
- [x] **GitHub Actions CI para Tests**:
  - *Implementado*: `.github/workflows/test.yml` instala dependencias y ejecuta la suite estándar `python -m unittest discover -v` en push y pull request a `main`.

---

### 🔵 3. Gestión Financiera & Modelo Kebo (Prioridad Media)

- [ ] **Function Calling Nativo con Gemini Tools**:
  - *Contexto*: Actualmente el fallback a Gemini solo genera texto y no puede modificar la base de datos de forma autónoma.
  - *Estado*: No implementar escrituras autónomas de Gemini. La regla operativa exige que Gemini sea solo lectura; cualquier futura herramienta debe limitarse a propuestas que se revaliden mediante el router determinístico y confirmación explícita del usuario.
- [ ] **Reportes Financieros en PDF / Excel**:
  - *Acción*: Crear endpoint `/api/reportes/mensual` que genere un balance descargable con gráficos y tablas de transacciones.
- [x] **Categorización Automática de Gastos**:
  - *Implementado*: `modules/finance/transactions/search.py:obtener_sugerencias_categoria` reconoce comercios colombianos comunes (D1, Éxito, Carulla, Oxxo, Ara, Rappi, Uber, DiDi y otros) antes de consultar el historial.
- [ ] **Manejo de Metas de Ahorro Interactivas**:
  - *Acción*: Agregar comandos directos para metas (`!meta crear [nombre] [monto] [fecha]` y `!meta abonar [nombre] [monto]`).
- [x] **Transferencias entre Cuentas en Lenguaje Natural**:
  - *Implementado*: Refactorización de `modules/finance/transactions/` completada. Parser para frases como `"pasé 50.000 de Bancolombia a Nequi"` invoca `registrar_transferencia`.

---

### 🟣 4. Audio & Multimodal (Prioridad Media/Baja)

- [ ] **Audio Multi-Intención**:
  - *Contexto*: Si el usuario envía un audio largo diciendo *"Hola Jarvis, gasté 20k en taxi y recuérdame pagar la luz mañana"*, actualmente se procesa como una sola intención.
  - *Acción*: Permitir splitting de oraciones compuestas en audios transcritos para ejecutar múltiples acciones atómicas.
- [ ] **OCR de Recibos y Facturas Detallado**:
  - *Acción*: Extraer tabla de productos individuales en `pensar_respuesta_imagen` cuando se sube una foto de factura.
- [ ] **Soporte de Mensajes de Voz en Canales de Voz de Discord**:
  - *Acción*: Conectar bot a canal de voz para interactuar en tiempo real (modo asistente presencial).

---

### ⚙️ 5. Infraestructura y DevOps

- [ ] **Monitoreo de Cuota y Latencia de Gemini**:
  - *Acción*: Logging estructurado del tiempo de respuesta y de las keys activas en `_clientes_cache`.
- [ ] **Dashboard Web Interactivo (`templates/dashboard.html`)**:
  - *Acción*: Integrar Chart.js para visualización de balance mensual, gastos por categoría y estado de presupuestos.
- [ ] **Webhook de Notificaciones Discord para Alertas Críticas**:
  - *Acción*: Verificar que el cron `alertas.py` se dispare periódicamente vía GitHub Actions sin agotar límites de Render.

---

## 📌 Guía Rápida para Agentes de IA

Cuando trabajes en este repositorio, recuerda:
1. **Nunca elimines los parsers determinísticos** en `modules/ai.py`: Filtran el 90% de los mensajes sin consumir cuota de Gemini.
2. **Cuidado con las importaciones dentro de funciones**: Python marcará la variable como local para todo el scope si detecta un `import X` dentro de un condicional.
3. **Estructura Firestore**: Siempre usa `budgets/{YYYY-MM}/items` y normaliza el mes a dos dígitos (`09`, no `9`).
4. **Encoding en Windows**: Asegúrate de que las operaciones de consola o tests manejen UTF-8 (`sys.stdout.reconfigure(encoding='utf-8')`).


# 🧠 JARVIS — Identidad y Personalidad del Agente

## Quién soy

Soy **JARVIS**, un copiloto personal y financiero inteligente. Opero 24/7 como un agente autónomo capaz de razonar, actuar y auto-corregirme para resolver las necesidades del usuario.

## Rol Principal

Asistente financiero ejecutivo y proactivo. Mi objetivo es ayudar al usuario a **entender, organizar y optimizar** sus finanzas personales usando datos reales almacenados en su base de datos.

## Capacidades

- **Gestión de cuentas**: Consultar saldos, crear cuentas, actualizar balances.
- **Transacciones**: Registrar ingresos, gastos y transferencias entre cuentas.
- **Presupuestos**: Crear, consultar y ajustar techos de gasto mensuales por categoría.
- **Recordatorios**: Crear y listar recordatorios de pagos o actividades.
- **Análisis financiero**: Proveer contexto financiero con liquidez, mes actual, presupuestos e histórico.
- **Habilidades aprendidas**: Almacenar y consultar preferencias, reglas y acuerdos del usuario.
- **Razonamiento**: Usar ciclos ReAct (Reason → Act → Observe) para resolver consultas complejas paso a paso.
- **Auto-corrección**: Si una acción falla, analizo el error y reintento con una estrategia diferente (hasta 3 veces).

## Principios de Comportamiento

1. **Directo pero amable**: Respondo con precisión sin ser condescendiente ni regañar.
2. **Basado en datos**: Siempre uso los datos reales del usuario. Nunca invento cifras.
3. **Proactivo**: Si detecto oportunidades de ahorro, alertas de presupuesto o patrones, los menciono.
4. **Transparente**: Si no puedo ejecutar una acción, explico por qué y sugiero alternativas.
5. **Seguro**: Nunca almaceno tokens, contraseñas ni credenciales bancarias.
6. **Contextual**: Distingo entre liquidez de cuentas, presupuestos (techos de gasto) e histórico.

## Reglas Financieras Críticas

- Un **presupuesto** es un techo mensual de gasto, NO dinero separado. Nunca se resta de `accounts.balance`.
- Las comparaciones presupuesto/gasto usan el **mismo periodo YYYY-MM**.
- Los periodos siempre usan dos dígitos: `2026-09`, nunca `2026-9`.
- No confundir liquidez con presupuesto.
- No mutar datos sin instrucción explícita del usuario.

## Tono de Comunicación

- Conciso: máximo 2-3 párrafos por respuesta salvo análisis complejos.
- Usa emojis con moderación (1-2 por mensaje).
- En español colombiano, natural y cercano.
- Si la frase del usuario es ambigua, ofrezco una interpretación + un comando concreto.
- Moneda base: COP (pesos colombianos). Formatea montos con separador de miles.

## Idioma

Español (Colombia) por defecto. Respondo en el idioma en que me escriban.


