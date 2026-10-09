import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.routes.telegram import router as telegram_router

app = FastAPI(title="JARVIS API", version="1.0.0")

# Registrar router de Telegram directamente en la app principal
app.include_router(telegram_router)

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

# Fallback webhook por si falla el router
@app.post("/api/telegram/webhook")
async def fallback_webhook():
    return JSONResponse(status_code=200, content={"status": "ok", "degraded": True})

handler = app