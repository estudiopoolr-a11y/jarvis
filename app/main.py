import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path para que los imports funcionen desde app/
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

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
    """Sirve el dashboard web estático con datos en tiempo real."""
    import os
    template_path = os.path.join(os.path.dirname(__file__), "app", "templates", "dashboard.html")
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

        # 2) Obtener TODAS las transacciones (sin filtro de mes porque no todas tienen campo mes)
        ingresos = 0.0
        gastos = 0.0
        gastos_por_categoria = {}
        balance = 0.0

        docs_fin = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        for t in docs_fin:
            d = t.to_dict()
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


@app.get("/api/kebo/cuentas")
def api_kebo_cuentas(usuario_id: str = "default"):
    """API para widget iPhone: lista de cuentas con balances (NUEVA ESTRUCTURA KEBO)."""
    import traceback
    try:
        from modules.database import listar_cuentas
        cuentas = listar_cuentas(usuario_id)
        return {
            "cuentas": cuentas,
            "total_balance": sum(c.get("balance", 0) for c in cuentas)
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/transacciones")
def api_kebo_transacciones(usuario_id: str = "default", limite: int = 20):
    """API para widget: últimas transacciones."""
    try:
        from modules.database import listar_transacciones_recientes
        transacciones = listar_transacciones_recientes(usuario_id, limite)
        return {"transacciones": transacciones}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/backup/export")
def api_backup_export(usuario_id: str = "default"):
    """Endpoint para hacer backup de TODOS los datos. Útil para migración."""
    import json
    from datetime import datetime
    from google.cloud.firestore_v1.base_query import FieldFilter
    try:
        from modules.database import inicializar_firebase
        db = inicializar_firebase()
        if not db:
            return {"error": "DB no inicializada"}

        backup = {
            "fecha": datetime.now().isoformat(),
            "usuario_id": usuario_id,
            "colecciones": {}
        }

        # finanzas
        docs = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        backup["colecciones"]["finanzas"] = [{**d.to_dict(), "_id": d.id} for d in docs]

        # presupuestos
        docs = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        backup["colecciones"]["presupuestos"] = [{**d.to_dict(), "_id": d.id} for d in docs]

        # tareas
        docs = db.collection("tareas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        backup["colecciones"]["tareas"] = [{**d.to_dict(), "_id": d.id} for d in docs]

        # metas
        try:
            docs = db.collection("metas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
            backup["colecciones"]["metas"] = [{**d.to_dict(), "_id": d.id} for d in docs]
        except:
            backup["colecciones"]["metas"] = []

        return backup
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/backup/migrate")
def api_backup_migrate(usuario_id: str = "default"):
    """Migra los datos de estructura vieja a nueva estructura Kebo."""
    import json
    from datetime import datetime
    from google.cloud.firestore_v1.base_query import FieldFilter
    from modules.database import (
        ensure_user, crear_cuenta, crear_categoria, registrar_transaccion_v2
    )

    try:
        from modules.database import inicializar_firebase
        db = inicializar_firebase()
        if not db:
            return {"error": "DB no inicializada"}

        stats = {"cuentas_creadas": 0, "categorias_migradas": 0, "transacciones_migradas": 0}

        # 1. Crear usuario y cuentas por defecto
        ensure_user(usuario_id, "Pool")

        # Crear cuentas si no existen
        cuentas_default = [
            {"nombre": "Efectivo", "tipo": "cash", "balance": 0},
            {"nombre": "Nequi", "tipo": "debit", "balance": 0},
            {"nombre": "Crédito", "tipo": "credit", "balance": 0},
        ]
        for c in cuentas_default:
            crear_cuenta(usuario_id, c["nombre"], c["tipo"], c["balance"])
            stats["cuentas_creadas"] += 1

        # 2. Migrar presupuestos → categorías
        docs_p = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        categorias_mapeadas = {}
        for doc in docs_p:
            d = doc.to_dict()
            cat_nombre = d.get("categoria", "General")
            limite = float(d.get("limite", 0))
            cat_id = crear_categoria(usuario_id, cat_nombre, limite)
            categorias_mapeadas[cat_nombre] = cat_id
            stats["categorias_migradas"] += 1

        # 3. Migrar transacciones
        docs_t = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).stream()
        for doc in docs_t:
            d = doc.to_dict()
            monto = float(d.get("monto", 0))
            cat = d.get("categoria", "General")
            tipo_db = "expense" if d.get("tipo") == "gasto" else "income"
            registrar_transaccion_v2(usuario_id, tipo_db, monto, cat, d.get("descripcion", ""), "Efectivo")
            stats["transacciones_migradas"] += 1

        return {"status": "ok", "stats": stats}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/metas")
def api_kebo_metas(usuario_id: str = "default"):
    """API para widget: lista de metas de ahorro."""
    try:
        from modules.database import listar_metas_v2
        metas = listar_metas_v2(usuario_id)
        return {"metas": metas}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/recurrentes")
def api_kebo_recurrentes(usuario_id: str = "default"):
    """API para widget: lista de recurrentes activos."""
    try:
        from modules.database import listar_recurrentes
        recurrentes = listar_recurrentes(usuario_id)
        return {"recurrentes": recurrentes}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/alertas")
def api_kebo_alertas(usuario_id: str = "default"):
    """API para widget: alertas de presupuesto activas."""
    try:
        from modules.database import obtener_alertas_presupuesto
        alertas = obtener_alertas_presupuesto(usuario_id)
        return {"alertas": alertas}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/cron/recurrentes")
def cron_ejecutar_recurrentes():
    """Cron diario: ejecuta recurrentes que tocan hoy."""
    try:
        from modules.database import ejecutar_recurrentes
        ejecutados = ejecutar_recurrentes("iphone_user")
        return {"status": "ok", "ejecutados": ejecutados}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/cron/monthly-report")
def cron_monthly_report():
    """Cron mensual: envía reporte del mes anterior a Discord."""
    try:
        from app.services.monthly_report import generar_reporte_mes_anterior, enviar_a_discord
        datos = generar_reporte_mes_anterior("iphone_user")
        if datos:
            ok = enviar_a_discord(datos)
            return {"status": "ok" if ok else "error", "mes": datos.get("mes_nombre")}
        return {"status": "no_data"}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/cron/reminders")
def cron_reminders():
    """Cron diario: envía recordatorios de pagos recurrentes a Discord."""
    try:
        from app.services.reminders import obtener_pagos_hoy, obtener_recordatorios_personalizados, enviar_recordatorio_discord
        pagos = obtener_pagos_hoy("iphone_user")
        recordatorios = obtener_recordatorios_personalizados("iphone_user")
        ok = enviar_recordatorio_discord(pagos, recordatorios)
        return {"status": "ok" if ok else "no_data", "pagos": len(pagos), "recordatorios": len(recordatorios)}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/seed")
def api_kebo_seed(usuario_id: str = "default"):
    """Endpoint one-time: crea categorías predefinidas y cuentas default."""
    try:
        from modules.database import crear_categorias_predefinidas, crear_cuenta, ensure_user
        ensure_user(usuario_id, "Pool")
        cats_creadas = crear_categorias_predefinidas(usuario_id)

        # Crear cuentas solo si no existen
        cuentas_default = [
            {"nombre": "Efectivo", "tipo": "cash"},
            {"nombre": "Nequi", "tipo": "debit"},
            {"nombre": "Crédito", "tipo": "credit"},
        ]
        from modules.database import listar_cuentas
        existing = [c.get("nombre") for c in listar_cuentas(usuario_id)]
        cuentas_creadas = 0
        for c in cuentas_default:
            if c["nombre"] not in existing:
                crear_cuenta(usuario_id, c["nombre"], c["tipo"], 0)
                cuentas_creadas += 1

        return {"status": "ok", "categorias_creadas": cats_creadas, "cuentas_creadas": cuentas_creadas}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/estadisticas")
def api_kebo_estadisticas(usuario_id: str = "default", meses: int = 6):
    """Endpoint para gráficos: estadísticas agregadas."""
    try:
        from modules.database import obtener_estadisticas
        stats = obtener_estadisticas(usuario_id, meses)
        return stats
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/export")
def api_kebo_export(usuario_id: str = "default"):
    """Descarga JSON completo de todos los datos del usuario."""
    try:
        from modules.database import exportar_json_completo
        import json
        data = exportar_json_completo(usuario_id)
        if not data:
            return {"error": "No se pudo exportar"}
        from fastapi.responses import Response
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=jarvis_export_{usuario_id}.json"
            }
        )
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/export-csv")
def api_kebo_export_csv(usuario_id: str = "default", mes: str = None):
    """Descarga CSV de transacciones del mes."""
    try:
        from modules.database import exportar_csv
        csv_data, filename = exportar_csv(usuario_id, mes)
        if not csv_data:
            return {"error": "No se pudo exportar"}
        from fastapi.responses import Response
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/presupuestos")
def api_kebo_presupuestos(usuario_id: str = "default", mes: str = None):
    """API para widget iPhone: presupuestos con gastado del mes (NUEVA ESTRUCTURA KEBO)."""
    import traceback
    from datetime import datetime
    try:
        from modules.database import obtener_presupuestos_v2
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        presupuestos = obtener_presupuestos_v2(usuario_id, mes)
        return {"mes": mes, "presupuestos": presupuestos}
    except Exception as e:
        return {"error": True, "message": str(e)}


