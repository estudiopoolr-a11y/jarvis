import os
import sys
from pathlib import Path
from datetime import datetime

from fastapi import File, Form, UploadFile
from fastapi.responses import HTMLResponse

from app.api import USUARIO_PRINCIPAL, ComandoPayload, app
from modules.ai import pensar_respuesta, pensar_respuesta_imagen, procesar_intencion_natural
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos, obtener_tareas_pendientes

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


@app.get("/api/widget/dashboard")
def api_widget_dashboard(usuario_id: str = "iphone_user"):
    """Endpoint único que devuelve TODO lo que necesita el widget iPhone.

    Optimizado para hacer UNA sola llamada HTTP desde el widget.
    Retorna:
        - mes: periodo actual YYYY-MM
        - presupuestos: lista de {categoria, limite, gastado, disponible, pct}
        - total_presupuestado / total_gastado / total_disponible
        - prestamos_pendientes: lista de préstamos por cobrar (status != 'pagado')
        - total_por_cobrar: suma de pendientes
        - balance_general: ingresos - gastos del mes
        - alertas: top categorías excedidas
        - ingresos_gastos: ingresos y gastos por categoría
        - cuentas: lista de cuentas con su balance disponible
        - timestamp: para cache-busting
    """
    import traceback
    from datetime import datetime

    try:
        from modules.db import (
            inicializar_firebase, _get_user_ref,
            obtener_presupuestos_v2, listar_prestamos, obtener_balance_v2
        )

        db = inicializar_firebase()
        if not db:
            return {"error": "Firebase no disponible"}

        now = datetime.now()
        mes_actual = now.strftime("%Y-%m")

        # 1. Presupuestos con gastado del mes
        try:
            presupuestos_raw = obtener_presupuestos_v2(usuario_id, mes_actual)
        except Exception as e:
            presupuestos_raw = {}

        presupuestos_lista = []
        total_presupuestado = 0.0
        total_gastado = 0.0
        total_disponible = 0.0
        alertas = []

        for cat_nombre, info in presupuestos_raw.items():
            limite = float(info.get("limite", 0))
            gastado = float(info.get("gastado", 0))
            disponible = limite - gastado
            pct = (gastado / limite * 100) if limite > 0 else 0

            presupuestos_lista.append({
                "categoria": cat_nombre,
                "limite": limite,
                "gastado": gastado,
                "disponible": disponible,
                "pct": round(pct, 1),
                "excedido": gastado > limite,
            })

            total_presupuestado += limite
            total_gastado += gastado
            total_disponible += disponible

            if gastado > limite:
                alertas.append({
                    "tipo": "excedido",
                    "categoria": cat_nombre,
                    "mensaje": f"Excedido: gastado {gastado:,.0f} de {limite:,.0f}",
                })
            elif pct >= 80:
                alertas.append({
                    "tipo": "alerta",
                    "categoria": cat_nombre,
                    "mensaje": f"Cerca del límite: {pct:.0f}% usado",
                })

        # 2. Préstamos por cobrar (solo pendientes)
        try:
            prestamos = listar_prestamos(usuario_id, solo_pendientes=True)
        except Exception:
            prestamos = []

        prestamos_pendientes = []
        total_por_cobrar = 0.0
        for p in prestamos:
            # Serializar el préstamo para evitar problemas con DatetimeWithNanoseconds
            p_serial = _serializar_valor(p)
            prestamos_pendientes.append(p_serial)
            monto = float(p.get("monto", p.get("monto_pendiente", 0)))
            total_por_cobrar += monto

        # 3. Ingresos y gastos por categoría
        ingresos_gastos = {}
        total_ingresos = 0.0
        total_gastos_categoria = 0.0
        try:
            user_ref = db.collection('users').document(usuario_id)
            transactions_ref = user_ref.collection('transactions').document(mes_actual).collection('items')
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
                    total_gastos_categoria += monto
        except Exception as e:
            traceback.print_exc()

        # 4. Cuentas con balance disponible
        cuentas = []
        total_balance_cuentas = 0.0
        try:
            user_ref = db.collection('users').document(usuario_id)
            accounts_ref = user_ref.collection('accounts')
            accounts = accounts_ref.stream()

            for acc in accounts:
                acc_data = acc.to_dict()
                nombre = acc_data.get('name', 'Cuenta sin nombre')
                balance = float(acc_data.get('balance', 0))
                tipo_cuenta = acc_data.get('type', 'general')
                
                cuentas.append({
                    "nombre": nombre,
                    "balance": balance,
                    "tipo": tipo_cuenta,
                    "disponible": balance  # El balance es el disponible
                })
                total_balance_cuentas += balance
        except Exception as e:
            traceback.print_exc()

        return {
            "mes": mes_actual,
            "presupuestos": presupuestos_lista,
            "total_presupuestado": total_presupuestado,
            "total_gastado": total_gastado,
            "total_disponible": total_disponible,
            "prestamos_pendientes": prestamos_pendientes,
            "total_por_cobrar": total_por_cobrar,
            "balance_general": total_ingresos - total_gastos_categoria,
            "alertas": alertas,
            "ingresos_gastos": ingresos_gastos,
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos_categoria,
            "cuentas": cuentas,
            "total_balance_cuentas": total_balance_cuentas,
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
