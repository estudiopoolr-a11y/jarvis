# 🤖 Proyecto JARVIS - Asistente Personal

Asistente personal inteligente integrado con inteligencia artificial (Gemini) y automatización para la gestión de tareas, finanzas y notas de voz.

## 📂 Estructura del Proyecto

jarvis/
│
├── .env                  # 🔒 Variables de entorno y credenciales (API Key)
├── .gitignore
├── iniciar_jarvis.bat
├── jarvis_discord.py
├── jarvis-be47a-firebase-adminsdk-fbsvc-c87a300e12.json
├── main.py               # 🚀 Punto de entrada principal del sistema
├── readme.md
├── requirements.txt      # 📦 Dependencias y librerías de Python
├── server.py 
│
├── audio_cache/          # 🎵 Carpeta temporal para procesamiento de notas de voz
│
└── modules/              # 🧩 Módulos de lógica separada
    ├── database.py
    └── ai_brain.py       # 🧠 Conexión y lógica de procesamiento con Gemini