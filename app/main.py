import os
from fastapi import FastAPI

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


# Registrar router de Telegram directamente en la app principal
from app.routes.telegram import router as telegram_router
app.include_router(telegram_router)

handler = app