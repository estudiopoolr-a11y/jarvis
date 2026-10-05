@echo off
taskkill /f /im uvicorn.exe >nul 2>&1
start /b uvicorn app.main:app --host 0.0.0.0 --port 8000
timeout /t 5 >nul
curl -i http://localhost:8000/
taskkill /f /im uvicorn.exe >nul 2>&1