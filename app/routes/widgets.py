import os
import sys
from pathlib import Path

from fastapi import File, Form, UploadFile
from fastapi.responses import HTMLResponse

from app.api import USUARIO_PRINCIPAL, ComandoPayload, app
from modules.ai import pensar_respuesta, pensar_respuesta_imagen, procesar_intencion_natural
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos, obtener_tareas_pendientes

# ============================================================
# 🆕 WIDGET DASHBOARD — Endpoint único para el widget iPhone
# ============================================================

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
            monto = float(p.get("monto", p.get("monto_pendiente", 0)))
            pendiente = float(p.get("monto_pendiente", monto))
            prestamos_pendientes.append({
                "persona": p.get("persona", ""),
                "monto": monto,
                "pendiente": pendiente,
                "fecha": p.get("fecha", ""),
                "nota": p.get("nota", ""),
                "status": p.get("status", "pendiente"),
            })
            total_por_cobrar += pendiente

        # 3. Balance general del mes
        try:
            balance, ingresos, gastos, _ = obtener_balance_v2(usuario_id, mes_actual)
        except Exception:
            balance = ingresos = gastos = 0.0

        # 4. Categorías excedidas (top 3)
        excedidas = sorted(
            [p for p in presupuestos_lista if p["excedido"]],
            key=lambda x: x["gastado"] - x["limite"],
            reverse=True,
        )[:3]

        return {
            "ok": True,
            "mes": mes_actual,
            "timestamp": now.isoformat(),
            "presupuestos": presupuestos_lista,
            "total_presupuestado": round(total_presupuestado, 2),
            "total_gastado": round(total_gastado, 2),
            "total_disponible": round(total_disponible, 2),
            "prestamos_pendientes": prestamos_pendientes,
            "total_por_cobrar": round(total_por_cobrar, 2),
            "balance_general": {
                "balance": round(balance, 2),
                "ingresos": round(ingresos, 2),
                "gastos": round(gastos, 2),
            },
            "alertas": alertas,
            "excedidas": [{"categoria": e["categoria"], "exceso": e["gastado"] - e["limite"]} for e in excedidas],
        }
    except Exception as e:
        import traceback
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()[-500:]}


# ============================================================
# 🆕 QUERY SHORTCUTS — Endpoints pre-definidos para Jarvis
# (Sin necesidad de llamar a Gemini)
# ============================================================

