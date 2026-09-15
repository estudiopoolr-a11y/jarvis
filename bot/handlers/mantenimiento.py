"""Handlers de comandos Discord de JARVIS."""
from datetime import datetime, timedelta

import discord
import firebase_admin
from google.cloud.firestore_v1.base_query import FieldFilter

from bot import bot
from bot.state import (
    usuarios_silenciados,
    usuarios_modo_voz,
    canales_activos,
    conversaciones_activas,
)
from bot.services.ai import (
    pensar_respuesta,
    pensar_respuesta_audio,
    procesar_intencion_natural,
    analizar_inversion,
    transcribir_audio,
    _API_KEYS,
    _key_index,
)
from bot.services.db import *  # noqa: F403,F401

@bot.command(name="diagnostico")
async def diagnostico(ctx):
    """Diagnóstico de lectura Kebo del usuario (para depurar ¿por qué $0?)."""
    try:
        from bot.services.db import _get_user_ref, inicializar_firebase, obtener_balance_financiero
        if not firebase_admin._apps:
            inicializar_firebase()
        uid = str(ctx.author.id)
        _, user_ref = _get_user_ref(uid)
        partes = [f"🔎 **Diagnóstico para `{uid}`**"]
        if not user_ref:
            partes.append("⚠️ user_ref vacío")
            await ctx.send("\n".join(partes))
            return

        # 1) ¿Existe el doc de usuario?
        try:
            udoc = user_ref.get()
            partes.append(f"• Doc usuario existe: {udoc.exists}")
        except Exception as e:
            partes.append(f"• Error get usuario: {e}")

        # 2) Listar meses de transactions
        try:
            meses = [d.id for d in user_ref.collection("transactions").stream()]
            partes.append(f"• Meses en transactions: {meses}")
        except Exception as e:
            partes.append(f"• Error listando transactions: {e}")

        # 3) Contar items en julio
        try:
            items = list(user_ref.collection("transactions").document("2026-07").collection("items").stream())
            partes.append(f"• Items en 2026-07: {len(items)}")
            if items:
                t0 = items[0].to_dict() or {}
                partes.append(f"• Primer item keys: {list(t0.keys())}")
                partes.append(f"• type={t0.get('type')} amount={t0.get('amount')} date={t0.get('date')}")
        except Exception as e:
            partes.append(f"• Error items 2026-07: {e}")

        # 4) Qué retorna obtener_balance_financiero
        try:
            balance = obtener_balance_financiero(uid)
            partes.append(f"• obtener_balance_financiero → {balance[:3]}, #{len(balance[3])} mov")
        except Exception as e:
            partes.append(f"• Error obtener_balance_financiero: {e}")

        await ctx.send("\n".join(partes))
    except Exception as e:
        await ctx.send(f"⚠️ Error en diagnostico: {e}")

@bot.command(name="buscar_historial")
async def buscar_historial(ctx):
    """Recorre todos los usuarios y reporta dónde hay transacciones/budgets por mes."""
    try:
        from bot.services.db import inicializar_firebase, db
        if not firebase_admin._apps:
            inicializar_firebase()

        lineas = []
        usuarios = list(db.collection("users").stream())
        lineas.append(f"🔎 **{len(usuarios)} usuarios encontrados**")

        # Meses de interés (mayo-agosto 2026) probados de forma directa,
        # porque listar la subcolección transactions NO devuelve docs implícitos.
        fechas_probar = ["2026-08", "2026-07", "2026-06", "2026-05", "2026-04"]

        for udoc in usuarios:
            uid = udoc.id
            ref = db.collection("users").document(uid)
            meses_tx = []
            suma_tx = 0
            for mi in fechas_probar:
                try:
                    items = list(ref.collection("transactions").document(mi).collection("items").stream())
                    if items:
                        meses_tx.append(f"{mi}({len(items)})")
                        suma_tx += len(items)
                except Exception:
                    pass
            meses_bud = []
            for mi in fechas_probar:
                try:
                    boutems = list(ref.collection("budgets").document(mi).collection("items").stream())
                    if boutems:
                        meses_bud.append(f"{mi}({len(boutems)})")
                except Exception:
                    pass

            etiqueta = "**← TU CUENTA**" if uid == str(ctx.author.id) else ""
            lineas.append(
                f"\n📁 **{uid}** {etiqueta}\n"
                f"   • transactions KEBO: {meses_tx or 'ninguno'}  (total {suma_tx})\n"
                f"   • budgets KEBO: {meses_bud or 'ninguno'}"
            )

        # ---- LEGACY: finanzas/ y presupuestos/ ----
        try:
            leg_fin = {}
            for d in db.collection("finanzas").stream():
                t = d.to_dict() or {}
                k = str(t.get("usuario_id", "?"))
                mes = t.get("mes", "?")
                leg_fin.setdefault(k, {}).setdefault(mes, 0)
                leg_fin[k][mes] += 1
            lineas.append("\n🗄️ **Legacy `finanzas/`** (movimientos por usuario y mes):")
            if not leg_fin:
                lineas.append("   vacío")
            for k, meses in leg_fin.items():
                desglose = ", ".join(f"{m}: {n}" for m, n in meses.items())
                mk = "**← TU CUENTA**" if k == str(ctx.author.id) else ""
                lineas.append(f"   • `{k}` {mk} → {desglose}")
        except Exception as e:
            lineas.append(f"   ⚠️ Error finanzas legacy: {e}")

        try:
            leg_pres = {}
            for d in db.collection("presupuestos").stream():
                p = d.to_dict() or {}
                k = str(p.get("usuario_id", "?"))
                leg_pres[k] = leg_pres.get(k, 0) + 1
            lineas.append("\n🗄️ **Legacy `presupuestos/`** (por usuario):")
            if not leg_pres:
                lineas.append("   vacío")
            for k, n in leg_pres.items():
                mk = "**← TU CUENTA**" if k == str(ctx.author.id) else ""
                lineas.append(f"   • `{k}` {mk} → {n} presupuestos")
        except Exception as e:
            lineas.append(f"   ⚠️ Error presupuestos legacy: {e}")

        await ctx.send("\n".join(lineas))
    except Exception as e:
        await ctx.send(f"⚠️ Error en buscar_historial: {e}")

