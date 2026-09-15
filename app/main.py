"""
app/main.py - Entrypoint FastAPI para JARVIS.

Las rutas viven en app/routes.py. Este wrapper mantiene
la fijacion Procfile (uvicorn app.main:app) y server.py intactos
para Render.
"""
from app.routes import app

__all__ = ["app"]

if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