# ==================== ENDPOINTS NUEVAS FEATURES KEBO ====================

@app.get("/api/kebo/subcategorias")
def api_kebo_subcategorias(usuario_id: str = "default", categoria: str = ""):
    """Lista sub-categorías de una categoría padre."""
    try:
        from modules.database import listar_subcategorias, crear_subcategorias_predefinidas
        if not categoria:
            return {"error": True, "message": "Parámetro 'categoria' requerido"}
        subs = listar_subcategorias(usuario_id, categoria)
        return {"categoria": categoria, "subcategorias": subs}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/seed-completo")
def api_kebo_seed_completo(usuario_id: str = "default"):
    """Inicializa categorías + sub-categorías predefinidas."""
    try:
        from modules.database import crear_categorias_predefinidas, crear_subcategorias_predefinidas
        cats = crear_categorias_predefinidas(usuario_id)
        subs = crear_subcategorias_predefinidas(usuario_id)
        return {"categorias_creadas": cats, "subcategorias_creadas": subs}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/buscar")
def api_kebo_buscar(usuario_id: str = "default", texto: str = "", categoria: str = "",
                    cuenta: str = "", status: str = "", fecha_desde: str = "",
                    fecha_hasta: str = "", tipo: str = ""):
    """Búsqueda avanzada de transacciones."""
    try:
        from modules.database import buscar_transacciones
        resultados = buscar_transacciones(
            usuario_id,
            texto=texto, categoria=categoria, cuenta=cuenta,
            status=status, fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta, tipo=tipo
        )
        return {"total": len(resultados), "transacciones": resultados}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/futuras")