@bot.command(name="corregir_gastos")
async def corregir_gastos(ctx, arg: str = ""):
    """Muestra/elimina gastos duplicados de julio 2026.
    Uso: !corregir_gastos          → vista previa (no borra)
         !corregir_gastos confirmar → borra los duplicados
    """
    try:
        from bot.services.db import deduplicar_gastos, inicializar_firebase
        if not firebase_admin._apps:
            inicializar_firebase()
        uid = str(ctx.author.id)
        dry_run = arg.strip().lower() != "confirmar"
        reporte = deduplicar_gastos(uid, 2026, 7, dry_run=dry_run)
        await ctx.send(reporte)
    except Exception as e:
        await ctx.send(f"⚠️ Error en corregir_gastos: {e}")

@bot.command(name="migrar_finanzas")
async def migrar_finanzas(ctx, arg: str = ""):
    """Migra finanzas/presupuestos legacy → Kebo (tu cuenta) y borra legacy.
    Uso: !migrar_finanzas            → vista previa (no migra ni borra)
         !migrar_finanzas confirmar  → migra y deja solo Kebo
    """
    try:
        from bot.services import db as dbmod
        if not firebase_admin._apps:
            dbmod.inicializar_firebase()
        db = dbmod.db if dbmod.db else dbmod.inicializar_firebase()
        uid = str(ctx.author.id)
        confirmar = arg.strip().lower() == "confirmar"

        # ---------- Leer legacy ----------
        finanzas = {}
        for d in db.collection("finanzas").stream():
            t = d.to_dict() or {}
            # solo movimientos del usuario (o los que no tienen usuario = suyos)
            t_uid = str(t.get("usuario_id", ""))
            if t_uid and t_uid not in (uid, "default"):
                continue
            mes = t.get("mes") or ""
            finanzas.setdefault(mes, []).append(t)

        presupuestos = {p.get("categoria", "?").capitalize(): float(p.get("limite", 0))
                        for p in db.collection("presupuestos").stream()
                        if not p.to_dict().get("usuario_id") or str(p.to_dict().get("usuario_id")) in (uid, "default")}

        # ---------- Resumen ----------
        total_ing = sum(t.get("monto", 0) for ms in finanzas.values() for t in ms
                        if str(t.get("tipo")).lower().startswith("ing"))
        total_gas = sum(t.get("monto", 0) for ms in finanzas.values() for t in ms
                        if str(t.get("tipo")).lower().startswith("gas"))

        lineas = [f"🗄️ **LEGACY — finanzas/ y presupuestos/**"]
        if not finanzas and not presupuestos:
            lineas.append("\n✅ No hay data legacy de finanzas que migrar.")
        else:
            lineas.append(f"\n📈 **finanzas/** por mes:")
            for mes in sorted(finanzas):
                movs = finanzas[mes]
                lineas.append(f"   `{mes or 'sin-mes'}` → {len(movs)} movs")
            lineas.append(f"\n   • Ingresos legacy: +${total_ing:,.2f}")
            lineas.append(f"   • Gastos legacy:   -${total_gas:,.2f}")
            if presupuestos:
                lineas.append(f"\n📑 **presupuestos/** legacy ({len(presupuestos)}):")
                for cat, m in presupuestos.items():
                    lineas.append(f"   • {cat}: ${m:,.0f}")

            # Detección de julio duplicado: cuánto hay en legacy de 2026-07
            jul_legacy = finanzas.get("2026-07") or []
            lineas.append(f"\n⚠️ **Julio en legacy**: {len(jul_legacy)} movs "
                          f"(vs {len(list(db.collection('users').document(uid).collection('transactions').document('2026-07').collection('items').stream()))} en Kebo)")

        if confirmar:
            if not finanzas and not presupuestos:
                await ctx.send("\n".join(lineas) + "\n\nNada que migrar.")
                return
            # ---------- Migrar finanzas legacy → Kebo ----------
            mig_s = mig_g = 0
            for mes, movs in finanzas.items():
                if not mes:
                    continue
                year, month = mes.split("-")
                for t in movs:
                    tipo = str(t.get("tipo")).lower()
                    tipo_k = "income" if tipo.startswith("ing") else "expense"
                    cat = str(t.get("categoria")).capitalize()
                    monto = float(t.get("monto", 0))
                    fecha = f"{int(year):04d}-{int(month):02d}-15"
                    try:
                        dbmod.registrar_transaccion_v2(
                            uid, tipo_k, monto, cat,
                            descripcion=str(t.get("descripcion", "")),
                            cuenta_nombre="Efectivo",
                            fecha=fecha,
                        )
                        if tipo_k == "income":
                            mig_s += 1
                        else:
                            mig_g += 1
                    except Exception as e:
                        await ctx.send(f"⚠️ No migré {cat} ${monto}: {e}")
            # ---------- Migrar presupuestos legacy → Kebo ----------
            # sin mes conocido: al mes más reciente con actividad
            meses_orden = sorted([m for m in finanzas if m], reverse=True)
            for cat, monto in presupuestos.items():
                y_m = None
                # si ya hay un presupuesto de esa cat en julio, no lo piso
                if y_m is None and meses_orden:
                    y_m = meses_orden[0]
                if not y_m:
                    continue
                year, month = y_m.split("-")
                try:
                    dbmod.establecer_presupuesto_mes(uid, cat, monto,
                                                     year=int(year), month=int(month))
                except Exception as e:
                    await ctx.send(f"⚠️ No migré presupuesto {cat}: {e}")
            lineas.append(f"\n🚀 **Migrado a Kebo**: {mig_s} ingresos + {mig_g} gastos + "
                          f"{len(presupuestos)} presupuestos")
            # ---------- Borrar legacy ----------
            n_fin = sum(len(v) for v in finanzas.values())
            try:
                for d in db.collection("finanzas").stream():
                    d.reference.delete()
                for d in db.collection("presupuestos").stream():
                    d.reference.delete()
                lineas.append(f"\n🗑️ **Legacy borrado**: {n_fin} finanzas + {len(presupuestos)} presupuestos. "
                              f"Solo queda KEBO.")
            except Exception as e:
                lineas.append(f"\n⚠️ Migrado pero no pude borrar legacy: {e}")
        else:
            lineas.append("\n\nℹ️ Vista previa — nada migrado ni borrado.")
            lineas.append("Para migrar y dejar solo Kebo: `!migrar_finanzas confirmar`")

        await ctx.send("\n".join(lineas))
    except Exception as e:
        await ctx.send(f"⚠️ Error en migrar_finanzas: {e}")