@app.get("/api/query/resumen")
def api_query_resumen(usuario_id: str = "iphone_user", mes: str = None):
    """Resumen rápido del mes: balance + total presupuestado/gastado."""
    try:
        from datetime import datetime
        from modules.db import (
            inicializar_firebase, obtener_balance_v2, obtener_presupuestos_v2
        )
        inicializar_firebase()
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        balance, ingresos, gastos, _ = obtener_balance_v2(usuario_id, mes)
        presupuestos = obtener_presupuestos_v2(usuario_id, mes)
        total_limite = sum(p.get("limite", 0) for p in presupuestos.values())
        total_gastado = sum(p.get("gastado", 0) for p in presupuestos.values())
        return {
            "ok": True, "mes": mes,
            "balance": round(balance, 2),
            "ingresos": round(ingresos, 2),
            "gastos": round(gastos, 2),
            "presupuestado": round(total_limite, 2),
            "gastado_presupuestos": round(total_gastado, 2),
            "disponible_presupuestos": round(total_limite - total_gastado, 2),
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/query/categoria")
def api_query_categoria(usuario_id: str = "iphone_user", nombre: str = None, mes: str = None):
    """Detalle de UNA categoría: presupuesto vs gastado en el mes."""
    try:
        from datetime import datetime
        from modules.db import inicializar_firebase, obtener_presupuestos_v2
        inicializar_firebase()
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        if not nombre:
            return {"error": True, "message": "Parámetro 'nombre' requerido"}
        presupuestos = obtener_presupuestos_v2(usuario_id, mes)
        # Búsqueda flexible
        info = None
        nombre_lower = nombre.lower().strip()
        for cat_nombre, cat_info in presupuestos.items():
            if cat_nombre.lower() == nombre_lower or nombre_lower in cat_nombre.lower():
                info = cat_info
                nombre_real = cat_nombre
                break
        if not info:
            return {"ok": True, "encontrada": False, "categoria": nombre, "mes": mes}
        limite = float(info.get("limite", 0))
        gastado = float(info.get("gastado", 0))
        return {
            "ok": True, "encontrada": True,
            "categoria": nombre_real,
            "mes": mes,
            "limite": limite,
            "gastado": gastado,
            "disponible": round(limite - gastado, 2),
            "pct_usado": round((gastado / limite * 100) if limite > 0 else 0, 1),
            "excedido": gastado > limite,
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/query/prestamos")
def api_query_prestamos(usuario_id: str = "iphone_user", solo_pendientes: bool = True):
    """Lista préstamos. Por defecto solo pendientes."""
    try:
        from modules.db import inicializar_firebase, listar_prestamos
        inicializar_firebase()
        prestamos = listar_prestamos(usuario_id, solo_pendientes=solo_pendientes)
        total = sum(float(p.get("monto_pendiente", p.get("monto", 0))) for p in prestamos)
        return {
            "ok": True,
            "cantidad": len(prestamos),
            "total_pendiente": round(total, 2),
            "prestamos": [
                {
                    "persona": p.get("persona", ""),
                    "monto": p.get("monto", 0),
                    "pendiente": p.get("monto_pendiente", p.get("monto", 0)),
                    "fecha": p.get("fecha", ""),
                    "status": p.get("status", "pendiente"),
                } for p in prestamos
            ],
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/query/balance")
def api_query_balance(usuario_id: str = "iphone_user", mes: str = None):
    """Balance total: ingresos - gastos del mes."""
    try:
        from datetime import datetime
        from modules.db import inicializar_firebase, obtener_balance_v2
        inicializar_firebase()
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        balance, ingresos, gastos, _ = obtener_balance_v2(usuario_id, mes)
        return {
            "ok": True, "mes": mes,
            "balance": round(balance, 2),
            "ingresos": round(ingresos, 2),
            "gastos": round(gastos, 2),
            "ahorrado": round(balance, 2),
            "interpretacion": (
                "Ahorraste este mes" if balance > 0
                else "Gastaste más de lo que ingresaste" if balance < 0
                else "Ingresos = Gastos"
            ),
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/query/excedidas")
def api_query_excedidas(usuario_id: str = "iphone_user", mes: str = None):
    """Categorías que se excedieron del presupuesto."""
    try:
        from datetime import datetime
        from modules.db import inicializar_firebase, obtener_presupuestos_v2
        inicializar_firebase()
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        presupuestos = obtener_presupuestos_v2(usuario_id, mes)
        excedidas = []
        for cat, info in presupuestos.items():
            limite = float(info.get("limite", 0))
            gastado = float(info.get("gastado", 0))
            if gastado > limite and limite > 0:
                excedidas.append({
                    "categoria": cat,
                    "limite": limite,
                    "gastado": gastado,
                    "exceso": round(gastado - limite, 2),
                    "pct_exceso": round((gastado / limite - 1) * 100, 1),
                })
        excedidas.sort(key=lambda x: x["exceso"], reverse=True)
        return {
            "ok": True, "mes": mes,
            "cantidad": len(excedidas),
            "total_exceso": round(sum(e["exceso"] for e in excedidas), 2),
            "excedidas": excedidas,
        }
    except Exception as e:
        return {"error": True, "message": str(e)}


@app.get("/api/query/transacciones")
def api_query_transacciones(usuario_id: str = "iphone_user", mes: str = None, limite: int = 20):
    """Últimas N transacciones del mes."""
    try:
        from datetime import datetime
        from modules.db import inicializar_firebase, _get_user_ref
        db = inicializar_firebase()
        _, user_ref = _get_user_ref(usuario_id)
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        items = user_ref.collection("transactions").document(mes).collection("items")
        docs = list(items.stream())
        resultado = []
        for d in docs:
            data = d.to_dict()
            data["_id"] = d.id
            resultado.append(data)
        # Más recientes primero
        resultado.sort(key=lambda x: x.get("date", ""), reverse=True)
        return {
            "ok": True, "mes": mes,
            "total": len(resultado),
            "transacciones": resultado[:limite],
        }
    except Exception as e:
        return {"error": True, "message": str(e)}

