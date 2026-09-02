# 🤖 Proyecto JARVIS - Asistente Personal Inteligente

Asistente personal integrado con inteligencia artificial (Gemini) y automatización para la gestión de tareas, finanzas y notas de voz. Diseñado para ser tu asistente ejecutivo personal, frío, analítico y eficiente. Desplegado 24/7 en Render con bot de Discord persistente.

## ✨ Características Principales

### 💰 Gestión Financiera Inteligente
- **Registro automático de ingresos y gastos** a través de lenguaje natural
- **Carga masiva de datos** mediante prompt estructurado (presupuestos + transacciones en un solo mensaje)
- **Presupuestos por categoría** con alertas proactivas cuando se acercan al límite (80% warning, 90% critical)
- **Balance financiero en tiempo real** con ingresos, gastos y neto
- **Historial de transacciones** almacenado de forma segura en Firebase
- **Procesamiento de recibos** mediante IA (extrae monto, establecimiento y categoría)
- **Detección de gastos anormales** (gastos que superan 2x del promedio histórico)

### 📋 Gestión de Tareas
- **Creación de tareas** con prioridad y fecha límite
- **Lista de pendientes** siempre actualizada
- **Marcado de completado** mediante búsqueda inteligente
- **Detección de tareas vencidas** y próximas a vencer
- **Recordatorios contextuales** basados en tu carga de trabajo

### 🧠 Inteligencia Artificial Avanzada
- **Análisis de inversiones** combinando datos en vivo de Yahoo Finanzas y búsqueda web
- **Comprensión de lenguaje natural** para intenciones complejas
- **Fundamentación en datos reales**: la IA responde ÚNICAMENTE con información de tu base de datos, evitando alucinaciones financieras
- **Modo voz** con respuesta de audio mediante Google Text-to-Speech
- **Rotación automática de hasta 5 API Keys de Gemini** (rotación round-robin ante 429)

### 🖥️ Múltiples Interfaces
- **Discord Bot**: Interactúa mediante comandos, menciones de usuario y menciones de rol (`<@&ID>`)
- **Dashboard Web**: Visualiza tus finanzas, presupuestos y tareas en tiempo real
- **API REST**: Endpoints para integraciones externas y automatizaciones (cron)
- **Procesamiento de multimedia**: Imágenes (recibos/facturas) y audio (notas de voz)
- **Notificaciones vía Webhook de Discord**: Resúmenes diarios y semanales automáticos

### 🚨 Alertas Proactivas
- **Presupuestos críticos** (>90% del límite)
- **Tareas vencidas** con días de retraso
- **Tareas próximas a vencer** (≤2 días)
- **Gastos anormales** (>2x del promedio histórico)
- **Resumen semanal** cada domingo con variación vs semana anterior

### 🔐 Privacidad y Seguridad
- **Datos almacenados exclusivamente en tu proyecto Firebase**
- **Ninguna información financiera se envía a terceros** excepto para el procesamiento necesario con Gemini
- **Variables de entorno** para credenciales sensibles
- **Safety settings configuradas** para evitar contenido inapropiado

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

## 🚀 Inicio Rápido

