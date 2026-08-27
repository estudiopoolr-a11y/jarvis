import os
import sys
import subprocess
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from modules.database import obtener_balance_financiero, obtener_tareas_pendientes
from modules.ai_brain import procesar_intencion_natural, pensar_respuesta, pensar_respuesta_imagen

app = FastAPI(title="JARVIS Control Center")

class ComandoPayload(BaseModel):
    texto: str
    usuario_id: str = "iphone_user"

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def render_dashboard(usuario_id: str = "default"):
    balance, ingresos, gastos, movimientos = obtener_balance_financiero(usuario_id)
    tareas = obtener_tareas_pendientes(usuario_id)
    
    tareas_html = "".join([
        f"<li style='margin-bottom:8px; background:#1e293b; padding:10px; border-radius:6px; border-left:4px solid #38bdf8;'>"
        f"<strong>[{t['prioridad']}]</strong> {t['tarea']} <span style='color:#94a3b8; font-size:0.85em;'>(Vence: {t['fecha_limite']})</span></li>"
        for t in tareas
    ]) or "<p style='color:#64748b;'>No hay tareas pendientes.</p>"
    
    movs_html = "".join([
        f"<div style='padding:6px 0; border-bottom:1px solid #334155;'>{m}</div>"
        for m in movimientos[-8:]
    ]) or "<p style='color:#64748b;'>Sin movimientos registrados.</p>"

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JARVIS System Control</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #334155; padding-bottom: 15px; margin-bottom: 20px; }}
            .status-badge {{ background-color: #10b981; color: #022c22; font-weight: bold; padding: 6px 14px; border-radius: 20px; font-size: 0.85em; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            .card {{ background: #1e293b; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); border: 1px solid #334155; }}
            .metric {{ font-size: 1.8em; font-weight: bold; margin: 10px 0; }}
            .ingresos {{ color: #4ade80; }}
            .gastos {{ color: #f87171; }}
            .balance {{ color: #38bdf8; }}
            ul {{ list-style-type: none; padding: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🤖 JARVIS System Control</h2>
                <span class="status-badge">ONLINE & ACTIVE</span>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>💰 Estado Financiero</h3>
                    <div class="metric balance">Neto: ${balance:,.0f}</div>
                    <div style="display:flex; justify-content:space-between; margin-top:15px;">
                        <span class="ingresos">Ingresos: +${ingresos:,.0f}</span>
                        <span class="gastos">Gastos: -${gastos:,.0f}</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📋 Tareas Pendientes ({len(tareas)})</h3>
                    <ul>{tareas_html}</ul>
                </div>
                
                <div class="card" style="grid-column: span 2;">
                    <h3>📊 Últimos Movimientos</h3>
                    <div>{movs_html}</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/api/comando")
def ejecutar_comando_shortcut(payload: ComandoPayload):
    respuesta = procesar_intencion_natural(payload.texto, payload.usuario_id)
    if not respuesta:
        respuesta = pensar_respuesta(payload.texto)
    return {"status": "ok", "respuesta": respuesta}

@app.post("/api/recibo")
async def subir_recibo_shortcut(file: UploadFile = File(...), usuario_id: str = Form("iphone_user")):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
        
    resultado = pensar_respuesta_imagen(temp_path, "Extrae el recibo y registra la transacción", usuario_id)
    if os.path.exists(temp_path): os.remove(temp_path)
    return {"status": "ok", "resultado": resultado}

if __name__ == "__main__":
    bot_process = subprocess.Popen([sys.executable, "jarvis_discord.py"])
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)