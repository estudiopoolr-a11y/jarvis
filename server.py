import os
import sys
import subprocess
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "JARVIS is online and running!"}

if __name__ == "__main__":
    # 1. Usamos sys.executable para que use el entorno virtual (.venv) correcto
    print("Iniciando JARVIS Discord Bot...")
    bot_process = subprocess.Popen([sys.executable, "jarvis_discord.py"])

    # 2. Iniciamos FastAPI para que Render detecte el puerto abierto
    port = int(os.environ.get("PORT", 10000))
    print(f"Iniciando servidor web en el puerto {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)