from app.api import ComandoPayload, app
from modules.ai import pensar_respuesta, procesar_intencion_natural

@app.post("/api/comando")
def ejecutar_comando_shortcut(payload: ComandoPayload):
    respuesta = procesar_intencion_natural(payload.texto, payload.usuario_id)
    if not respuesta:
        respuesta = pensar_respuesta(payload.texto)
    return {"status": "ok", "respuesta": respuesta}
