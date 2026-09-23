import os
import sys
from pathlib import Path

from fastapi import File, Form, UploadFile
from fastapi.responses import HTMLResponse

from app.api import USUARIO_PRINCIPAL, ComandoPayload, app
from modules.ai import pensar_respuesta, pensar_respuesta_imagen, procesar_intencion_natural
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos, obtener_tareas_pendientes

@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.head("/dashboard", response_class=HTMLResponse)
def render_dashboard(usuario_id: str = "default"):
    """Sirve el dashboard web estático con datos en tiempo real."""
    import os
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("<h1>Dashboard no disponible</h1>", status_code=500)


# Mantener endpoint legacy (se conserva por compatibilidad)
@app.get("/dashboard/v1", response_class=HTMLResponse)
def render_dashboard_v1(usuario_id: str = "default"):
    balance, ingresos, gastos, movimientos = obtener_balance_financiero(usuario_id)
    tareas = obtener_tareas_pendientes(usuario_id)
    presupuestos = obtener_resumen_presupuestos(usuario_id)
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
