import os
import sys
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from modules.database import (
    obtener_balance_financiero,
    obtener_tareas_pendientes,
    obtener_resumen_presupuestos
)
from pydantic import BaseModel
import uvicorn

from modules.database import obtener_balance_financiero, obtener_tareas_pendientes
from modules.ai_brain import procesar_intencion_natural, pensar_respuesta, pensar_respuesta_imagen

app = FastAPI(title="JARVIS Control Center")

class ComandoPayload(BaseModel):
    texto: str
    usuario_id: str = "iphone_user"

@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.head("/dashboard", response_class=HTMLResponse)
def render_dashboard(usuario_id: str = "default"):
    balance, ingresos, gastos, movimientos = obtener_balance_financiero(usuario_id)
    tareas = obtener_tareas_pendientes(usuario_id)
    presupuestos = obtener_resumen_presupuestos(usuario_id)

    # Generar HTML de Presupuestos
    html_presupuestos = ""
    if not presupuestos:
        html_presupuestos = "<p style='color:#888;'>No has establecido presupuestos aún.</p>"
    else:
        for p in presupuestos:
            porcentaje = min(int((p['gastado'] / p['limite']) * 100) if p['limite'] > 0 else 0, 100)
            color_barra = "#e74c3c" if p['excedido'] else ("#f39c12" if porcentaje > 80 else "#2ecc71")
            
            html_presupuestos += f"""
            <div style="background:#1e1e2e; padding:15px; border-radius:10px; margin-bottom:12px; border-left:5px solid {color_barra};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="color:#fff; font-size:16px;">{p['categoria']}</strong>
                    <span style="color:{color_barra}; font-weight:bold;">
                        {'$' + f"{abs(p['restante']):,.0f}" + (' Excedido ⚠️' if p['excedido'] else ' Restante')}
                    </span>
                </div>
                <div style="font-size:12px; color:#aaa; margin:5px 0;">
                    Gastado: ${p['gastado']:,.0f} de ${p['limite']:,.0f}
                </div>
                <div style="background:#313244; height:8px; border-radius:4px; overflow:hidden;">
                    <div style="background:{color_barra}; width:{porcentaje}%; height:100%;"></div>
                </div>
            </div>
            """

    # HTML Completo del Dashboard
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JARVIS Dashboard</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background:#11111b; color:#cdd6f4; margin:0; padding:20px; }}
            .container {{ max-width:900px; margin:auto; }}
            .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:20px; margin-top:20px; }}
            .card {{ background:#181825; padding:20px; border-radius:12px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
            h1, h2 {{ color:#cba6f7; }}
            .balance-card {{ background: linear-gradient(135deg, #1e1e2e, #313244); text-align:center; padding:20px; border-radius:12px; margin-bottom:20px; }}
            .ingreso {{ color:#a6e3a1; }}
            .gasto {{ color:#f38ba8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 JARVIS - Control Personal</h1>
            
            <div class="balance-card">
                <h2>Balance Neto: ${balance:,.0f}</h2>
                <p><span class="ingreso">🟢 Ingresos: ${ingresos:,.0f}</span> | <span class="gasto">🔴 Gastos: ${gastos:,.0f}</span></p>
            </div>

            <div class="grid">
                <div class="card">
                    <h2>📊 Presupuestos</h2>
                    {html_presupuestos}
                </div>

                <div class="card">
                    <h2>📋 Tareas Pendientes</h2>
                    <ul>
                        {"".join([f"<li><strong>{t['tarea']}</strong> ({t['prioridad']})</li>" for t in tareas]) if tareas else "<li>Sin tareas pendientes 🎉</li>"}
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

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

@app.get("/api/cron/daily-summary")
def cron_daily_summary():
    """Endpoint para Render Cron Job - envía resumen diario al canal de Discord."""
    try:
        from daily_summary import main as daily_main
        daily_main()
        return {"status": "ok", "message": "Resumen enviado"}
    except Exception as e:
        print(f"Error en cron daily-summary: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # NOTA: El bot de Discord se ejecuta LOCALMENTE (jarvis_discord.py).
    # Render solo ejecuta el dashboard web y API.
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)