import os
import sys
from pathlib import Path
from datetime import datetime

from fastapi import File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi import APIRouter

from app.api import USUARIO_PRINCIPAL, ComandoPayload, app
from modules.ai import pensar_respuesta, pensar_respuesta_imagen, procesar_intencion_natural
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos, obtener_tareas_pendientes

router = APIRouter(prefix="/api/widget")

# ============================================================
# 🆕 WIDGET DASHBOARD — Endpoint único para el widget iPhone
# ============================================================

def _serializar_valor(valor):
    """Convierte valores no serializables (DatetimeWithNanoseconds, etc.) a tipos JSON."""
    if valor is None:
        return None
    # Verificar si es un objeto datetime o similar (Firebase Timestamp)
    if hasattr(valor, 'isoformat'):
        return valor.isoformat()
    # Si es un dict, recursividad
    if isinstance(valor, dict):
        return {k: _serializar_valor(v) for k, v in valor.items()}
    # Si es una lista, recursividad
    if isinstance(valor, list):
        return [_serializar_valor(v) for v in valor]
    return valor


@router.get("/resumen")
async def obtener_resumen_widget():
    """Endpoint simplificado para el Widget de iOS.
    Garantiza una respuesta JSON válida incluso en caso de error.
    """
    try:
        # Reutilizamos la lógica del dashboard para obtener datos reales
        from app.routes.widgets import api_widget_dashboard
        res = await api_widget_dashboard(usuario_id="default")
        return res
    except Exception as e:
        return {
            "status": "error",
            "mensaje": str(e),
            "total_balance_cuentas": 0,
            "cuentas": [],
            "mes": "Error",
            "total_ingresos": 0,
            "total_gastos": 0,
            "presupuestos": []
        }

@router.get("/dashboard")
def api_widget_dashboard(usuario_id: str = ""):

    """Endpoint único que devuelve TODO lo que necesita el widget iPhone.

    Optimizado para hacer UNA sola llamada HTTP desde el widget.
    Retorna:
        - total_balance_cuentas: suma de saldos de cuentas
        - cuentas: lista de objetos {nombre, disponible}
        - mes: nombre del mes y año (ej: "Octubre 2026")
        - total_ingresos: total de ingresos del mes
        - total_gastos: total de gastos del mes
        - presupuestos: lista de objetos {categoria, gastado, limite, excedido}
    """
    import traceback
    from datetime import datetime

    try:
        from modules.db import (
            inicializar_firebase,
            obtener_presupuestos_v2,
            listar_prestamos,
            obtener_balance_v2
        )
        from firebase_admin import firestore

        db = inicializar_firebase()
        if not db:
            return {"error": "Firebase no disponible"}

        now = datetime.now()
        # Formato de mes: "Octubre 2026" en lugar de "2026-10"
        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        mes_nombre = meses[now.month]
        mes_actual = f"{mes_nombre} {now.year}"

        # 1. Presupuestos con gastado del mes (usando usuario_id si se proporciona, sino "default")
        user_id_for_queries = usuario_id if usuario_id else "default"
        try:
            presupuestos_raw = obtener_presupuestos_v2(user_id_for_queries, now.strftime("%Y-%m"))
        except Exception as e:
            presupuestos_raw = {}

        presupuestos_lista = []
        for cat_nombre, info in presupuestos_raw.items():
            limite = float(info.get("limite", 0))
            gastado = float(info.get("gastado", 0))
            disponible = limite - gastado
            excedido = gastado > limite

            presupuestos_lista.append({
                "categoria": cat_nombre,
                "gastado": gastado,
                "limite": limite,
                "excedido": excedido
            })

        # 2. Préstamos por cobrar (solo pendientes)
        try:
            prestamos = listar_prestamos(user_id_for_queries, solo_pendientes=True)
        except Exception:
            prestamos = []

        # 3. Ingresos y gastos por categoría
        # Las transacciones siguen estando en users/{id}/transactions/{mes}/items
        ingresos_gastos = {}
        total_ingresos = 0.0
        total_gastos = 0.0
        try:
            # Si no se proporciona usuario_id, usamos "default" para las transacciones también
            user_ref = db.collection('users').document(user_id_for_queries)
            transactions_ref = user_ref.collection('transactions').document(now.strftime("%Y-%m")).collection('items')
            transactions = transactions_ref.stream()

            for t in transactions:
                data = t.to_dict()
                categoria = data.get('category', 'Sin categoría')
                tipo = data.get('type', 'gasto')
                monto = float(data.get('amount', 0))

                if categoria not in ingresos_gastos:
                    ingresos_gastos[categoria] = {"ingreso": 0, "gasto": 0}

                ingresos_gastos[categoria][tipo] += monto
                
                if tipo == 'ingreso':
                    total_ingresos += monto
                else:
                    total_gastos += monto
        except Exception as e:
            traceback.print_exc()

        # 4. Cuentas con balance disponible - COLECCIÓN RAÍZ SIN FILTRADO POR USUARIO
        cuentas = []
        total_balance_cuentas = 0.0
        try:
            # MIGRACIÓN COMPLETA: Las cuentas están en la colección raíz 'accounts'
            # Ya no filtramos por usuario_id, obtenemos todas las cuentas
            accounts_ref = db.collection('accounts')
            accounts = accounts_ref.stream()

            for acc in accounts:
                acc_data = acc.to_dict()
                # Compatibilidad con ambos formatos: name/nombre y type/tipo
                nombre = acc_data.get('name') or acc_data.get('nombre', 'Cuenta sin nombre')
                balance = float(acc_data.get('balance', 0))
                
                cuentas.append({
                    "nombre": nombre,
                    "disponible": balance
                })
                total_balance_cuentas += balance
        except Exception as e:
            traceback.print_exc()

        # Calculate new fields for widget
        presupuesto_mes = sum(p["limite"] for p in presupuestos_lista)
        porcentaje_usado = (total_gastos / presupuesto_mes * 100) if presupuesto_mes > 0 else 0
        comparativa_texto = f"{porcentaje_usado:.1f}% del límite mes"
        alerta = porcentaje_usado > 85

        return {
            # Original fields for backward compatibility
            "total_balance_cuentas": total_balance_cuentas,
            "cuentas": cuentas,
            "mes": mes_actual,
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "presupuestos": presupuestos_lista,
            # New fields as requested
            "balance_total": total_balance_cuentas,
            "gastos_mes": total_gastos,
            "presupuesto_mes": presupuesto_mes,
            "porcentaje_usado": round(porcentaje_usado, 2),
            "comparativa_texto": comparativa_texto,
            "alerta": alerta,
            "mensaje": "JARVIS Finanzas OK",
            "status": "ok"
        }

    except Exception as e:
        traceback.print_exc()
        # Blindaje defensivo para que el Widget de iOS no colapse
        return {
            "status": "ok",
            "total_balance_cuentas": 0,
            "cuentas": [],
            "mes": "Error",
            "total_ingresos": 0,
            "total_gastos": 0,
            "presupuestos": [],
            "mensaje": "JARVIS Vercel Active (Fallback)"
        }
