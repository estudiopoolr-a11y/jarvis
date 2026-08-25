# 🤖 Proyecto JARVIS - Asistente Personal

Asistente personal inteligente integrado con inteligencia artificial (Gemini) y automatización para la gestión de tareas, finanzas y notas de voz.

## 📂 Estructura del Proyecto

jarvis/
│
├── .env                  # 🔒 Variables de entorno y credenciales (API Key)
├── requirements.txt      # 📦 Dependencias y librerías de Python
├── main.py               # 🚀 Punto de entrada principal del sistema
│
├── database/             # 🗄️ Almacenamiento de bases de datos SQLite (tareas, etc.)
│   └── tasks.db
│
├── audio_cache/          # 🎵 Carpeta temporal para procesamiento de notas de voz
│
└── modules/              # 🧩 Módulos de lógica separada
    ├── __init__.py
    ├── ai_brain.py       # 🧠 Conexión y lógica de procesamiento con Gemini
    └── 
       # 📱 Conexión y automatización con WhatsApp