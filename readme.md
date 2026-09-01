# 🤖 Proyecto JARVIS - Asistente Personal Inteligente

Asistente personal integrado con inteligencia artificial (Gemini) y automatización para la gestión de tareas, finanzas y notas de voz. Diseñado para ser tu asistente ejecutivo personal, frío, analítico y eficiente.

## ✨ Características Principales

### 💰 Gestión Financiera Inteligente
- **Registro automático de ingresos y gastos** a través de lenguaje natural
- **Presupuestos por categoría** con alertas proactivas cuando se superan
- **Balance financiero en tiempo real** con ingresos, gastos y neto
- **Historial de transacciones** almacenado de forma segura en Firebase
- **Procesamiento de recibos** mediante IA (extrae monto, establecimiento y categoría)

### 📋 Gestión de Tareas
- **Creación de tareas** con prioridad y fecha límite
- **Lista de pendientes** siempre actualizada
- **Marcado de completado** mediante búsqueda inteligente
- **Recordatorios contextuales** basados en tu carga de trabajo

### 🧠 Inteligencia Artificial Avanzada
- **Análisis de inversiones** combinando datos en vivo de Yahoo Finanzas y búsqueda web
- **Comprensión de lenguaje natural** para intenciones complejas
- **Fundamentación en datos reales**: la IA responde ÚNICAMENTE con información de tu base de datos, evitando alucinaciones financieras
- **Modo voz** con respuesta de audio mediante Google Text-to-Speech

### 🖥️ Múltiples Interfaces
- **Discord Bot**: Interactúa mediante comandos y menciones
- **Dashboard Web**: Visualiza tus finanzas, presupuestos y tareas en tiempo real
- **API REST**: Endpoints para integraciones externas
- **Procesamiento de multimedia**: Imágenes (recibos/facturas) y audio (notas de voz)

### 🔐 Privacidad y Seguridad
- **Datos almacenados exclusivamente en tu proyecto Firebase**
- **Ninguna información financiera se envía a terceros** excepto para el procesamiento necesario con Gemini
- **Variables de entorno** para credenciales sensibles
- **Safety settings configuradas** para evitar contenido inapropiado

## 📂 Estructura del Proyecto

```
jarvis/
│
├── .env                  # 🔒 Variables de entorno y credenciales (API Key(s))
├── .gitignore
├── iniciar_jarvis.bat    # 🚀 Script de inicio para Windows
├── iniciar_claude.bat    # 🤖 Script para Claude Code integration
├── jarvis_discord.py     # 💬 Bot de Discord principal
├── server.py             # 🌐 Servidor web FastAPI con dashboard
├── readme.md             # 📖 Este archivo
├── requirements.txt      # 📦 Dependencias de Python
├── serviceAccountKey.json # 🔐 Credenciales de Firebase (no subir a git)
│
├── audio_cache/          # 🎵 Carpeta temporal para procesamiento de notas de voz
│
└── modules/              # 🧩 Módulos de lógica separada
    ├── database.py       # 🗃️ Integración con Firebase Firestore
    └── ai_brain.py       # 🧠 Lógica de IA y procesamiento con rotación de API Keys
```

## 🚀 Inicio Rápido

