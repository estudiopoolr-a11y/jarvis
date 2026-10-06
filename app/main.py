import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="JARVIS API", version="1.0.0")

@app.get("/")
@app.get("/debug")
@app.get("/api/debug")
async def debug_root():
    return {
        "status": "online",
        "environment": os.getenv("VERCEL_ENV", "development"),
        "has_telegram_token": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "has_gemini_key": bool(os.getenv("GEMINI_API_KEY")),
    }

try:
    from app.routes import app as routes_app
    app.mount("", routes_app)
except Exception as e:
    @app.post("/api/telegram/webhook")
    async def fallback_webhook():
        return JSONResponse(
            status_code=500,
            content={"error": "Module initialization failed", "details": str(e)}
        )

handler = app

