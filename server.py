import os
import threading
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "JARVIS is online and running!"}

def run_discord_bot():
    # Importa y ejecuta tu bot de Discord para que corra en segundo plano
    import jarvis_discord

if __name__ == "__main__":
    # 1. Iniciamos el bot de Discord en un hilo separado para que no bloquee el puerto
    bot_thread = threading.Thread(target=run_discord_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # 2. Iniciamos FastAPI en el hilo principal para que Render detecte el puerto abierto
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)