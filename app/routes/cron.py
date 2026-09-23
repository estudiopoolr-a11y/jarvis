import os
import sys
from pathlib import Path

from fastapi import File, Form, UploadFile
from fastapi.responses import HTMLResponse

from app.api import USUARIO_PRINCIPAL, ComandoPayload, app
from modules.ai import pensar_respuesta, pensar_respuesta_imagen, procesar_intencion_natural
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos, obtener_tareas_pendientes

@app.get("/api/cron/recurrentes")
def cron_ejecutar_recurrentes():
    """Cron diario: ejecuta recurrentes que tocan hoy."""
    try:
        from modules.db import ejecutar_recurrentes
        ejecutados = ejecutar_recurrentes(USUARIO_PRINCIPAL)
        return {"status": "ok", "ejecutados": ejecutados}
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/cron/monthly-report")
def cron_monthly_report():
    """Cron mensual: envía reporte del mes anterior a Discord."""
    try:
        from app.services.monthly_report import generar_reporte_mes_anterior, enviar_a_discord
        datos = generar_reporte_mes_anterior(USUARIO_PRINCIPAL)
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
        pagos = obtener_pagos_hoy(USUARIO_PRINCIPAL)
        recordatorios = obtener_recordatorios_personalizados(USUARIO_PRINCIPAL)
        ok = enviar_recordatorio_discord(pagos, recordatorios)
        return {"status": "ok" if ok else "no_data", "pagos": len(pagos), "recordatorios": len(recordatorios)}
    except Exception as e:
        return {"error": True, "message": str(e)}

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