@bot.command(name="consolidar")
async def consolidar(ctx, *, arg: str = ""):
    """Consolida finanzas KEBO de 'default' → tu cuenta.
    Uso:
      !consolidar                      → muestra julio (default vs tuyo) lado a lado
      !consolidar mostrar              → re-muestra julio comparado
      !consolidar copiar may,jun,ago   → copia esos meses de default a tu cuenta
      !consolidar copiar todo          → copia todos los meses EXCEPTO julio
      !consolidar copiar julio         → copia también julio (tras revisar)
    """
    try:
        from bot.services import db as dbmod
        if not firebase_admin._apps:
            dbmod.inicializar_firebase()
        db = dbmod.db if dbmod.db else dbmod.inicializar_firebase()
        uid = str(ctx.author.id)
        ORIGEN = "default"
        MESES = ["2026-05", "2026-06", "2026-07", "2026-08"]

        def leer_items(user_id, mes):
            out = []
            base = db.collection("users").document(user_id).collection("transactions").document(mes).collection("items")
            try:
                for d in base.stream():
                    it = d.to_dict() or {}
                    it["_id"] = d.id
                    it["_mes"] = mes
                    out.append(it)
            except Exception:
                pass
            return out

        def desc(item):
            tipo = item.get("type", "expense")
            m = float(item.get("amount", item.get("monto", 0)))
            signo = "+" if tipo == "income" else "-"
            emoji = "🟢" if tipo == "income" else "🔴"
            cat = str(item.get("category_name") or item.get("categoria") or item.get("category_id") or "?")
            d = item.get("date", "") or item.get("_mes")
            return f"{emoji} {signo}${m:,.0f} · {cat} · {d[:10]}"

        accion = arg.strip().lower()

        # ---------- Ver julio comparado ----------
        if not accion or accion == "mostrar":
            jul_def = leer_items(ORIGEN, "2026-07")
            jul_uid = leer_items(uid, "2026-07")
            lineas = [f"🔁 **JULIO comparado** — `default` ({len(jul_def)}) vs TU cuenta ({len(jul_uid)})\n"]
            lineas.append(f"**En `default` (importado):**")
            lineas += [f"   {desc(x)}" for x in jul_def] or ["   (nada)"]
            lineas.append(f"\n**En TU cuenta (del bloque):**")
            lineas += [f"   {desc(x)}" for x in jul_uid] or ["   (nada)"]
            total_def = sum(float(x.get("amount", x.get("monto", 0))) for x in jul_def if x.get("type") != "income")
            lineas.append(f"\nℹ️ Subtotal gasto julio `default`: -${total_def:,.0f}. "
                          f"Cuando lo revises: `!consolidar copiar todo` (excluye julio) o `!consolidar copiar julio`.")
            await ctx.send("\n".join(lineas))
            return

        # ---------- Copiar meses ----------
        if accion.startswith("copiar"):
            resto = accion.replace("copiar", "").strip().lower()
            if resto in ("todo", "all", ""):
                meses = [m for m in MESES if m != "2026-07"]
            else:
                pedido = [p.strip() for p in resto.replace(" ", "").split(",") if p.strip()]
                meses = []
                for m in MESES:
                    partes = m.split("-")
                    y = partes[0]
                    num = str(int(partes[1]))
                    if num in pedido or y in pedido or m in pedido or m.replace("-", "") in pedido:
                        meses.append(m)
                if "julio" in resto or "jul" in resto or "7" in pedido:
                    meses.append("2026-07")

            if not meses:
                await ctx.send("ℹ️ No se copió nada. Meses válidos: may, jun, jul, ago.")
                return

            # Resolver categoría: default items guardan category_name? si no, por category_id
            # -> usar registrar_transaccion_v2 (resuelve/crea categoría y cuenta bajo el uid)
            copiadas = migradas_ing = migradas_gas = 0
            duplicadas = []
            for mes in meses:
                items = leer_items(ORIGEN, mes)
                for it in items:
                    tipo = it.get("type", "expense")
                    monto = abs(float(it.get("amount", it.get("monto", 0))))
                    fecha = it.get("date", "")
                    descripcion = it.get("description", "")
                    # nombre de categoría: si hay category_name usar; si no, intentar por category_id
                    cat = it.get("category_name") or None
                    if not cat and it.get("category_id"):
                        try:
                            cid = db.collection("users").document(ORIGEN).collection("categories").document(str(it["category_id"])).get()
                            if cid.exists:
                                cat = cid.to_dict().get("nombre", it["category_id"])
                        except Exception:
                            cat = None
                    if not cat:
                        cat = it.get("category_id") or "General"

                    try:
                        dbmod.registrar_transaccion_v2(
                            uid, tipo, monto, str(cat).capitalize(),
                            descripcion=descripcion or f"Importado {mes}",
                            cuenta_nombre="Efectivo",
                            fecha=fecha if fecha else f"{mes}-15",
                        )
                        copiadas += 1
                        if tipo == "income":
                            migradas_ing += 1
                        else:
                            migradas_gas += 1
                    except Exception as e:
                        duplicadas.append(f"{mes}: {desc(it)} → {e}")

            res = [f"✅ Consolidado `default` → TU cuenta: **{copiadas}** transacciones "
                   f"({migradas_ing} ing, {migradas_gas} gas) en {', '.join(meses)}"]
            if duplicadas:
                res.append(f"\n⚠️ No se copiaron {len(duplicadas)}:")
                res += [f"   • {x}" for x in duplicadas[:10]]
            res.append("\nRevisa con `!finanzas` o `!buscar_historial`.")
            await ctx.send("\n".join(res))
            return

        await ctx.send("ℹ️ Uso: `!consolidar` | `!consolidar mostrar` | `!consolidar copiar may,jun,ago|todo|julio`")
    except Exception as e:
        await ctx.send(f"⚠️ Error en consolidar: {e}")
