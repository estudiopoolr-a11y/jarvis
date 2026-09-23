"""Kebo HTTP routes: reports."""
from fastapi.responses import HTMLResponse

from app.api import app

@app.get("/api/kebo/metas")
def api_kebo_metas(usuario_id: str = "default"):
    """API para widget: lista de metas de ahorro."""
    try:
        from modules.db import listar_metas_v2
        metas = listar_metas_v2(usuario_id)
        return {"metas": metas}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/recurrentes")
def api_kebo_recurrentes(usuario_id: str = "default"):
    """API para widget: lista de recurrentes activos."""
    try:
        from modules.db import listar_recurrentes
        recurrentes = listar_recurrentes(usuario_id)
        return {"recurrentes": recurrentes}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/estadisticas")
def api_kebo_estadisticas(usuario_id: str = "default", meses: int = 6):
    """Endpoint para gráficos: estadísticas agregadas."""
    try:
        from modules.db import obtener_estadisticas
        stats = obtener_estadisticas(usuario_id, meses)
        return stats
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/recordatorios")
def api_kebo_recordatorios(usuario_id: str = "default"):
    """Lista recordatorios del usuario."""
    try:
        from modules.db import listar_recordatorios, obtener_recordatorios_hoy
        return {
            "hoy": obtener_recordatorios_hoy(usuario_id),
            "todos": listar_recordatorios(usuario_id)
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/pronostico")
def api_kebo_pronostico(usuario_id: str = "default"):
    """Pronóstico de gastos para el mes actual basado en historial."""
    try:
        from modules.db import obtener_estadisticas
        stats = obtener_estadisticas(usuario_id, meses=6)
        tendencia = stats.get("tendencia", [])

        if len(tendencia) < 2:
            return {"error": True, "message": "Sin suficiente historial para calcular pronóstico"}

        # Calcular promedio de gastos de los últimos 3 meses
        gastos_recientes = [t["gastos"] for t in tendencia[-3:]]
        promedio = sum(gastos_recientes) / len(gastos_recientes)

        # Tendencia: comparar últimos 2 meses
        if len(tendencia) >= 2:
            mes_actual = tendencia[-1]["gastos"]
            mes_anterior = tendencia[-2]["gastos"]
            if mes_anterior > 0:
                cambio_pct = ((mes_actual - mes_anterior) / mes_anterior) * 100
            else:
                cambio_pct = 0
        else:
            cambio_pct = 0

        # Pronóstico simple: promedio ponderado (más peso al mes más reciente)
        if len(gastos_recientes) >= 2:
            pronostico = (gastos_recientes[-1] * 0.5 + promedio * 0.5)
        else:
            pronostico = promedio

        return {
            "pronostico_mensual": round(pronostico, -3),
            "promedio_3_meses": round(promedio, -3),
            "gastos_mes_actual": round(tendencia[-1]["gastos"] if tendencia else 0),
            "gastos_mes_anterior": round(tendencia[-2]["gastos"] if len(tendencia) > 1 else 0),
            "cambio_vs_mes_anterior_pct": round(cambio_pct, 1),
            "tendencia": "📈 Al alza" if cambio_pct > 5 else "📉 A la baja" if cambio_pct < -5 else "➡️ Estable",
            "mensaje": f"Este mes podrías gastar ~${round(pronostico/100000, 1):.1f}M basado en tus últimos 3 meses."
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/export-pdf")
def api_kebo_export_pdf(usuario_id: str = "default"):
    """Genera un reporte mensual en HTML optimizado para imprimir/PDF."""
    try:
        from modules.db import (
            obtener_balance_v2, listar_cuentas, obtener_presupuestos_v2,
            listar_transacciones_recientes, obtener_estadisticas, listar_metas_v2,
            obtener_alertas_presupuesto
        )
        from datetime import datetime

        balance, ingresos, gastos, _ = obtener_balance_v2(usuario_id)
        cuentas = listar_cuentas(usuario_id)
        presupuestos = obtener_presupuestos_v2(usuario_id)
        transacciones = listar_transacciones_recientes(usuario_id, limite=30)
        stats = obtener_estadisticas(usuario_id, meses=6)
        metas = listar_metas_v2(usuario_id)
        alertas = obtener_alertas_presupuesto(usuario_id)

        ahora = datetime.now()
        mes_nombre = ahora.strftime("%B %Y").capitalize()

        # Generar HTML del reporte
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte JARVIS - {mes_nombre}</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }}
    h1 {{ color: #6366f1; border-bottom: 2px solid #6366f1; padding-bottom: 10px; }}
    h2 {{ color: #444; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; }}
    .date {{ color: #888; font-size: 14px; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
    .card {{ background: #f8f9fa; border-radius: 8px; padding: 15px; text-align: center; }}
    .card-value {{ font-size: 24px; font-weight: bold; }}
    .income {{ color: #10b981; }}
    .expense {{ color: #ef4444; }}
    .balance {{ color: #6366f1; }}
    table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
    th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
    th {{ background: #f0f0f5; font-weight: 600; }}
    .total {{ font-weight: bold; background: #f0f0f5; }}
    .alert-warning {{ color: #f59e0b; }}
    .alert-danger {{ color: #ef4444; }}
    .accounts {{ margin: 15px 0; }}
    .account-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
    @media print {{ body {{ padding: 0; }} .no-print {{ display: none; }} }}
</style>
</head>
<body>
<div class="header">
    <div>
        <h1>📊 Reporte JARVIS</h1>
        <p class="date">{mes_nombre} | Generado: {ahora.strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    <div style="text-align:right">
        <button class="no-print" onclick="window.print()" style="padding:10px 20px;background:#6366f1;color:white;border:none;border-radius:8px;cursor:pointer">🖨️ Imprimir / Guardar PDF</button>
    </div>
</div>

<h2>💰 Resumen del Mes</h2>
<div class="grid">
    <div class="card">
        <div style="color:#888;font-size:12px">INGRESOS</div>
        <div class="card-value income">{ingresos:,.0f}</div>
    </div>
    <div class="card">
        <div style="color:#888;font-size:12px">GASTOS</div>
        <div class="card-value expense">{gastos:,.0f}</div>
    </div>
    <div class="card">
        <div style="color:#888;font-size:12px">BALANCE</div>
        <div class="card-value balance">{balance:,.0f}</div>
    </div>
</div>

<h2>💳 Cuentas</h2>
<div class="accounts">
    {"".join(f'<div class="account-row"><span>{c.get("icono","💳")} {c.get("nombre","")}</span><span style="font-weight:bold">${c.get("balance",0):,.0f}</span></div>' for c in cuentas)}
    <div class="account-row" style="font-weight:bold;border-top:2px solid #ddd;padding-top:12px">
        <span>Total</span><span>${sum(c.get("balance",0) for c in cuentas):,.0f}</span>
    </div>
</div>

<h2>📁 Gastos por Categoría</h2>
<table>
    <tr><th>Categoría</th><th>Límite</th><th>Gastado</th><th>Restante</th><th>%</th></tr>
    {"".join(f'<tr><td>{p}</td><td>${v["limite"]:,.0f}</td><td style="color:{"#ef4444" if v["gastado"]>v["limite"] else "#333"}">${v["gastado"]:,.0f}</td><td>${v["libre"]:,.0f}</td><td>{round(v["gastado"]/max(v["limite"],1)*100,1)}%</td></tr>' for p,v in presupuestos.items() if v["limite"]>0)}
</table>

<h2>📋 Transacciones Recientes</h2>
<table>
    <tr><th>Fecha</th><th>Descripción</th><th>Categoría</th><th style="text-align:right">Monto</th></tr>
    {"".join(f'<tr><td>{t.get("fecha","")}</td><td>{t.get("descripcion","")}</td><td>{t.get("categoria","")}</td><td style="text-align:right;color:{"#ef4444" if t.get("tipo")=="expense" else "#10b981"}">{"-" if t.get("tipo")=="expense" else "+"}${t.get("monto",0):,.0f}</td></tr>' for t in transacciones[:20])}
</table>

<h2>🎯 Metas</h2>
<table>
    <tr><th>Meta</th><th>Objetivo</th><th>Actual</th><th>Progreso</th></tr>
    {"".join(f'<tr><td>{m.get("nombre","")}</td><td>${m.get("monto_objetivo",0):,.0f}</td><td>${m.get("current_amount",0):,.0f}</td><td>{round(m.get("current_amount",0)/max(m.get("monto_objetivo",1),1)*100,1)}%</td></tr>' for m in metas)}
</table>

{"<h2>⚠️ Alertas</h2><ul>" + "".join(f'<li class="{"alert-danger" if a.get("tipo")=="excedido" else "alert-warning"}">{a.get("mensaje","")}</li>' for a in alertas) + "</ul>" if alertas else ""}

<div style="margin-top:40px;text-align:center;color:#888;font-size:12px">
    Generado por JARVIS - {ahora.strftime('%d/%m/%Y %H:%M')}
</div>
</body>
</html>"""
        return HTMLResponse(content=html, media_type="text/html")
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"error": True, "message": str(e)}
