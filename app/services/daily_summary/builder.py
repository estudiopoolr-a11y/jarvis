"""app/services/daily_summary/builder.py - Construye mensajes para el resumen diario."""

from datetime import datetime
from firebase_admin import firestore

def construir_mensaje(db, hora_actual: datetime, balance, presupuestos, tareas) -> str:
    """Construye el mensaje del resumen."""
    if not balance:
        return "🤖 **JARVIS** | No hay datos registrados aún."

    saludo = "🌅 Buenos días" if hora_actual.hour < 12 else "🌆 Buenas tardes"
    fecha = hora_actual.strftime("%A %d de %B, %Y")
    hora = hora_actual.strftime("%I:%M %p")

    partes = [f"{saludo}, señor. {fecha} - {hora}", ""]

    for uid, data in balance.items():
        ingresos = data["ingresos"]
        gastos = data["gastos"]
        neto = ingresos - gastos

        partes.append(f"💰 **BALANCE GENERAL**")
        partes.append(f"• Ingresos: +${ingresos:,.0f}")
        partes.append(f"• Gastos: -${gastos:,.0f}")
        partes.append(f"• Neto: ${neto:,.0f}")
        partes.append("")

        # Presupuestos
        if uid in presupuestos and presupuestos[uid]:
            partes.append("🎯 **PRESUPUESTOS**")
            for cat, limite in presupuestos[uid].items():
                gasto_cat = 0.0
                try:
                    docs = db.collection("finanzas").where("usuario_id", "==", str(uid)).where("categoria", "==", cat).stream()
                    for d in docs:
                        if d.to_dict().get("tipo") == "gasto":
                            gasto_cat += float(d.to_dict().get("monto", 0))
                except Exception:
                    pass

                pct = (gasto_cat / limite * 100) if limite > 0 else 0
                barra = "█" * int(pct // 10) + "░" * (10 - int(pct // 10))
                estado = "🚨" if pct >= 100 else "⚠️" if pct >= 80 else "✅"
                partes.append(f"{estado} {cat}: {barra} {pct:.0f}% (${gasto_cat:,.0f}/${limite:,.0f})")
            partes.append("")

        # Tareas pendientes
        if uid in tareas and tareas[uid]:
            partes.append(f"📋 **TAREAS PENDIENTES ({len(tareas[uid])})**")
            for t in tareas[uid][:5]:
                prioridad = t.get("prioridad", "Media")
                emoji = "🔴" if prioridad == "Alta" else "🟡" if prioridad == "Media" else "🟢"
                partes.append(f"{emoji} {t.get('tarea')} (Vence: {t.get('fecha_limite', 'Pronto')})")
            if len(tareas[uid]) > 5:
                partes.append(f"  ...y {len(tareas[uid]) - 5} más")
        else:
            partes.append("✅ Sin tareas pendientes.")

        partes.append("")
        partes.append("_Sistemas operativos. JARVIS a la espera de instrucciones._")

    return "\n".join(partes)