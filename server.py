"""
server.py - Entrypoint del Web Service.

Render tiene configurado 'python server.py' como Start Command.
Este archivo arranca el servidor FastAPI real que vive en app/main.py.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path para que 'app' sea importable
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# Importar la app FastAPI
from app.main import app  # noqa: E402

print("[server.py] App importada desde app.main", flush=True)

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    print(f"[server.py] Arrancando Uvicorn en 0.0.0.0:{port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)