### Prerrequisitos
- Python 3.8+
- Cuenta de [Google Cloud](https://console.cloud.google.com/) con API de Gemini habilitada
- Proyecto de [Firebase](https://firebase.google.com/) con Firestore API habilitada
- Bot de [Discord](https://discord.com/developers/applications) con token y privilegios de mensaje de contenido
- Cuenta de [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech) (opcional, para modo voz)
- **Una o más API Keys de Gemini** (configuradas en tu `.env`)

### Configuración
1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/jarvis.git
   cd jarvis
   ```

2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Configura variables de entorno en `.env`:
   - **Una sola API Key** (modo original):
     ```
     GEMINI_API_KEY=tu_api_key_de_gemini
     DISCORD_TOKEN=tu_token_de_bot_de_discord
     ```
   - **Múltiples API Keys** (rotación automática, recomendado):
     ```
     GEMINI_API_KEYS=key1,key2,key3
     DISCORD_TOKEN=tu_token_de_bot_de_discord
     ```

4. Coloca tu archivo de credenciales de Firebase:
   - Descarga el JSON de servicio desde Firebase Console > Configuración de proyecto > Cuentas de servicio
   - Renómbralo a `serviceAccountKey.json` y colócalo en la raíz del proyecto

5. Inicia el sistema:
   ```bash
   # Servidor web (que también inicia el bot Discord)
   python server.py
   
   # Solo el bot Discord
   python jarvis_discord.py
   ```

## 💬 Uso en Discord

Una vez que el bot esté en línea, mencionalo con `@Jarvis` seguido de tu comando:

### Comandos Financieros
- `@Jarvis gasto 50 en supermercado` - Registra un gasto
- `@Jarvis ingreso 1000 trabajo freelance` - Registra un ingreso
- `@Jarvis presupuesto Alimentación 15000` - Establece presupuesto para categoría
- `@Jarvis finanzas` - Muestra balance completo y historial
- `@Jarvis debo 20000 préstamo` - Registra una deuda como gasto

### Gestión de Tareas
- `@Jarvis tarea llamar al médico mañana Alta` - Crea tarea con prioridad
- `@Jarvis tareas` - Lista tareas pendientes
- `@Jarvis hecho llamar al médico` - Marca tarea como completada
- `@Jarvis borra todos los datos` - Reinicia la base de datos

### Análisis y Consultas
- `@Jarvis inversión AAPL` - Analiza acción de Apple
- `@Jarvis buscar últimas noticias sobre inflación` - Búsqueda web con contexto financiero
- `@Jarvis voz` - Alterna modo de respuesta de audio

### Comandos de Control
- `@Jarvis dormir 8` - Silencia notificaciones por 8 horas
- `@Jarvis pausar 2` - Pausa notificaciones por 2 horas

## 🌐 Dashboard Web

Accede a `http://localhost:10000` para ver:
- **Balance neto** con ingresos vs gastos visualizados
- **Presupuestos por categoría** con barras de progreso y alertas de exceso
- **Lista de tareas pendientes** organizada por prioridad
- **Historial reciente de transacciones**

## 🔧 Optimización y Arquitectura

### Flujo de Procesamiento
1. **Entrada** (Texto, Imagen, Audio) → Discord/Web/API
2. **Pre-procesamiento** → Extracción de intenciones (atajos determinísticos para optimizar costos)
3. **Análisis de Intención** → Llamada a Gemini solo cuando es necesario
4. **Fundamentación** → Inyección de datos reales de Firebase para evitar alucinaciones
5. **Ejecución** → Operaciones en Firebase (guardar transacción, crear tarea, etc.)
6. **Respuesta** → Formateo y envío al usuario

### Optimización de Costos de API
- **Atajos determinísticos** para comandos comunes (borrar, listar tareas, etc.) evitan llamadas a Gemini
- **Historial limitado a 10 movimientos** en cada inyección de contexto (reduce tokens ~80%)
- **Cache de contexto financiero** (30 segundos) para evitar consultas redundantes a Firebase
- **Cooldown anti-spam** (3 segundos) para evitar mensajes duplicados
- **Rotación automática de API Keys**: si una key obtiene error 429, cambia instantáneamente a otra

### Manejo de Errores 429
- Detección precisa entre límites por minuto (retryable) y límites diarios (espera hasta mañana)
- Extracción automática de `retryDelay` de los detalles de error de Gemini
- Mensajes de error contextuales y útiles para el usuario

### Rotación de API Keys
- Soporte para múltiples API Keys mediante `GEMINI_API_KEYS` (lista separada por comas)
- Algoritmo round-robin que cambia a la siguiente key al detectar error 429
- Transparente para el usuario: no se pierde la conversación ni se requiere nueva solicitud
- Mayor disponibilidad y tolerancia a fallos de cuota o límites de tasa

## 📈 Mejoras Implementadas

### Optimización de Consumo de API (Agosto 2026)
- Historial limitado a últimos 10 movimientos en prompts (antes: historial completo)
- Cache de contexto financiero con TTL de 30 segundos
- Cooldown anti-spam de 3 segundos entre mensajes por usuario
- Instrucciones más concisas para reducir tokens por consulta
- Solo TTS bajo demanda explícita (no automático por enviar audio)

### Manejo Avanzado de Límites de API (Agosto 2026)
- Detección entre límites por minuto y límites diarios
- Extracción automática de retry delay de errores
- Mensajes de error específicos según el tipo de límite

### Rotación de API Keys (Agosto 2026)
- Soporte para múltiples keys en distintos proyectos Google Cloud
- Fallback automático sin interrupción perceptible para el usuario

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

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

## ☎️ Soporte

Para preguntas y soporte:
- Issues de GitHub
- Documentación en el código (docstrings y comentarios)

---

*Hecho con ❤️ por tu asistente personal ejecutivo JARVIS*