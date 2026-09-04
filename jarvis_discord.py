"""
jarvis_discord.py - Shim de compatibilidad.

Render tenía configurado ejecutar este archivo como entrypoint.
Ahora el servidor real es app/main.py. Este shim solo lo importa
para que el deploy no falle y el servidor web arranque.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# Importar y arrancar la app
from app.main import app

# Log para saber que el shim está corriendo
print("=" * 60)
print("🟢 JARVIS shim: importando app.main")
print(f"   Rutas disponibles: {len(app.routes)}")
print("=" * 60)

if __name__ == "__main__":
    import uvicorn
    port = int(__import__("os").getenv("PORT", 8000))
    print(f"🚀 Arrancando uvicorn en puerto {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
