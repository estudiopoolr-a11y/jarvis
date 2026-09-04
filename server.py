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

    # Calcular gastos reales por categoría
    gastos_por_categoria = {}
    for t in movimientos:
        if t.get("tipo") == "gasto":
            cat = t.get("categoria", "General")
            monto = float(t.get("monto", 0))
            gastos_por_categoria[cat] = gastos_por_categoria.get(cat, 0) + monto

    # Generar HTML de Presupuestos
    html_presupuestos = ""
    if not presupuestos:
        html_presupuestos = "<p style='color:#888;'>No has establecido presupuestos aún.</p>"
    else:
        for categoria, limite in presupuestos.items():
            gastado = gastos_por_categoria.get(categoria, 0)
            restante = limite - gastado
            excedido = restante < 0
            porcentaje = min(int((abs(gastado) / limite) * 100) if limite > 0 else 0, 100)
            # Para la barra, mostrar porcentaje del límite usado (hasta 100%)
            porcentaje_barra = min(int((gastado / limite) * 100) if limite > 0 else 0, 100) if gastado >= 0 else 100
            color_barra = "#e74c3c" if excedido else ("#f39c12" if porcentaje_barra > 80 else "#2ecc71")

            html_presupuestos += f"""
            <div style="background:#1e1e2e; padding:15px; border-radius:10px; margin-bottom:12px; border-left:5px solid {color_barra};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="color:#fff; font-size:16px;">{categoria}</strong>
                    <span style="color:{color_barra}; font-weight:bold;">
                        {'$' + f"{abs(restante):,.0f}" + (' Excedido ⚠️' if excedido else ' Restante')}
                    </span>
                </div>
                <div style="font-size:12px; color:#aaa; margin:5px 0;">
                    Gastado: ${gastado:,.0f} de ${limite:,.0f}
                </div>
                <div style="background:#313244; height:8px; border-radius:4px; overflow:hidden;">
                    <div style="background:{color_barra}; width:{porcentaje_barra}%; height:100%;"></div>
                </div>
            </div>
            """

    # HTML Completo del Dashboard
    # Preparar datos para gráficos
    gastos_por_categoria = {}
    for t in movimientos:
        if t.get("tipo") == "gasto":
            cat = t.get("categoria", "General")
            monto = float(t.get("monto", 0))
            gastos_por_categoria[cat] = gastos_por_categoria.get(cat, 0) + monto

    import json
    chart_data = json.dumps({
        "categorias": list(gastos_por_categoria.keys()),
        "montos": list(gastos_por_categoria.values())
    })

    # Datos de presupuesto vs gastado para gráfico de barras
    presupuesto_vs_gastado = []
    for cat, limite in presupuestos.items():
        gastado = gastos_por_categoria.get(cat, 0)
        presupuesto_vs_gastado.append({"cat": cat, "limite": limite, "gastado": gastado})

    chart_bar_data = json.dumps(presupuesto_vs_gastado)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JARVIS Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background:#11111b; color:#cdd6f4; margin:0; padding:20px; }}
            .container {{ max-width:1200px; margin:auto; }}
            .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap:20px; margin-top:20px; }}
            .card {{ background:#181825; padding:20px; border-radius:12px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
            h1, h2 {{ color:#cba6f7; }}
            .balance-card {{ background: linear-gradient(135deg, #1e1e2e, #313244); text-align:center; padding:20px; border-radius:12px; margin-bottom:20px; }}
            .ingreso {{ color:#a6e3a1; }}
            .gasto {{ color:#f38ba8; }}
            .chart-container {{ position: relative; height: 300px; }}
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
                    <h2>🥧 Gastos por Categoría</h2>
                    <div class="chart-container">
                        <canvas id="pieChart"></canvas>
                    </div>
                </div>

                <div class="card">
                    <h2>📊 Presupuesto vs Gastado</h2>
                    <div class="chart-container">
                        <canvas id="barChart"></canvas>
                    </div>
                </div>

                <div class="card">
                    <h2>🎯 Presupuestos</h2>
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

        <script>
            // Gráfico de pastel: Gastos por categoría
            const pieData = {chart_data};
            if (pieData.categorias.length > 0) {{
                new Chart(document.getElementById('pieChart'), {{
                    type: 'doughnut',
                    data: {{
                        labels: pieData.categorias,
                        datasets: [{{
                            data: pieData.montos,
                            backgroundColor: ['#cba6f7', '#f38ba8', '#a6e3a1', '#fab387', '#89b4fa', '#f9e2af', '#94e2d5', '#b4befe']
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'bottom', labels: {{ color: '#cdd6f4' }} }}
                        }}
                    }}
                }});
            }}

            // Gráfico de barras: Presupuesto vs Gastado
            const barData = {chart_bar_data};
            if (barData.length > 0) {{
                new Chart(document.getElementById('barChart'), {{
                    type: 'bar',
                    data: {{
                        labels: barData.map(d => d.cat),
                        datasets: [
                            {{ label: 'Presupuesto', data: barData.map(d => d.limite), backgroundColor: '#89b4fa' }},
                            {{ label: 'Gastado', data: barData.map(d => d.gastado), backgroundColor: '#f38ba8' }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ labels: {{ color: '#cdd6f4' }} }}
                        }},
                        scales: {{
                            x: {{ ticks: {{ color: '#cdd6f4' }} }},
                            y: {{ ticks: {{ color: '#cdd6f4' }} }}
                        }}
                    }}
                }});
            }}
        </script>
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

@app.get("/api/finanzas/resumen")
def api_finanzas_resumen(usuario_id: str = "default"):
    """API para widget iPhone Scriptable: resumen del MES ACTUAL con presupuestos y gastado por categoría."""
    import traceback
    from datetime import datetime
    from google.cloud.firestore_v1.base_query import FieldFilter

    try:
        from modules.database import inicializar_firebase
        db = inicializar_firebase()
        if not db:
            return {"error": True, "message": "DB no inicializada"}

        # Mes actual en formato YYYY-MM
        mes_actual = datetime.now().strftime("%Y-%m")

        # 1) Obtener TODOS los presupuestos (no tienen campo mes en la estructura actual)
        docs_pres = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        presupuestos = {}
        for doc in docs_pres:
            d = doc.to_dict()
            presupuestos[d.get("categoria")] = float(d.get("limite", 0))

        # 2) Obtener transacciones y filtrar por mes actual
        ingresos = 0.0
        gastos = 0.0
        gastos_por_categoria = {}
        balance = 0.0

        docs_fin = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        for t in docs_fin:
            d = t.to_dict()
            # Filtrar por mes si tiene campo fecha o mes
            fecha_str = d.get("fecha", "") or d.get("timestamp", "")
            mes_doc = d.get("mes", "")
            if not mes_doc and fecha_str and len(fecha_str) >= 7:
                mes_doc = fecha_str[:7]

            # Solo contar los del mes actual
            if mes_doc and mes_doc != mes_actual:
                continue

            monto = float(d.get("monto", 0))
            tipo = d.get("tipo", "gasto")
            cat = d.get("categoria", "General")

            if tipo == "ingreso":
                ingresos += monto
            else:
                gastos += monto
                gastos_por_categoria[cat] = gastos_por_categoria.get(cat, 0) + monto

        balance = ingresos - gastos

        # 3) Construir respuesta
        datos_por_categoria = []
        total_limite = 0
        total_gastado = 0
        total_libre = 0

        for categoria, limite in sorted(presupuestos.items()):
            gastado = gastos_por_categoria.get(categoria, 0)
            libre = limite - gastado
            excedido = libre < 0
            total_limite += limite
            total_gastado += gastado
            total_libre += libre

            datos_por_categoria.append({
                "categoria": categoria,
                "limite": round(limite),
                "gastado": round(gastado),
                "libre": round(libre),
                "excedido": excedido
            })

        return {
            "mes": mes_actual,
            "balance": round(balance),
            "ingresos": round(ingresos),
            "gastos": round(gastos),
            "total_limite": round(total_limite),
            "total_gastado": round(total_gastado),
            "total_libre": round(total_libre),
            "porcentaje_uso": round((total_gastado / max(total_limite, 1)) * 100),
            "datos_por_categoria": datos_por_categoria
        }
    except Exception as e:
        return {
            "error": True,
            "tipo_error": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()[:1000]
        }

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

@app.get("/api/cron/weekly-summary")
def cron_weekly_summary():
    """Endpoint para Render Cron Job - envía resumen semanal al canal de Discord."""
    try:
        from modules.alertas import enviar_resumen_semanal_discord
        exito = enviar_resumen_semanal_discord()
        if exito:
            return {"status": "ok", "message": "Resumen semanal enviado"}
        else:
            return {"status": "error", "message": "Error enviando resumen semanal"}
    except Exception as e:
        print(f"Error en cron weekly-summary: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/cron/alertas")
def cron_alertas():
    """Endpoint para Render Cron Job - verifica y envía alertas proactivas."""
    try:
        from modules.alertas import verificar_y_enviar_alertas
        resultado = verificar_y_enviar_alertas()
        return resultado
    except Exception as e:
        print(f"Error en cron alertas: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # NOTA: El bot de Discord se ejecuta LOCALMENTE (jarvis_discord.py).
    # Render solo ejecuta el dashboard web y API.
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)