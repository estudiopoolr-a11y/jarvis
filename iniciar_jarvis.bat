@echo off
echo Cerrando instancias previas de Chrome...
taskkill /f /im chrome.exe >nul 2>&1

echo Abriendo Chrome con conexion activa (Puerto 9222)...
start chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDevSession"

echo Esperando a que el navegador este listo...
timeout /t 4 /nobreak >nul

echo Activando entorno virtual y lanzando a JARVIS...
cd /d "C:\Users\DEEL\OneDrive\Desktop\Projects\jarvis"
call .venv\Scripts\activate
python jarvis_whatsapp.py

pause