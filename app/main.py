"""
app/main.py - Entrypoint FastAPI para JARVIS.

Las rutas viven en app/routes.py. Este wrapper mantiene
la fijacion Procfile (uvicorn app.main:app) y server.py intactos
para Render.
"""
from app.routes import app
from fastapi import Request

# For Vercel, we need to export the handler
handler = app

# Debug route to test if the function is being called
@app.get("/debug")
async def debug():
    return {"message": "debug"}

# Add a catch-all route for debugging that handles all HTTP methods
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def catch_all(path: str, request: Request):
    return {"message": f"Catch-all: {path}", "method": request.method, "path": path}

__all__ = ["app", "handler"]

if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