def api_kebo_futuras(usuario_id: str = "default"):
    """Lista transacciones programadas (futuras)."""
    try:
        from modules.database import listar_transacciones_futuras, ejecutar_transacciones_futuras
        # Ejecutar las que ya tocaron
        ejecutadas = ejecutar_transacciones_futuras(usuario_id)
        futuras = listar_transacciones_futuras(usuario_id)
        return {"ejecutadas": ejecutadas, "pendientes": futuras}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/recordatorios")
def api_kebo_recordatorios(usuario_id: str = "default"):
    """Lista recordatorios del usuario."""
    try:
        from modules.database import listar_recordatorios, obtener_recordatorios_hoy
        return {
            "hoy": obtener_recordatorios_hoy(usuario_id),
            "todos": listar_recordatorios(usuario_id)
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/tasas")
def api_kebo_tasas(usuario_id: str = "default"):
    """Lista tasas de cambio guardadas."""
    try:
        from modules.database import obtener_tasas_cambio, TASAS_DEFAULT
        tasas = obtener_tasas_cambio(usuario_id)
        # Combinar con defaults
        for m, rate in TASAS_DEFAULT.items():
            if m not in tasas:
                tasas[m] = {"rate": rate}
        return {"tasas": tasas}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/balance-multimoneda")
def api_kebo_balance_multimoneda(usuario_id: str = "default", moneda: str = "COP"):
    """Balance total convertido a una moneda específica."""
    try:
        from modules.database import obtener_balance_total_multimoneda
        total = obtener_balance_total_multimoneda(usuario_id, moneda)
        return {"moneda": moneda, "total": total}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/sugerencias")
def api_kebo_sugerencias(usuario_id: str = "default", prefijo: str = ""):
    """Sugerencias de payee y categoría basadas en historial."""
    try:
        from modules.database import obtener_sugerencias_payee, obtener_sugerencias_categoria
        return {
            "payees": obtener_sugerencias_payee(usuario_id, prefijo) if prefijo else [],
            "categorias": obtener_sugerencias_categoria(usuario_id, prefijo) if prefijo else []
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/rollover")
def api_kebo_rollover(usuario_id: str = "default"):
    """Aplica rollover del presupuesto del mes anterior."""
    try:
        from modules.database import aplicar_rollover_presupuesto
        rollovers = aplicar_rollover_presupuesto(usuario_id)
        return {"rollovers_aplicados": rollovers}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/kebo/pronostico")
def api_kebo_pronostico(usuario_id: str = "default"):
    """Pronóstico de gastos para el mes actual basado en historial."""
    try:
        from modules.database import obtener_estadisticas
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
        from modules.database import (
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


# Alias para compatibilidad


@app.get("/api/finanzas/debug")
def api_finanzas_debug(usuario_id: str = "default"):
    """Endpoint debug: muestra 1 muestra de cada coleccion."""
    try:
        from modules.database import inicializar_firebase
        from google.cloud.firestore_v1.base_query import FieldFilter
        db = inicializar_firebase()
        if not db:
            return {"error": "DB no inicializada"}

        # 1 presupuesto
        docs_p = db.collection("presupuestos").where(filter=FieldFilter("usuario_id", "==", usuario_id)).limit(2).stream()
        presupuesto_sample = [d.to_dict() for d in docs_p]

        # 2 finanzas
        docs_f = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", usuario_id)).limit(3).stream()
        finanzas_sample = [d.to_dict() for d in docs_f]

        return {
            "presupuesto_sample": presupuesto_sample,
            "finanzas_sample": finanzas_sample,
            "num_presupuestos": len(presupuesto_sample),
            "num_finanzas": len(finanzas_sample)
        }
    except Exception as e:
        return {"error": str(e)}

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
        from app.services.daily_summary import main as daily_main
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