### Prerrequisitos
- Python 3.11+
- Cuenta de [Google Cloud](https://console.cloud.google.com/) con API de Gemini habilitada
- Proyecto de [Firebase](https://firebase.google.com/) con Firestore API habilitada
- Bot de [Discord](https://discord.com/developers/applications) con token y Message Content Intent
- Webhook de Discord para notificaciones
- **Una o más API Keys de Gemini** (recomendado: 3-5 keys para rotación)

### Configuración Local

1. **Clona el repositorio**:
   ```bash
   git clone https://github.com/tu-usuario/jarvis.git
   cd jarvis
   ```

2. **Instala dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configura variables de entorno** en `.env`:
   ```bash
   # Gemini API Keys (rotación automática)
   GEMINI_API_KEYS=key1,key2,key3,key4,key5
   
   # Discord
   DISCORD_TOKEN=tu_token_de_bot_de_discord
   DISCORD_WEBHOOK_URL=tu_webhook_de_discord
   
   # Firebase (alternativa al archivo JSON)
   FIREBASE_CREDENTIALS=contenido_json_completo
   ```

4. **Coloca credenciales de Firebase**:
   - Descarga el JSON desde Firebase Console → Configuración → Cuentas de servicio
   - Renómbralo a `serviceAccountKey.json` y colócalo en la raíz

5. **Inicia el sistema** (ahora en 2 procesos separados):
   ```bash
   # Solo el bot Discord (recomendado)
   python jarvis_discord.py
   
   # Solo el servidor web (dashboard + API)
   python server.py
   ```

## ☁️ Despliegue en Render (24/7)

JARVIS está configurado para correr **24/7 en Render** usando dos servicios:

### 🟦 Web Service (Dashboard + API)
- **Tipo**: Web Service
- **Comando de inicio**: `python server.py`
- **Puerto**: 10000
- **Duerme tras 15 min de inactividad** (UptimeRobot lo mantiene activo)
- **URL**: `https://jarvis-h20g.onrender.com`

### 🟨 Background Worker (Bot Discord)
- **Tipo**: Background Worker
- **Comando de inicio**: `python jarvis_discord.py`
- **NO se duerme** - corre 24/7
- **Variables de entorno**: Mismas que el Web Service

### Pasos para desplegar
1. Conecta tu repositorio en [render.com](https://render.com)
2. Crea el **Web Service** apuntando a `server.py`
3. Crea el **Background Worker** apuntando a `jarvis_discord.py`
4. Copia las variables de entorno en ambos servicios
5. Configura [UptimeRobot](https://uptimerobot.com) para hacer ping cada 5-10 min al Web Service

### ⚠️ Error 405 Method Not Allowed
Si usas UptimeRobot, asegúrate de que el Web Service soporte **HEAD requests** (UptimeRobot usa HEAD por defecto para ahorrar ancho de banda). El servidor ya incluye `@app.head("/")` y `@app.head("/dashboard")` para compatibilidad.

## 💬 Uso en Discord

Una vez que el bot esté en línea, mencionalo con `@Jarvis` o al rol configurado (`<@&ID>`):

### Comandos Financieros
- `@Jarvis gasto 50 en supermercado` - Registra un gasto
- `@Jarvis ingreso 1000 trabajo freelance` - Registra un ingreso
- `@Jarvis presupuesto Alimentación 15000` - Establece presupuesto para categoría
- `@Jarvis finanzas` - Muestra balance completo y historial

### Carga Masiva de Datos
Envía un mensaje estructurado con presupuestos y transacciones en un solo prompt:

```
@Jarvis Configura y carga masivamente mis datos financieros de agosto.

Presupuestos:
- Deudas: 200000
- Alimentacion: 150000
- Women: 300000
- Moto: 100000

Transacciones:
- tipo: ingreso, monto: 806199.03, categoria: Salario, descripcion: Salario mensual
- tipo: gasto, monto: 332540, categoria: Women, descripcion: Gastos categoría Women
- tipo: gasto, monto: 205000, categoria: Deudas, descripcion: Pagos de deudas
```

### Gestión de Tareas
- `@Jarvis tarea llamar al médico mañana Alta` - Crea tarea con prioridad
- `@Jarvis tareas` - Lista tareas pendientes
- `@Jarvis hecho llamar al médico` - Marca tarea como completada
- `@Jarvis borra todos los datos` - Reinicia la base de datos

### Comandos Slash
- `!finanzas` - Balance completo
- `!tareas` - Tareas pendientes
- `!hecho "descripción"` - Marca tarea completada
- `!dormir 8` - Silencia notificaciones por 8 horas
- `!pausar 2` - Pausa notificaciones por 2 horas
- `!voz` - Activa/desactiva respuestas de audio TTS
- `!inversion AAPL` - Análisis de acción

### Análisis y Consultas
- `@Jarvis inversión AAPL` - Analiza acción de Apple
- `@Jarvis buscar últimas noticias sobre inflación` - Búsqueda web con contexto financiero

## 🌐 API REST

### Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET`  | `/` | Dashboard HTML (soporta HEAD) |
| `GET`  | `/dashboard` | Dashboard HTML (soporta HEAD) |
| `POST` | `/api/comando` | Procesa comando de texto natural |
| `POST` | `/api/recibo` | Sube imagen de recibo para procesar |
| `GET`  | `/api/cron/daily-summary` | Ejecuta resumen diario a Discord |
| `GET`  | `/api/cron/weekly-summary` | Ejecuta resumen semanal a Discord |
| `GET`  | `/api/cron/alertas` | Verifica y envía alertas proactivas |

### Ejemplo de uso
```bash
# Comando
curl -X POST "https://jarvis-h20g.onrender.com/api/comando" \
  -H "Content-Type: application/json" \
  -d '{"texto": "gasto 50000 en mercado", "usuario_id": "iphone_user"}'

# Recibo
curl -X POST "https://jarvis-h20g.onrender.com/api/recibo" \
  -F "file=@recibo.jpg" \
  -F "usuario_id=iphone_user"
```

## ⏰ Automatización (Cron Jobs)

JARVIS usa **GitHub Actions** como cron (alternativa gratuita a Render Cron Job).

### 📅 Resumen Diario
- **Frecuencia**: Cada 30 minutos entre 7am-12pm y 7pm-12am (hora Colombia UTC-5)
- **Acción**: Despierta Render y llama a `/api/cron/daily-summary` y `/api/cron/alertas`
- **Workflow**: `.github/workflows/daily-summary.yml`
- **Contenido del resumen**:
  - Balance general (ingresos vs gastos vs neto)
  - Estado de presupuestos (barras de progreso)
  - Tareas pendientes (top 5)

### 📊 Resumen Semanal
- **Frecuencia**: Domingos 8am hora Colombia
- **Acción**: Llama a `/api/cron/weekly-summary`
- **Workflow**: `.github/workflows/weekly-summary.yml`
- **Contenido del resumen**:
  - Ingresos/gastos de la semana vs semana anterior
  - Top 5 categorías con más gastos
  - Tareas pendientes

### 🚨 Alertas Proactivas
- **Frecuencia**: Cada 30 minutos (junto con daily summary)
- **Detecta**:
  - Presupuestos >80% (warning) y >90% (critical)
  - Tareas vencidas
  - Tareas próximas a vencer (≤2 días)
  - Gastos anormales (>2x del promedio)

### Variables de Entorno Requeridas en Render
```
GEMINI_API_KEYS=key1,key2,key3
DISCORD_TOKEN=tu_token
DISCORD_WEBHOOK_URL=tu_webhook
FIREBASE_CREDENTIALS=contenido_json
PORT=10000
```

## 🔧 Optimización y Arquitectura

### Flujo de Procesamiento
1. **Entrada** (Texto, Imagen, Audio) → Discord/Web/API
2. **Pre-procesamiento** → Parsers determinísticos (90% de los casos evitan Gemini)
3. **Fallback a Gemini** → Solo para intenciones complejas
4. **Fundamentación** → Inyección de datos reales de Firebase para evitar alucinaciones
5. **Ejecución** → Operaciones en Firebase (guardar transacción, crear tarea, etc.)
6. **Respuesta** → Formateo y envío al usuario

### Optimización de Costos de API
- **Parsers determinísticos** para comandos comunes (90% de las intenciones se resuelven sin Gemini)
  - `_parse_tarea()`: Crea tareas
  - `_parse_transaccion()`: Registra gastos/ingresos
  - `_parse_presupuesto()`: Configura presupuestos
  - `_parse_completar_tarea()`: Marca tareas como hechas
  - `_parse_configuracion_masiva()`: Carga masiva de presupuestos + transacciones
- **Historial limitado a 10 movimientos** en cada inyección de contexto (reduce tokens ~80%)
- **Cache de contexto financiero** (30 segundos) para evitar consultas redundantes a Firebase
- **Cooldown anti-spam** (3 segundos) para evitar mensajes duplicados
- **Rotación automática de API Keys**: si una key obtiene 429, cambia instantáneamente a otra

### Manejo de Errores 429
- Detección precisa entre límites por minuto (retryable) y límites diarios (espera hasta mañana)
- Extracción automática de `retryDelay` de los detalles de error de Gemini
- Mensajes de error contextuales y útiles para el usuario
- **Rotación transparente** entre 5 keys sin interrumpir la conversación

### Rotación de API Keys
- Soporte para múltiples API Keys mediante `GEMINI_API_KEYS` (lista separada por comas)
- Algoritmo round-robin que cambia a la siguiente key al detectar error 429
- Transparente para el usuario: no se pierde la conversación ni se requiere nueva solicitud
- Mayor disponibilidad y tolerancia a fallos de cuota o límites de tasa

## 📈 Historial de Cambios Recientes

### Fase 3 - Alertas Proactivas (Septiembre 2026)
- Nuevo módulo `modules/alertas.py` con detección de:
  - Presupuestos críticos (>80% warning, >90% critical)
  - Tareas vencidas y próximas a vencer
  - Gastos anormales (>2x del promedio histórico)
- Resumen semanal cada domingo vía Discord webhook
- Nuevos endpoints `/api/cron/weekly-summary` y `/api/cron/alertas`
- Workflow de GitHub Actions `weekly-summary.yml`

### Separación Bot/Web Service (Septiembre 2026)
- Render con **dos servicios**:
  - Web Service (`server.py`): Dashboard + API
  - Background Worker (`jarvis_discord.py`): Bot Discord 24/7
- Solución al error 405 Method Not Allowed (soporte HEAD)
- UptimeRobot mantiene el Web Service activo
- El bot corre 24/7 sin depender de PC local

### Cron con GitHub Actions (Septiembre 2026)
- Workflow `daily-summary.yml` ejecuta resumen cada 30 min
- Reemplaza Render Cron Job (plan gratuito)
- Activa automáticamente vía push a `main`

### Parsers Determinísticos (Agosto 2026)
- Implementados parsers para 90% de las intenciones comunes
- Elimina la mayoría de llamadas a Gemini
- Reduce costos y latencia

### Rotación de API Keys (Agosto 2026)
- Soporte para 5 keys simultáneas
- Rotación automática ante 429
- Variables de entorno: `GEMINI_API_KEYS` (csv) o `GEMINI_API_KEY` (single)

### Limpieza de Menciones (Agosto 2026)
- Soporte para menciones de rol `<@&ID>` en Discord
- Regex limpia menciones de usuario y rol del texto
- Variable `ALLOWED_ROLE_IDS` en `jarvis_discord.py`

### Optimización de Consumo (Agosto 2026)
- Historial limitado a últimos 10 movimientos
- Cache de contexto financiero (TTL 30s)
- Cooldown anti-spam (3s)
- Solo TTS bajo demanda explícita

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor:
1. Haz fork del repositorio
2. Crea una rama para tu feature
3. Haz commit de tus cambios
4. Abre un Pull Request

### Áreas para Contribuir
- Nuevos comandos de Discord
- Mejoras al dashboard web (gráficos, visualizaciones)
- Optimizaciones adicionales de Firestore
- Tests unitarios y de integración
- Nuevos parsers determinísticos

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

## ☎️ Soporte

Para preguntas y soporte:
- Issues de GitHub
- Documentación en el código (docstrings y comentarios)

---

*Hecho con ❤️ por tu asistente personal ejecutivo JARVIS*
