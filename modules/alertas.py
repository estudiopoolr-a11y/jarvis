"""
JARVIS Alertas Proactivas - Fase 3
Detecta presupuestos críticos, tareas vencidas y gastos anormales.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from google.cloud.firestore_v1.base_query import FieldFilter

# Zona horaria Colombia
TZ = timezone(timedelta(hours=-5))

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL") or "https://discordapp.com/api/webhooks/1544477914391904406/J4y5ycFy6e-AVHTDoN2-kRh-Su1Dt3ArUAePdOvIFbMTCjAuvKwwrvPqszE1yLeFtmO3"

# Firebase
import firebase_admin
from firebase_admin import credentials, initialize_app, firestore

db = None


def inicializar_firebase():
    """Inicializa Firebase desde variables de entorno o archivo local."""
    global db
    if not firebase_admin._apps:
        firebase_json_str = (
            os.getenv("FIREBASE_CREDENTIALS") or
            os.getenv("FIREBASE_CREDENTIALS_JSON") or
            os.getenv("FIREBASE_KEY") or
            os.getenv("FIREBASE_SERVICE_ACCOUNT")
        )
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")

        if firebase_json_str:
            firebase_json_str = firebase_json_str.strip()
            if (firebase_json_str.startswith("'") and firebase_json_str.endswith("'")) or \
               (firebase_json_str.startswith('"') and firebase_json_str.endswith('"')):
                firebase_json_str = firebase_json_str[1:-1].strip()
            with open(cred_path, "w", encoding="utf-8") as f:
                f.write(firebase_json_str)
            cred = credentials.Certificate(cred_path)
            initialize_app(cred)

        if not firebase_admin._apps and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            initialize_app(cred)

    if firebase_admin._apps:
        db = firestore.client()
    return db


# ============== ALERTAS DE PRESUPUESTO ==============

def obtener_gastos_por_categoria(uid: str) -> dict:
    """Obtiene el total gastado por categoría para un usuario."""
    if not db:
        inicializar_firebase()

    gastos = {}
    try:
        docs = db.collection("finanzas").where(filter=FieldFilter("usuario_id", "==", str(uid))).stream()
        for doc in docs:
            data = doc.to_dict()
            if data.get("tipo") == "gasto":
                cat = data.get("categoria", "General")
                monto = float(data.get("monto", 0))
                gastos[cat] = gastos.get(cat, 0) + monto
    except Exception as e:
        print(f"Error obteniendo gastos por categoría: {e}")

    return gastos


def verificar_presupuestos_criticos(uid: str = "default") -> list:
    """
    Verifica presupuestos que están cerca del límite.
    Retorna lista de alertas con nivel (warning/critical).
    """
    if not db:
        inicializar_firebase()

    alertas = []

    # Obtener presupuestos
    presupuestos = {}
    try:
        docs = db.collection("presupuestos").stream()
        for doc in docs:
            data = doc.to_dict()
            if data.get("usuario_id") == uid:
                cat = data.get("categoria")
                limite = float(data.get("limite", 0))
                if limite > 0:
                    presupuestos[cat] = limite
    except Exception as e:
        print(f"Error leyendo presupuestos: {e}")
        return alertas

    # Obtener gastos reales
    gastos = obtener_gastos_por_categoria(uid)

    # Verificar cada presupuesto
    for cat, limite in presupuestos.items():
        gastado = gastos.get(cat, 0)
        porcentaje = (gastado / limite) * 100 if limite > 0 else 0

        if porcentaje >= 90:
            alertas.append({
                "tipo": "critical",
                "categoria": cat,
                "gastado": gastado,
                "limite": limite,
                "porcentaje": porcentaje,
                "restante": limite - gastado
            })
        elif porcentaje >= 80:
            alertas.append({
                "tipo": "warning",
                "categoria": cat,
                "gastado": gastado,
                "limite": limite,
                "porcentaje": porcentaje,
                "restante": limite - gastado
            })

    return alertas


def verificar_tareas_vencidas(uid: str = "default") -> list:
    """
    Detecta tareas vencidas y próximas a vencer.
    Retorna lista de tareas con su estado.
    """
    if not db:
        inicializar_firebase()

    tareas_vencidas = []
    tareas_proximas = []
    ahora = datetime.now(TZ)

    try:
        docs = db.collection("tareas").where(filter=FieldFilter("completada", "==", False)).stream()
        for doc in docs:
            data = doc.to_dict()
            if data.get("usuario_id") != uid:
                continue

            tarea = data.get("tarea", "Sin nombre")
            prioridad = data.get("prioridad", "Media")
            fecha_limite_str = data.get("fecha_limite", "")

            # Parsear fecha límite
            try:
                fecha_limite = datetime.strptime(fecha_limite_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue  # Saltar si no tiene fecha válida

            dias_restantes = (fecha_limite - ahora).days

            if dias_restantes < 0:
                tareas_vencidas.append({
                    "tarea": tarea,
                    "prioridad": prioridad,
                    "dias_vencida": abs(dias_restantes),
                    "fecha_limite": fecha_limite_str
                })
            elif dias_restantes <= 2:
                tareas_proximas.append({
                    "tarea": tarea,
                    "prioridad": prioridad,
                    "dias_restantes": dias_restantes,
                    "fecha_limite": fecha_limite_str
                })
    except Exception as e:
        print(f"Error leyendo tareas: {e}")

    return {"vencidas": tareas_vencidas, "proximas": tareas_proximas}


def detectar_gastos_anormales(uid: str = "default", umbral_multiplicador: float = 2.0) -> list:
    """
    Detecta gastos que superan significativamente el promedio histórico.
    umbral_multiplicador: múltiplo del promedio para considerar anormal (default: 2x)
    """
    if not db:
        inicializar_firebase()

    alertas = []
    ahora = datetime.now(TZ)

    # Obtener todos los gastos históricos
    historial_gastos = {}
    try:
        docs = db.collection("finanzas").where(filter=FieldFilter("tipo", "==", "gasto")).stream()
        for doc in docs:
            data = doc.to_dict()
            if data.get("usuario_id") != uid:
                continue

            cat = data.get("categoria", "General")
            monto = float(data.get("monto", 0))
            fecha_str = data.get("fecha", "")

            # Intentar parsear fecha
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                # Si no hay fecha, usar fecha actual para simplificar
                fecha = ahora

            if cat not in historial_gastos:
                historial_gastos[cat] = []
            historial_gastos[cat].append({"monto": monto, "fecha": fecha})
    except Exception as e:
        print(f"Error leyendo historial de gastos: {e}")
        return alertas

    # Calcular promedios y detectar anomalías
    for cat, gastos in historial_gastos.items():
        if len(gastos) < 2:
            continue

        montos = [g["monto"] for g in gastos]
        promedio = sum(montos) / len(montos)

        # Obtener el último gasto
        gastos_ordenados = sorted(gastos, key=lambda x: x["fecha"], reverse=True)
        ultimo_gasto = gastos_ordenados[0]

        # Verificar si es anormal
        if ultimo_gasto["monto"] > promedio * umbral_multiplicador:
            alertas.append({
                "categoria": cat,
                "monto_actual": ultimo_gasto["monto"],
                "promedio_historico": promedio,
                "multiplicador": ultimo_gasto["monto"] / promedio if promedio > 0 else 0,
                "fecha": ultimo_gasto["fecha"].strftime("%Y-%m-%d")
            })

    return alertas


def construir_mensaje_alertas() -> str:
    """Construye el mensaje completo de alertas para Discord."""
    if not db:
        inicializar_firebase()

    partes = []
    ahora = datetime.now(TZ)

    # Verificar presupuestos
    alertas_presupuestos = verificar_presupuestos_criticos()

    if alertas_presupuestos:
        partes.append("🚨 **ALERTAS DE PRESUPUESTO**")

        for alerta in alertas_presupuestos:
            emoji = "🔴" if alerta["tipo"] == "critical" else "⚠️"
            nivel = "CRÍTICO" if alerta["tipo"] == "critical" else "ADVERTENCIA"
            partes.append(f"{emoji} **{alerta['categoria']}** ({nivel})")
            partes.append(f"   Gastado: ${alerta['gastado']:,.0f} / ${alerta['limite']:,.0f} ({alerta['porcentaje']:.0f}%)")
            partes.append(f"   Remaining: ${max(0, alerta['restante']):,.0f}")
        partes.append("")

    # Verificar tareas
    tareas = verificar_tareas_vencidas()

    if tareas["vencidas"]:
        partes.append("⏰ **TAREAS VENCIDAS**")
        for t in tareas["vencidas"]:
            emoji = "🔴" if t["prioridad"] == "Alta" else "🟡"
            partes.append(f"{emoji} **{t['tarea']}** - Vencida hace {t['dias_vencida']} día(s)")
            partes.append(f"   📅 Fecha límite: {t['fecha_limite']}")
        partes.append("")

    if tareas["proximas"]:
        partes.append("📅 **TAREAS PRÓXIMAS A VENCER**")
        for t in tareas["proximas"]:
            dias = "hoy" if t["dias_restantes"] == 0 else f"{t['dias_restantes']} día(s)"
            emoji = "🔴" if t["prioridad"] == "Alta" else "🟡"
            partes.append(f"{emoji} **{t['tarea']}** - Vence {dias}")
        partes.append("")

    # Verificar gastos anormales
    gastos_anormales = detectar_gastos_anormales()

    if gastos_anormales:
        partes.append("💸 **GASTOS ANORMALES DETECTADOS**")
        for g in gastos_anormales:
            partes.append(f"⚠️ **{g['categoria']}**")
            partes.append(f"   Último: ${g['monto_actual']:,.0f} (promedio: ${g['promedio_historico']:,.0f})")
            partes.append(f"   Multiplicador: {g['multiplicador']:.1f}x del promedio")
        partes.append("")

    if not partes:
        return ""  # Sin alertas

    return "\n".join(partes)


def enviar_alerta_discord(mensaje: str) -> bool:
    """Envía alerta a Discord via webhook."""
    if not mensaje:
        return False

    payload = {
        "content": f"🚨 **ALERTAS JARVIS** | {datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}\n\n{mensaje}",
        "username": "JARVIS Alerts",
        "avatar_url": None
    }

    try:
        import requests
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 204:
            print(f"✅ Alerta enviada a las {datetime.now(TZ).strftime('%H:%M')}")
            return True
        else:
            print(f"⚠️ Error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Error enviando alerta: {e}")
        return False


def verificar_y_enviar_alertas() -> dict:
    """
    Función principal: verifica todas las alertas y envía si hay novedades.
    Retorna estadísticas de lo verificado.
    """
    if not db:
        inicializar_firebase()

    if not db:
        return {"status": "error", "message": "No se pudo conectar a Firebase"}

    # Verificar cada tipo de alerta
    alertas_presupuestos = verificar_presupuestos_criticos()
    tareas = verificar_tareas_vencidas()
    gastos_anormales = detectar_gastos_anormales()

    # Construir mensaje solo si hay alertas
    mensaje = construir_mensaje_alertas()

    if mensaje:
        enviar_alerta_discord(mensaje)
        return {
            "status": "ok",
            "message": "Alertas enviadas",
            "presupuestos_criticos": len(alertas_presupuestos),
            "tareas_vencidas": len(tareas["vencidas"]),
            "tareas_proximas": len(tareas["proximas"]),
            "gastos_anormales": len(gastos_anormales)
        }
    else:
        return {
            "status": "ok",
            "message": "Sin alertas pendientes",
            "presupuestos_criticos": 0,
            "tareas_vencidas": 0,
            "tareas_proximas": 0,
            "gastos_anormales": 0
        }


# ============== RESUMEN SEMANAL ==============

def obtener_resumen_semanal(uid: str = "default") -> dict:
    """
    Genera un resumen de la semana: ingresos, gastos, variación vs semana anterior.
    """
    if not db:
        inicializar_firebase()

    ahora = datetime.now(TZ)
    hace_7_dias = ahora - timedelta(days=7)
    hace_14_dias = ahora - timedelta(days=14)

    resumen = {
        "semana_actual": {"ingresos": 0, "gastos": 0, "transacciones": 0},
        "semana_anterior": {"ingresos": 0, "gastos": 0, "transacciones": 0},
        "por_categoria": {},
        "tareas_completadas": 0,
        "tareas_pendientes": 0
    }

    # Obtener transacciones de las últimas 2 semanas
    try:
        docs = db.collection("finanzas").stream()
        for doc in docs:
            data = doc.to_dict()
            if data.get("usuario_id") != uid:
                continue

            fecha_str = data.get("fecha", "")
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            monto = float(data.get("monto", 0))
            tipo = data.get("tipo", "")
            cat = data.get("categoria", "General")

            if hace_14_dias <= fecha <= hace_7_dias:
                # Semana anterior
                if tipo == "ingreso":
                    resumen["semana_anterior"]["ingresos"] += monto
                elif tipo == "gasto":
                    resumen["semana_anterior"]["gastos"] += monto
                resumen["semana_anterior"]["transacciones"] += 1

            elif hace_7_dias <= fecha <= ahora:
                # Semana actual
                if tipo == "ingreso":
                    resumen["semana_actual"]["ingresos"] += monto
                elif tipo == "gasto":
                    resumen["semana_actual"]["gastos"] += monto
                resumen["semana_actual"]["transacciones"] += 1

                # Por categoría
                if cat not in resumen["por_categoria"]:
                    resumen["por_categoria"][cat] = 0
                if tipo == "gasto":
                    resumen["por_categoria"][cat] += monto
    except Exception as e:
        print(f"Error obteniendo resumen semanal: {e}")

    # Obtener tareas
    try:
        docs = db.collection("tareas").where(filter=FieldFilter("completada", "==", False)).stream()
        resumen["tareas_pendientes"] = sum(1 for _ in docs)
    except Exception:
        pass

    return resumen


def construir_mensaje_semanal() -> str:
    """Construye el mensaje de resumen semanal para Discord."""
    resumen = obtener_resumen_semanal()
    ahora = datetime.now(TZ)

    # Calcular variaciones
    ingresos_var = resumen["semana_actual"]["ingresos"] - resumen["semana_anterior"]["ingresos"]
    gastos_var = resumen["semana_actual"]["gastos"] - resumen["semana_anterior"]["gastos"]

    # Porcentajes de variación
    ing_pct = (ingresos_var / resumen["semana_anterior"]["ingresos"] * 100) if resumen["semana_anterior"]["ingresos"] > 0 else 0
    gas_pct = (gastos_var / resumen["semana_anterior"]["gastos"] * 100) if resumen["semana_anterior"]["gastos"] > 0 else 0

    partes = [
        f"📊 **RESUMEN SEMANAL** | {ahora.strftime('%d %B %Y')}",
        "",
        "**💰 FINANZAS**",
        f"• Ingresos: ${resumen['semana_actual']['ingresos']:,.0f} ({'+' if ingresos_var >= 0 else ''}{ing_pct:.0f}% vs semana pasada)",
        f"• Gastos: ${resumen['semana_actual']['gastos']:,.0f} ({'+' if gastos_var >= 0 else ''}{gas_pct:.0f}% vs semana pasada)",
        f"• Balance: ${resumen['semana_actual']['ingresos'] - resumen['semana_actual']['gastos']:,.0f}",
        "",
        "**📈 GASTOS POR CATEGORÍA**",
    ]

    # Ordenar por monto
    categorias = sorted(resumen["por_categoria"].items(), key=lambda x: x[1], reverse=True)
    for cat, monto in categorias[:5]:
        partes.append(f"• {cat}: ${monto:,.0f}")

    partes.extend([
        "",
        f"**📋 TAREAS** ({resumen['tareas_pendientes']} pendientes)",
        f"• Transacciones registradas: {resumen['semana_actual']['transacciones']}",
        "",
        "_JARVIS - Análisis automático semanal_"
    ])

    return "\n".join(partes)


def enviar_resumen_semanal_discord() -> bool:
    """Envía el resumen semanal a Discord."""
    mensaje = construir_mensaje_semanal()

    payload = {
        "content": mensaje,
        "username": "JARVIS Weekly",
        "avatar_url": None
    }

    try:
        import requests
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 204:
            print(f"✅ Resumen semanal enviado")
            return True
        else:
            print(f"⚠️ Error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Error enviando resumen semanal: {e}")
        return False


if __name__ == "__main__":
    # Prueba local
    inicializar_firebase()
    resultado = verificar_y_enviar_alertas()
    print(f"Resultado: {resultado}")
