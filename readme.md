<!-- cSpell:disable -->
# 🤖 Proyecto JARVIS - Asistente Personal Inteligente

> **"Sistemas en línea. JARVIS v3.0 Operativo."**

Asistente personal integrado con inteligencia artificial (Gemini) y automatización para la gestión de tareas, finanzas y notas de voz. Diseñado para ser tu asistente ejecutivo personal, frío, analítico y eficiente. Desplegado 24/7 en Render con bot de Discord persistente.

---

## 📋 Tabla de Contenidos

1. [¿Qué es JARVIS?](#-qué-es-jarvis)
2. [Características Principales](#-características-principales)
3. [Arquitectura del Sistema](#-arquitectura-del-sistema)
4. [Estructura del Proyecto](#-estructura-del-proyecto)
5. [Inicio Rápido Local](#-inicio-rápido-local)
6. [Despliegue en Render 24/7](#-despliegue-en-render-247)
7. [Uso en Discord](#-uso-en-discord)
8. [Ejemplos de Mensajes](#-ejemplos-de-mensajes)
9. [Dashboard Web](#-dashboard-web)
10. [API REST](#-api-rest)
11. [Automatización (Cron Jobs)](#-automatización-cron-jobs)
12. [Alertas Proactivas](#-alertas-proactivas)
13. [Optimización y Arquitectura](#-optimización-y-arquitectura)
14. [Variables de Entorno](#-variables-de-entorno)
15. [Troubleshooting](#-troubleshooting)
16. [Historial de Cambios](#-historial-de-cambios)
17. [Roadmap](#-roadmap)
18. [Contribuir](#-contribuir)

---

## 🎯 ¿Qué es JARVIS?

JARVIS es un **asistente personal ejecutivo** que combina:
- 🤖 **IA Generativa** (Google Gemini) con rotación automática de API keys
- 💬 **Bot de Discord** persistente 24/7
- 💰 **Gestión financiera personal** (ingresos, gastos, presupuestos)
- 📋 **Gestión de tareas** con prioridades y fechas límite
- 🚨 **Alertas proactivas** automáticas vía Discord
- 📊 **Resúmenes diarios y semanales** automáticos
- 🌐 **Dashboard web** con visualización en tiempo real

Está diseñado para funcionar como un **mayordomo digital**: ejecuta tareas, monitorea tu salud financiera, te alerta sobre problemas y responde preguntas complejas sobre tus datos.

### ¿Por qué JARVIS?

| Problema                     | Solución de JARVIS                            |
| ---------------------------- | --------------------------------------------- |
| Perder el control de gastos  | Registro automático + detección de anomalías  |
| Olvidar tareas importantes   | Tareas con prioridad + alertas de vencimiento |
| Necesitar consultar finanzas | Balance en tiempo real + resúmenes            |
| Sobrecargar la API de Gemini | Parsers determinísticos (90% sin Gemini)      |
| Caídas del servicio          | Bot separado del web service en Render        |
| Rate limits (429)            | Rotación automática entre 5 API keys          |

---

## ✨ Características Principales

### 💰 Gestión Financiera Inteligente
- **Registro automático de ingresos y gastos** a través de lenguaje natural
- **Carga masiva de datos** mediante prompt estructurado (presupuestos + transacciones en un solo mensaje)
- **Presupuestos por categoría** con alertas proactivas cuando se acercan al límite
- **Balance financiero en tiempo real** con ingresos, gastos y neto
- **Historial de transacciones** almacenado de forma segura en Firebase
- **Procesamiento de recibos** mediante IA (extrae monto, establecimiento y categoría)
- **Detección de gastos anormales** (gastos que superan 2x del promedio histórico)

### 📋 Gestión de Tareas
- **Creación de tareas** con prioridad (Alta/Media/Baja) y fecha límite
- **Lista de pendientes** siempre actualizada
- **Marcado de completado** mediante búsqueda inteligente
- **Detección de tareas vencidas** y próximas a vencer
- **Recordatorios contextuales** basados en tu carga de trabajo

### 🧠 Inteligencia Artificial Avanzada
- **Análisis de inversiones** combinando datos en vivo de Yahoo Finanzas y búsqueda web
- **Comprensión de lenguaje natural** para intenciones complejas
- **Fundamentación en datos reales**: la IA responde ÚNICAMENTE con información de tu base de datos
- **Modo voz** con respuesta de audio mediante Google Text-to-Speech
- **Rotación automática de hasta 5 API Keys de Gemini** (round-robin ante 429)

### 🖥️ Múltiples Interfaces
- **Discord Bot**: Comandos, menciones de usuario y menciones de rol (`<@&ID>`)
- **Dashboard Web**: Visualización en tiempo real con FastAPI
- **API REST**: Endpoints para integraciones externas
- **Procesamiento de multimedia**: Imágenes (recibos) y audio (notas de voz)
- **Notificaciones vía Webhook de Discord**: Resúmenes automáticos

### 🚨 Alertas Proactivas (Fase 3)
- **Presupuestos críticos** (>90% del límite)
- **Presupuestos en advertencia** (>80% del límite)
- **Tareas vencidas** con días de retraso
- **Tareas próximas a vencer** (≤2 días)
- **Gastos anormales** (>2x del promedio histórico)
- **Resumen semanal** cada domingo con comparación vs semana anterior

### 🔐 Privacidad y Seguridad
- **Datos almacenados exclusivamente en tu proyecto Firebase**
- **Ninguna información financiera se envía a terceros** excepto para Gemini
- **Variables de entorno** para credenciales sensibles
- **Safety settings configuradas** para evitar contenido inapropiado

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Componentes

```
┌──────────────────────────────────────────────────────────────────┐
│                        USUARIO FINAL                              │
│  (Discord, Dashboard Web, API REST, iPhone Shortcut)             │
└──────────────────────────────────────────────────────────────────┘
         │                    │                    │
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  DISCORD BOT    │  │  DASHBOARD WEB  │  │  API REST       │
│  (24/7)         │  │  (Render)       │  │  (Render)       │
│                 │  │                 │  │                 │
│  Mención @Jarvis│  │  GET /          │  │  POST /api/     │
│  !finanzas      │  │  GET /dashboard │  │  comando        │
│  !tareas        │  │  HTML Render    │  │  POST /api/     │
│  Audio/Imágenes │  │                 │  │  recibo         │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PROCESAMIENTO JARVIS                           │
│                                                                   │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │  Parsers     │───▶│  Gemini AI   │───▶│  Firebase    │     │
│   │  Determiníst.│    │  (fallback)  │    │  Firestore   │     │
│   │  90% casos   │    │  10% casos   │    │              │     │
│   └──────────────┘    └──────────────┘    └──────────────┘     │
│                              │                                   │
│                              ▼                                   │
│                    ┌──────────────────┐                          │
│                    │  Alertas         │                          │
│                    │  Proactivas      │                          │
│                    └──────────────────┘                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    AUTOMATIZACIÓN (CRON)                          │
│                                                                   │
│  GitHub Actions (cada 30 min):  daily-summary.yml                 │
│  GitHub Actions (domingo 8am):  weekly-summary.yml                │
│  GitHub Actions (cada 30 min):  alertas (junto con daily)         │
│                                                                   │
│  UptimeRobot (cada 5 min):       ping a Render Web Service        │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Discord Webhook │
                    │  (Notificaciones)│
                    └──────────────────┘
```

### Flujo de una Petición Típica

```
Usuario: "@Jarvis gasté 50000 en mercado"
   │
   ▼
[1] Discord Bot recibe mensaje
   │
   ▼
[2] Limpia menciones de usuario/rol (<@ID>, <@&ID>)
   │
   ▼
[3] Parser determinístico detecta "gast[oáé]" + monto
   │
   ▼
[4] Registra en Firebase: tipo=gasto, monto=50000, categoria=...
   │
   ▼
[5] Responde sin llamar a Gemini (¡ahorro de API!)
   │
   ▼
Usuario: "✅ Gasto registrado: $50,000 en Mercado"
```

### Flujo cuando el Parser no Detecta

```
Usuario: "@Jarvis cuánto llevo gastado en mujeres este mes?"
   │
   ▼
[1] Discord Bot recibe mensaje
   │
   ▼
[2] Limpia menciones
   │
   ▼
[3] Parser determinístico NO detecta intención directa
   │
   ▼
[4] Gemini AI analiza intención con contexto
   │
   ▼
[5] Consulta Firebase (últimos 10 movimientos, presupuestos)
   │
   ▼
[6] Gemini genera respuesta con datos reales
   │
   ▼
Usuario: "📊 En Women llevas $150,000 / $300,000 (50%)"
```

---

## 📂 Estructura del Proyecto

```
jarvis/
│
├── .env                      # 🔒 Variables de entorno y credenciales (NO subir a git)
├── .gitignore
├── iniciar_claude.bat        # 🤖 Script para Claude Code integration
├── jarvis_discord.py         # 💬 Bot de Discord principal (corre en Render Background Worker)
├── server.py                 # 🌐 Servidor web FastAPI con dashboard y endpoints
├── daily_summary.py          # 📅 Genera resumen diario a Discord (vía webhook)
├── readme.md                 # 📖 Este archivo
├── requirements.txt          # 📦 Dependencias de Python
├── serviceAccountKey.json    # 🔐 Credenciales de Firebase (NO subir a git)
│
├── audio_cache/              # 🎵 Carpeta temporal para procesamiento de notas de voz
│
├── modules/                  # 🧩 Módulos de lógica separada
│   ├── database.py           # 🗃️ Integración con Firebase Firestore
│   ├── ai_brain.py           # 🧠 Lógica de IA con parsers determinísticos + rotación de API Keys
│   └── alertas.py            # 🚨 Alertas proactivas (presupuestos, tareas, gastos anormales)
│
└── .github/
    └── workflows/            # ⚙️ GitHub Actions (cron jobs)
        ├── daily-summary.yml # 📅 Ejecuta resumen diario cada 30 min (7am-12pm, 7pm-12am COL)
        └── weekly-summary.yml # 📊 Ejecuta resumen semanal cada domingo 8am COL
```

---

## 🚀 Inicio Rápido Local

### Prerrequisitos

| Servicio     | Requisito                            | Dónde obtenerlo                                                       |
| ------------ | ------------------------------------ | --------------------------------------------------------------------- |
| Python       | 3.11+                                | [python.org](https://www.python.org/)                                 |
| Google Cloud | API de Gemini habilitada             | [console.cloud.google.com](https://console.cloud.google.com/)         |
| Firebase     | Firestore API habilitada             | [firebase.google.com](https://firebase.google.com/)                   |
| Discord      | Bot con Message Content Intent       | [discord.com/developers](https://discord.com/developers/applications) |
| API Keys     | 1-5 keys de Gemini (recomendado: 3+) | [aistudio.google.com](https://aistudio.google.com/)                   |

### Instalación

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/jarvis.git
cd jarvis

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 4. Colocar credenciales de Firebase
# Descargar JSON desde Firebase Console > Cuentas de servicio
# Renombrar a serviceAccountKey.json

# 5. Iniciar JARVIS (2 procesos separados)
python jarvis_discord.py  # Terminal 1: Bot Discord
python server.py          # Terminal 2: Dashboard + API
```

### Verificar Instalación

```bash
# El dashboard debería responder en:
curl http://localhost:10000/

# El bot debería estar en línea en Discord
# El endpoint de comando debería funcionar:
curl -X POST http://localhost:10000/api/comando \
  -H "Content-Type: application/json" \
  -d '{"texto": "hola", "usuario_id": "test"}'
```

---

## ☁️ Despliegue en Render 24/7

JARVIS está configurado para correr **24/7 en Render** usando dos servicios separados.

### 🟦 Web Service (Dashboard + API)
- **Tipo**: Web Service
- **Comando de inicio**: `python server.py`
- **Puerto**: 10000
- **Duerme tras 15 min de inactividad** (UptimeRobot lo mantiene activo)
- **URL ejemplo**: `https://jarvis-h20g.onrender.com`

### 🟨 Background Worker (Bot Discord)
- **Tipo**: Background Worker
- **Comando de inicio**: `python jarvis_discord.py`
- **NO se duerme** - corre 24/7
- **Variables de entorno**: Mismas que el Web Service

### Diagrama de Despliegue

```
┌──────────────────────────────────────────────────────────┐
│                        RENDER.COM                         │
│                                                           │
│  ┌────────────────────────┐  ┌────────────────────────┐  │
│  │   WEB SERVICE          │  │   BACKGROUND WORKER    │  │
│  │                        │  │                        │  │
│  │  python server.py      │  │  python jarvis_discord │  │
│  │  Puerto: 10000         │  │  (24/7 sin dormir)     │  │
│  │                        │  │                        │  │
│  │  • Dashboard HTML      │  │  • Bot Discord activo  │  │
│  │  • API REST            │  │  • Escucha menciones   │  │
│  │  • Endpoints /api/*    │  │  • Procesa mensajes    │  │
│  │                        │  │                        │  │
│  │  ⚠️ Duerme a 15 min   │  │  ✅ Siempre activo     │  │
│  └────────────────────────┘  └────────────────────────┘  │
│           ▲                                                │
│           │ ping cada 5 min                                │
│           │                                                │
│  ┌────────┴────────┐                                       │
│  │  UptimeRobot    │                                       │
│  │  (externo)      │                                       │
│  └─────────────────┘                                       │
└──────────────────────────────────────────────────────────┘
                              ▲
                              │
                              │ GET /api/cron/*
                              │
                ┌─────────────┴─────────────┐
                │     GITHUB ACTIONS        │
                │  (Cron gratuito)          │
                │                           │
                │  • daily-summary.yml      │
                │  • weekly-summary.yml     │
                └───────────────────────────┘
```

### Pasos para Desplegar

1. **Conectar repositorio en [render.com](https://render.com)**
2. **Crear Web Service** apuntando a `server.py`
3. **Crear Background Worker** apuntando a `jarvis_discord.py`
4. **Copiar variables de entorno** en ambos servicios
5. **Configurar [UptimeRobot](https://uptimerobot.com)** para hacer ping cada 5-10 min al Web Service

### ⚠️ Error 405 Method Not Allowed

Si usas UptimeRobot, **asegúrate** de que el Web Service soporte **HEAD requests** (UptimeRobot usa HEAD por defecto para ahorrar ancho de banda).

**Solución implementada en `server.py`:**
```python
@app.get("/")
@app.head("/")  # ← Soporte para UptimeRobot
def render_dashboard():
    ...
```

Si ves este error en los logs de UptimeRobot:
```
HTTP 405 - Method Not Allowed
```
Significa que el servidor no está aceptando HEAD. Verifica que el push a GitHub incluya los cambios con `@app.head`.

---

## 💬 Uso en Discord

Una vez que el bot esté en línea, mencionalo con `@Jarvis` o al rol configurado (`<@&ID>`).

### Comandos Rápidos (Slash)

| Comando                | Descripción                                             |
| ---------------------- | ------------------------------------------------------- |
| `!finanzas`            | Balance completo con últimos movimientos                |
| `!presupuestos`        | Estado de todos los presupuestos con barras de progreso |
| `!historial [N]`       | Últimas N transacciones (default: 20)                   |
| `!buscar <término>`    | Busca por categoría o descripción                       |
| `!estado`              | Estado del sistema: API keys, datos, modo               |
| `!ayuda`               | Lista completa de comandos disponibles                  |
| `!tareas`              | Lista de tareas pendientes                              |
| `!hecho "descripción"` | Marca tarea como completada                             |
| `!dormir 8`            | Silencia notificaciones por 8 horas                     |
| `!pausar 2`            | Pausa notificaciones por 2 horas                        |
| `!voz`                 | Activa/desactiva respuestas de audio TTS                |
| `!inversion AAPL`      | Análisis de acción de Apple                             |
| `!borrar confirmar`    | Borra TODOS tus datos (con confirmación)                |
| `!mes [mes]`           | Resumen de mes específico (ej: !mes agosto)             |
| `!stats`               | Estadísticas: promedios, proyecciones, anomalías        |
| `!top [N]`             | Top N categorías con más gastos (default: 5)            |

### Comandos con Menciones

#### 💰 Comandos Financieros
- `@Jarvis gasto 50 en supermercado` - Registra un gasto
- `@Jarvis ingreso 1000 trabajo freelance` - Registra un ingreso
- `@Jarvis presupuesto Alimentación 15000` - Establece presupuesto
- `@Jarvis finanzas` - Muestra balance completo y historial
- `@Jarvis debo 20000 préstamo` - Registra una deuda como gasto

#### 📋 Gestión de Tareas
- `@Jarvis tarea llamar al médico mañana Alta` - Crea tarea
- `@Jarvis tareas` - Lista tareas pendientes
- `@Jarvis hecho llamar al médico` - Marca como completada
- `@Jarvis borra todos los datos` - Reinicia la base de datos

#### 🧠 Análisis y Consultas
- `@Jarvis inversión AAPL` - Analiza acción de Apple
- `@Jarvis buscar últimas noticias sobre inflación` - Búsqueda web
- `@Jarvis cuánto llevo gastado en Women` - Consulta con datos reales

#### ⚙️ Control del Bot
- `@Jarvis dormir 8` - Silencia notificaciones por 8 horas
- `@Jarvis pausar 2` - Pausa notificaciones por 2 horas
- `@Jarvis voz` - Activa/desactiva modo TTS

---

## 📨 Ejemplos de Mensajes

### Ejemplo 1: Saludo con Balance

```
Usuario: @Jarvis hola

JARVIS: Sistemas activos. Balance actual: $806,199. Sin tareas críticas pendientes.
```

### Ejemplo 2: Registro de Gasto (Parser Determinístico)

```
Usuario: @Jarvis gasté 50000 en mercado

JARVIS: ✅ Gasto registrado: $50,000 en Mercado
       Categoría: Alimentacion
       Balance actual: $756,199
```

### Ejemplo 3: Configuración de Presupuesto

```
Usuario: @Jarvis presupuesto Women 300000

JARVIS: ✅ Presupuesto establecido: Women = $300,000
```

### Ejemplo 4: Carga Masiva

```
Usuario: @Jarvis Configura y carga masivamente mis datos financieros de agosto.

Presupuestos:
- Deudas: 200000
- Alimentacion: 150000
- Women: 300000
- Moto: 100000

Transacciones:
- tipo: ingreso, monto: 806199.03, categoria: Salario, descripcion: Salario mensual
- tipo: gasto, monto: 332540, categoria: Women, descripcion: Gastos categoría Women
- tipo: gasto, monto: 205000, categoria: Deudas, descripcion: Pagos de deudas

JARVIS: 🤖 [CONFIGURACIÓN MASIVA CARGADA]
       ✅ Base de datos reestructurada con éxito.
       7 presupuestos y 9 transacciones cargadas.
```

### Ejemplo 5: Crear Tarea

```
Usuario: @Jarvis tarea llamar al médico mañana Alta

JARVIS: ✅ Tarea creada: "Llamar al médico"
       Prioridad: Alta
       Fecha límite: 2026-09-02
```

### Ejemplo 6: Análisis de Inversión

```
Usuario: !inversion AAPL

JARVIS: 🍎 ANÁLISIS DE AAPL
       Precio actual: $189.50 (+2.3%)
       RSI: 65.4 (neutral-alcista)
       Recomendación: COMPRAR
       Análisis: Momentum positivo con soporte en $185...
```

### Ejemplo 7: Estado del Sistema

```
Usuario: !estado

JARVIS: 🤖 ESTADO DEL SISTEMA

✅ Bot: Activo y conectado
✅ Firebase: Conectado
🔑 API Keys Gemini: Usando 1/5
📊 Datos personales:
   • 9 transacciones
   • 7 presupuestos
   • 3 tareas pendientes
🔔 Notificaciones: Activas
🔇 Modo voz: Desactivado
```

### Ejemplo 8: Estado de Presupuestos

```
Usuario: !presupuestos

JARVIS: 🎯 ESTADO DE PRESUPUESTOS

✅ Deudas OK
   ████░░░░░░ 25%
   Gastado: $50,000 / $200,000
   Restante: $150,000

🟢 Alimentacion OK
   █████████░ 92%
   Gastado: $138,000 / $150,000
   Restante: $12,000

⚠️ Women ADVERTENCIA
   ████████░░ 80%
   Gastado: $240,000 / $300,000
   Restante: $60,000
```

### Ejemplo 9: Búsqueda por Categoría

```
Usuario: !buscar Women

JARVIS: 🔍 RESULTADOS PARA 'Women' (3 transacciones)

💸 Total gastos: $332,540
💰 Total ingresos: $0

Detalle:
🔴 -$332,540 en Women - Gastos categoría Women
🔴 -$80,000 en Women - Pago mensual
🔴 -$50,000 en Women - Extraordinario
```

### Ejemplo 10: Resumen Diario Automático

```
🤖 [JARVIS - Resumen Diario]
📅 Martes 1 de septiembre, 2026 - 08:00 AM

💰 BALANCE GENERAL
• Ingresos: +$806,199
• Gastos: -$936,440
• Neto: -$130,240

🎯 PRESUPUESTOS
✅ Deudas: ██░░░░░░░░ 20% ($41,000/$200,000)
🔴 Alimentacion: ██████████ 93% ($140,000/$150,000)
✅ Women: ██░░░░░░░░ 30% ($90,000/$300,000)
...

📋 TAREAS PENDIENTES (3)
🔴 Llamar al banco (Vence: 2026-09-03)
🟡 Comprar mercado (Vence: 2026-09-04)
🟢 Regar plantas (Vence: 2026-09-08)

_Sistemas operativos. JARVIS a la espera de instrucciones._
```

---

## 🌐 Dashboard Web

Accede a `https://jarvis-h20g.onrender.com/` (en producción) o `http://localhost:10000/` (local) para ver:

- **Balance neto** con ingresos vs gastos visualizados
- **Presupuestos por categoría** con barras de progreso
- **Colores según estado**:
  - 🟢 Verde (<80% usado)
  - 🟠 Naranja (80-90% usado - advertencia)
  - 🔴 Rojo (>90% usado - crítico)
- **Lista de tareas pendientes** organizada por prioridad
- **Historial reciente de transacciones**

---

## 🔌 API REST

### Endpoints Disponibles

| Método | Endpoint                   | Descripción                         |
| ------ | -------------------------- | ----------------------------------- |
| `GET`  | `/`                        | Dashboard HTML (soporta HEAD)       |
| `GET`  | `/dashboard`               | Dashboard HTML (soporta HEAD)       |
| `POST` | `/api/comando`             | Procesa comando de texto natural    |
| `POST` | `/api/recibo`              | Sube imagen de recibo para procesar |
| `GET`  | `/api/cron/daily-summary`  | Ejecuta resumen diario a Discord    |
| `GET`  | `/api/cron/weekly-summary` | Ejecuta resumen semanal a Discord   |
| `GET`  | `/api/cron/alertas`        | Verifica y envía alertas proactivas |

### Ejemplos de Uso

#### POST /api/comando

```bash
curl -X POST "https://jarvis-h20g.onrender.com/api/comando" \
  -H "Content-Type: application/json" \
  -d '{
    "texto": "gasto 50000 en mercado",
    "usuario_id": "iphone_user"
  }'
```

**Respuesta:**
```json
{
  "status": "ok",
  "respuesta": "✅ Gasto registrado: $50,000 en Mercado"
}
```

#### POST /api/recibo

```bash
curl -X POST "https://jarvis-h20g.onrender.com/api/recibo" \
  -F "file=@recibo.jpg" \
  -F "usuario_id=iphone_user"
```

**Respuesta:**
```json
{
  "status": "ok",
  "resultado": "Recibo procesado: $45,000 en Supermercado XYZ"
}
```

#### GET /api/cron/daily-summary

```bash
curl "https://jarvis-h20g.onrender.com/api/cron/daily-summary"
```

**Respuesta:**
```json
{
  "status": "ok",
  "message": "Resumen enviado"
}
```

---

## ⏰ Automatización (Cron Jobs)

JARVIS usa **GitHub Actions** como cron (alternativa gratuita a Render Cron Job).

### 📅 Resumen Diario

| Aspecto        | Detalle                                                                    |
| -------------- | -------------------------------------------------------------------------- |
| **Frecuencia** | Cada 30 minutos entre 7am-12pm y 7pm-12am (hora Colombia UTC-5)            |
| **Acción**     | Despierta Render + llama a `/api/cron/daily-summary` y `/api/cron/alertas` |
| **Workflow**   | `.github/workflows/daily-summary.yml`                                      |
| **Contenido**  | Balance general, presupuestos, tareas pendientes                           |

**Cron expression**: `0,30 12-17,0-4 * * *`
- UTC 12:00-17:00 = COL 7:00am-12:00pm
- UTC 00:00-04:00 = COL 7:00pm-12:00am

### 📊 Resumen Semanal

| Aspecto        | Detalle                                              |
| -------------- | ---------------------------------------------------- |
| **Frecuencia** | Domingos 8am hora Colombia (UTC 13:00)               |
| **Acción**     | Llama a `/api/cron/weekly-summary`                   |
| **Workflow**   | `.github/workflows/weekly-summary.yml`               |
| **Contenido**  | Variación vs semana anterior, top categorías, tareas |

**Cron expression**: `0 13 * * 0`

### 🚨 Alertas Proactivas

| Aspecto        | Detalle                                              |
| -------------- | ---------------------------------------------------- |
| **Frecuencia** | Cada 30 minutos (junto con daily summary)            |
| **Detecta**    | Presupuestos >80%, tareas vencidas, gastos anormales |
| **Endpoint**   | `/api/cron/alertas`                                  |

### Diagrama de Automatización

```
┌──────────────────────────────────────────────────────────┐
│                   GITHUB ACTIONS                          │
│                                                           │
│  ┌─────────────────────────────────────────────────┐     │
│  │ daily-summary.yml                               │     │
│  │                                                  │     │
│  │  ⏰ Cada 30 min (7am-12pm, 7pm-12am COL)        │     │
│  │  1. Despertar Render (ping HEAD)                │     │
│  │  2. Llamar /api/cron/daily-summary              │     │
│  │  3. Llamar /api/cron/alertas                    │     │
│  └─────────────────────────────────────────────────┘     │
│                                                           │
│  ┌─────────────────────────────────────────────────┐     │
│  │ weekly-summary.yml                              │     │
│  │                                                  │     │
│  │  ⏰ Domingo 8am COL                             │     │
│  │  1. Despertar Render                            │     │
│  │  2. Llamar /api/cron/weekly-summary             │     │
│  └─────────────────────────────────────────────────┘     │
└─────────────────────────┬────────────────────────────────┘
                          │
                          │ HTTPS
                          ▼
                ┌─────────────────────┐
                │   RENDER            │
                │   Web Service       │
                │   server.py         │
                └──────────┬──────────┘
                           │
                           │ Lee Firebase
                           ▼
                ┌─────────────────────┐
                │   FIREBASE          │
                │   Firestore         │
                └──────────┬──────────┘
                           │
                           │ Webhook POST
                           ▼
                ┌─────────────────────┐
                │   DISCORD           │
                │   📢 Mensaje        │
                └─────────────────────┘
```

---

## 🚨 Alertas Proactivas

### Tipos de Alertas

#### 1. 💰 Alertas de Presupuesto

**Detección automática cada 30 minutos:**

```python
if porcentaje >= 90%:
    nivel = "CRITICAL"  # 🔴
elif porcentaje >= 80%:
    nivel = "WARNING"   # 🟠
else:
    estado = "OK"        # 🟢
```

**Ejemplo de mensaje en Discord:**
```
🚨 ALERTAS JARVIS

🚨 ALERTAS DE PRESUPUESTO
🔴 Alimentacion (CRÍTICO)
   Gastado: $140,000 / $150,000 (93%)
   Restante: $10,000
⚠️ Women (ADVERTENCIA)
   Gastado: $250,000 / $300,000 (83%)
   Restante: $50,000
```

#### 2. ⏰ Alertas de Tareas Vencidas

**Detección automática cada 30 minutos:**

- **Tareas vencidas**: Lista con días de retraso
- **Tareas próximas (≤2 días)**: Lista con días restantes

**Ejemplo:**
```
⏰ TAREAS VENCIDAS
🔴 Llamar al banco - Vencida hace 2 día(s)
   📅 Fecha límite: 2026-08-30

📅 TAREAS PRÓXIMAS A VENCER
🟡 Comprar mercado - Vence en 1 día(s)
🟡 Regar plantas - Vence hoy
```

#### 3. 💸 Gastos Anormales

**Algoritmo de detección:**

```python
umbral = promedio_historico * 2.0
if gasto_actual > umbral:
    es_anormal = True
```

**Ejemplo:**
```
💸 GASTOS ANORMALES DETECTADOS
⚠️ Women
   Último: $150,000 (promedio: $50,000)
   Multiplicador: 3.0x del promedio
```

### Configuración

Todas las alertas se ejecutan vía:
- **Endpoint**: `GET /api/cron/alertas`
- **Workflow GitHub Actions**: `daily-summary.yml`
- **Frecuencia**: Cada 30 minutos

---

## 🔧 Optimización y Arquitectura

### Flujo de Procesamiento

```
1. ENTRADA (Texto, Imagen, Audio) → Discord/Web/API
       ↓
2. PRE-PROCESAMIENTO → Parsers determinísticos (90% de los casos)
       ↓
3. FALLBACK A GEMINI → Solo para intenciones complejas
       ↓
4. FUNDAMENTACIÓN → Inyección de datos reales de Firebase
       ↓
5. EJECUCIÓN → Operaciones en Firebase
       ↓
6. RESPUESTA → Formateo y envío al usuario
```

### Parsers Determinísticos Implementados

| Parser                          | Función                    | Ejemplo                    |
| ------------------------------- | -------------------------- | -------------------------- |
| `_parse_tarea()`                | Detecta creación de tareas | "tarea llamar al médico"   |
| `_parse_transaccion()`          | Detecta gastos/ingresos    | "gasté 50000 en mercado"   |
| `_parse_presupuesto()`          | Detecta configuración      | "presupuesto Women 300000" |
| `_parse_completar_tarea()`      | Detecta completado         | "hecho llamar al médico"   |
| `_parse_configuracion_masiva()` | Carga masiva               | "Presupuestos: X: Y..."    |

### Optimización de Costos de API

- ✅ **90% de las intenciones** se resuelven sin llamar a Gemini
- ✅ **Historial limitado a 10 movimientos** (reduce tokens ~80%)
- ✅ **Cache de contexto financiero** (30 segundos TTL)
- ✅ **Cooldown anti-spam** (3 segundos por usuario)
- ✅ **Rotación automática de 5 API Keys**

### Manejo de Errores 429

**Problema común en servicios de IA**: cuando excedes el límite de requests por minuto (RPM) o la cuota diaria, recibes error 429.

**Solución implementada:**

1. **Rate Limiter Local** - Previene errores antes de que ocurran:
   - Mantiene tracking de las últimas llamadas
   - Espera automáticamente si ya hiciste 14 requests en los últimos 60 segundos
   - Respeta el límite de RPM (15/min en gemini-3.1-flash-lite)

2. **Rotación de Keys con Backoff** - Cuando el rate limiter no es suficiente:
   - Extrae automáticamente el `retryDelay` del error
   - Espera antes de rotar a la siguiente key
   - Diferencia entre RPM (recuperable en ~60s) vs cuota diaria (medianoche)

3. **Mensajes Contextuales** - Informa al usuario claramente:
   - Si es RPM: "Límite de velocidad (RPM). Espera X segundos"
   - Si es cuota diaria: "Cuota diaria agotada. Se reinicia a medianoche (hora Colombia)"

```python
def _gemini_call_with_fallback(callable):
    # Rate limiter local: espera si estamos cerca del RPM
    _esperar_por_rpm()

    retries = len(_API_KEYS)
    for _ in range(retries):
        try:
            return callable(_get_current_client())
        except APIError as e:
            if e.code == 429:
                retry_delay = extraer_retry_delay(e)
                if retry_delay and retry_delay <= 120:
                    time.sleep(min(retry_delay, 5))
                _rotate_key()  # Cambia a la siguiente key
                continue
            raise
```

**Ventajas:**
- Previene el 90% de los errores 429 antes de que ocurran
- Detección precisa entre límites por minuto y diarios
- Extracción automática de `retryDelay`
- Mensajes contextuales al usuario
- Rotación transparente (sin interrumpir la conversación)

### Rotación de API Keys

```python
# Configuración
GEMINI_API_KEYS=key1,key2,key3,key4,key5

# Algoritmo
_key_index = 0
def _rotate_key():
    _key_index = (_key_index + 1) % len(_API_KEYS)
```

**Ventajas:**
- Hasta 5 keys simultáneas
- Round-robin automático ante 429
- Mayor disponibilidad
- Sin pérdida de conversación

---

## 🔑 Variables de Entorno

### Archivo `.env`

```bash
# ===== GEMINI (Requerido) =====
# Opción 1: Múltiples keys (recomendado para rotación)
GEMINI_API_KEYS=key1,key2,key3,key4,key5

# Opción 2: Una sola key
# GEMINI_API_KEY=tu_api_key

# Modelo (opcional)
GEMINI_MODEL=gemini-3.1-flash-lite

# ===== DISCORD (Requerido) =====
DISCORD_TOKEN=tu_token_de_bot
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# ===== FIREBASE (Requerido) =====
# Opción 1: JSON completo en variable
FIREBASE_CREDENTIALS={"type":"service_account",...}

# Opción 2: Path al archivo
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json

# ===== RENDER (Automático) =====
# PORT=10000  # Se configura automáticamente en Render
```

### Configuración en Render

Para cada servicio (Web + Background Worker), ve a **Environment** y agrega las mismas variables.

---

## 🔍 Troubleshooting

### Problema: Bot no responde a menciones

**Síntoma:** `@Jarvis hola` no genera respuesta

**Solución:**
1. Verifica que el **Background Worker** esté corriendo en Render
2. Revisa los logs del worker en Render Dashboard
3. Confirma que `ALLOWED_ROLE_IDS` en `jarvis_discord.py` tenga el ID correcto:
   ```python
   ALLOWED_ROLE_IDS = [1537704466407497738]  # ID del rol "App"
   ```

### Problema: UptimeRobot muestra error 405

**Síntoma:** UptimeRobot reporta "down" con HTTP 405

**Solución:**
- Asegúrate de que `server.py` tenga los decoradores HEAD:
  ```python
  @app.get("/")
  @app.head("/")
  def render_dashboard():
      ...
  ```
- Haz push a GitHub para redeploy

### Problema: Render se duerme cada 15 minutos

**Síntoma:** El dashboard/API no responde tras inactividad

**Solución:**
- Configura **UptimeRobot** con ping cada 5-10 minutos
- URL: `https://jarvis-h20g.onrender.com/`

### Problema: Error 429 en todas las API Keys

**Síntoma:** "All Gemini API keys exhausted due to 429"

**Solución:**
1. Verifica que las 5 keys sean válidas: ejecuta `test_all_keys.py`
2. Espera al reset diario de cuota (medianoche COL)
3. Agrega más keys al `.env` separadas por comas

### Problema: GitHub Actions no se ejecuta

**Síntoma:** El workflow `daily-summary.yml` no corre

**Solución:**
1. Ve a GitHub → Actions → selecciona el workflow
2. Verifica que esté habilitado (no en estado "Disabled")
3. Puedes ejecutarlo manualmente con "Run workflow"
4. Revisa la pestaña "Runs" para ver logs

### Problema: Discord rate limit (429)

**Síntoma:** Bot desconectado tras reinicios frecuentes

**Solución:**
- El bot está ahora en **Background Worker** (no se reinicia)
- Si persiste, añade `reconnect` con backoff exponencial

---

## 📈 Historial de Cambios

### Nuevos Comandos de Estadísticas (Septiembre 2026)
- ✅ `!mes [mes/año]` - Resumen de un mes específico (ej: !mes agosto)
- ✅ `!stats` - Estadísticas: promedios, top categorías, proyecciones
- ✅ `!top [N]` - Top N categorías con más gastos (medallas)
- ✅ `!borrar confirmar` - Borrar todos los datos con confirmación
- ✅ Comando soporta `!mes actual`, `!mes anterior`, `!mes 08 2026`, `!mes agosto`
- ✅ Cálculo automático de promedios diarios y proyecciones mensuales/anuales
- ✅ Bug fix: parser de configuración masiva corregido

### Nuevos Comandos Discord (Septiembre 2026)
- ✅ `!presupuestos` - Estado detallado con barras de progreso
- ✅ `!historial [N]` - Últimas N transacciones (default 20)
- ✅ `!buscar <término>` - Búsqueda por categoría o descripción
- ✅ `!estado` - Estado del sistema (API keys, datos, modo)
- ✅ `!ayuda` - Lista completa de comandos disponibles
- ✅ Bug fix: `!finanzas` ahora formatea correctamente los movimientos
- ✅ Mensaje de error 429 mejorado con instrucciones claras

### Fase 3 - Alertas Proactivas (Septiembre 2026)
- ✅ Nuevo módulo `modules/alertas.py` con detección de:
  - Presupuestos críticos (>90%) y warning (>80%)
  - Tareas vencidas y próximas a vencer
  - Gastos anormales (>2x del promedio histórico)
- ✅ Resumen semanal cada domingo vía Discord webhook
- ✅ Nuevos endpoints `/api/cron/weekly-summary` y `/api/cron/alertas`
- ✅ Workflow de GitHub Actions `weekly-summary.yml`

### Separación Bot/Web Service (Septiembre 2026)
- ✅ Render con **dos servicios**:
  - Web Service (`server.py`): Dashboard + API
  - Background Worker (`jarvis_discord.py`): Bot Discord 24/7
- ✅ Solución al error 405 Method Not Allowed (soporte HEAD)
- ✅ UptimeRobot mantiene el Web Service activo
- ✅ El bot corre 24/7 sin depender de PC local

### Cron con GitHub Actions (Septiembre 2026)
- ✅ Workflow `daily-summary.yml` ejecuta resumen cada 30 min
- ✅ Reemplaza Render Cron Job (plan gratuito)
- ✅ Activa automáticamente vía push a `main`

### Parsers Determinísticos (Agosto 2026)
- ✅ Implementados parsers para 90% de las intenciones comunes
- ✅ Elimina la mayoría de llamadas a Gemini
- ✅ Reduce costos y latencia significativamente

### Rotación de API Keys (Agosto 2026)
- ✅ Soporte para 5 keys simultáneas
- ✅ Rotación automática ante error 429
- ✅ Variables de entorno: `GEMINI_API_KEYS` (csv) o `GEMINI_API_KEY` (single)

### Limpieza de Menciones (Agosto 2026)
- ✅ Soporte para menciones de rol `<@&ID>` en Discord
- ✅ Regex limpia menciones de usuario y rol del texto
- ✅ Variable `ALLOWED_ROLE_IDS` en `jarvis_discord.py`

### Optimización de Consumo (Agosto 2026)
- ✅ Historial limitado a últimos 10 movimientos
- ✅ Cache de contexto financiero (TTL 30s)
- ✅ Cooldown anti-spam (3s)
- ✅ Solo TTS bajo demanda explícita

---

## 🚀 Roadmap

### Próximas Mejoras Planeadas

- [ ] **Reportes mensuales automáticos** (gráficos en PDF)
- [ ] **Categorización automática** de gastos con ML
- [ ] **Predicción de gastos** basada en histórico
- [ ] **Integración con WhatsApp** vía Twilio
- [ ] **App móvil nativa** (React Native o Flutter)
- [ ] **Modo multi-usuario** (soporte para varios usuarios)
- [ ] **Integración con bancos** (Plaid/Tink)
- [ ] **Sistema de metas** financieras
- [ ] **Análisis de tendencias** con visualización
- [ ] **Confirmación para comandos destructivos** (`!borrar todo`)
- [ ] **Filtros por mes** (`!mes agosto`)
- [ ] **Recordatorios programados** (`!recordar 2026-09-15 "..."`)
- [ ] **Tags/categorías personalizadas**
- [ ] **Tests automatizados** completos
- [ ] **Dashboard con gráficos** (Chart.js)

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor:

1. Haz fork del repositorio
2. Crea una rama para tu feature: `git checkout -b feature/nueva-funcionalidad`
3. Haz commit de tus cambios: `git commit -m 'Agregar nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

### Áreas para Contribuir

- 🆕 **Nuevos comandos de Discord** (`!comando` con prefijo)
- 📊 **Mejoras al dashboard web** (gráficos, visualizaciones)
- ⚡ **Optimizaciones adicionales de Firestore**
- 🧪 **Tests unitarios y de integración**
- 🤖 **Nuevos parsers determinísticos**
- 📱 **Integración con iPhone Shortcuts**
- 🔌 **Conectores con servicios externos** (Google Calendar, Notion, etc.)

---

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT**. Ver [LICENSE](LICENSE) para más detalles.

---

## ☎️ Soporte

Para preguntas y soporte:

- 🐛 **Issues de GitHub**: [github.com/estudiopoolr-a11y/jarvis/issues](https://github.com/estudiopoolr-a11y/jarvis/issues)
- 📖 **Documentación**: Este README y docstrings en el código
- 💬 **Discord**: Contacta al autor

---

## 🙏 Agradecimientos

- **Google Gemini** - Por la API de IA generativa
- **Discord.py** - Librería de Discord para Python
- **FastAPI** - Framework web moderno
- **Firebase** - Base de datos en tiempo real
- **Render** - Hosting 24/7 con plan gratuito
- **GitHub Actions** - CI/CD y cron gratuito
- **UptimeRobot** - Monitoring de servicios

---

*Hecho con ❤️ por tu asistente personal ejecutivo JARVIS*

> **"Sistemas en línea. A la espera de instrucciones."**
<!-- cSpell:enable -->
