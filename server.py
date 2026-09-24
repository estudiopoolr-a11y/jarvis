"""
server.py - Entrypoint del Web Service unificado (FastAPI + Discord Bot).

Render tiene configurado 'python server.py' o 'uvicorn server:app --host 0.0.0.0 --port $PORT' como Start Command.
Este archivo arranca la aplicacion FastAPI que inicia concurrentemente el bot de Discord en el mismo event loop.
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path para que 'app' sea importable
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# Importar la app FastAPI unificada
from app.main import app  # noqa: E402

print("[server.py] App unificada importada desde app.main", flush=True)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    print(f"[server.py] Arrancando Uvicorn en 0.0.0.0:{port}", flush=True)
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
