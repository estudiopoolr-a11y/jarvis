"""Deterministic intent router (modular version).

Este módulo contiene la función principal `procesar_intencion_natural`
pero delega las ramas a sub-routers para evitar código espagueti.

Las escrituras Firestore solo ocurren en acciones determinísticas (handlers)
que son invocadas desde aquí.
"""

from __future__ import annotations

from datetime import datetime

from modules.gemini.inversion import _asesorar_inversion, _es_intencion_inversion
from modules.nlp.router.shared import (
    detectar_mes_num,
    detectar_year,
    meses_spanish,
    nombre_mes,
    normalizar_limite_audio_audio,
)
from modules.nlp.actions import (
    handle_ajustar_balance,
    handle_analisis_financiero,
    handle_balance_finanzas,
    handle_bloque_presupuesto_mensual,
    handle_cuentas_kebo,
    handle_configuracion_masiva,
    handle_completar_tarea,
    handle_limpiar_base_datos,
    handle_listar_categorias,
    handle_listar_recordatorios,
    handle_meta_financiera,
    handle_nueva_tarea,
    handle_pago_fijo,
    handle_perfil_usuario,
    handle_presupuesto_simple,
    handle_recordatorio,
    handle_sobrante,
    handle_tareas_pendientes,
    handle_tasa_cambio,
    handle_transaccion,
    handle_transacciones_futuras,
    handle_ultimas_transacciones,
)
from modules.nlp.parsers import (
    _parse_ajustar_balance,
    _parse_analisis_financiero,
    _parse_bloque_presupuesto_mensual,
    _parse_borrar_presupuesto,
    _parse_editar_presupuesto,
    _parse_listar_categorias,
    _parse_meta,
    _parse_presupuesto_modificar,
    _parse_presupuesto_multiple,
    _parse_renombrar_presupuesto,
    _parse_sobrante,
    _parse_split,
    _parse_subcategoria,
    _parse_pago_fijo,
    _parse_perfil,
    _parse_recordatorio,
    _parse_tasa_cambio,
    _parse_transaccion,
    _parse_transaccion_futura,
    _parse_ver_presupuesto,
    _parse_transferencia,
    _parse_tarea,
    _parse_completar_tarea,
)

# Confirmaciones destructivas
from modules.nlp.confirmations import (
    cancel_budget_deletion,
    consume_budget_deletion,
)

# DB actions (determinísticas)
from modules.db import (
    agregar_aporte_meta,
    aplicar_rollover_presupuesto,
    buscar_transacciones,
    crear_cuenta,
    crear_subcategoria,
    eliminar_meta,
    eliminar_pago_fijo,
    eliminar_presupuesto_mes,
    eliminar_todos_presupuestos_mes,
    establecer_presupuesto,
    establecer_presupuesto_mes,
    guardar_meta,
    guardar_meta_v2,
    guardar_pago_fijo,
    guardar_perfil,
    guardar_recordatorio,
    guardar_tarea,
    guardar_tasa_cambio,
    limpiar_y_cargar_datos_dinamicos,
    listar_categorias,
    listar_cuentas,
    listar_metas_v2,
    listar_recurrentes,
    listar_recordatorios,
    listar_transacciones_futuras,
    listar_transacciones_recientes,
    marcar_tarea_completada,
    modificar_presupuesto,
    modificar_presupuesto_mes,
    obtener_alertas_presupuesto,
    obtener_balance_financiero,
    obtener_balance_total_multimoneda,
    obtener_estadisticas,
    obtener_metas,
    obtener_pagos_fijos,
    obtener_perfil,
    obtener_presupuestos_v2,
    obtener_resumen_presupuestos,
    obtener_tareas_pendientes,
    obtener_tasas_cambio,
    proyectar_meta,
    registrar_split,
    registrar_transaccion,
    registrar_transaccion_futura,
    registrar_transaccion_v2,
    registrar_transferencia,
    renombrar_presupuesto_mes,
    TASAS_DEFAULT,
    crear_categorias_predefinidas,
)

import re


def procesar_intencion_natural(prompt_usuario: str, usuario_id: str, es_audio: bool = False):
    """Router principal determinístico.

    Nota: por compatibilidad, este código reemplaza al anterior router.py.
    """

    texto_lc = prompt_usuario.lower().strip()

    # 1) Confirmación masiva (destructiva)
    if texto_lc in {"confirmar presupuestos", "confirmar borrar presupuestos"}:
        pending = consume_budget_deletion(usuario_id)
        if not pending:
            return "ℹ️ No tienes un borrado masivo pendiente, o la confirmación venció."
        count = eliminar_todos_presupuestos_mes(
            usuario_id,
            pending.year,
            f"{pending.month:02d}",
        )
        if count:
            return (
                f"🗑️ Se eliminaron **{count}** presupuestos de "
                f"{nombre_mes(pending.month)} {pending.year}."
            )
        return (
            f"ℹ️ No había presupuestos registrados para "
            f"{nombre_mes(pending.month)} {pending.year}."
        )

    if texto_lc in {"cancelar presupuestos", "cancelar borrar presupuestos"}:
        if cancel_budget_deletion(usuario_id):
            return "✅ Borrado masivo de presupuestos cancelado."
        return "ℹ️ No tienes un borrado masivo pendiente."

    # 0) ASESORÍA INVERSIÓN
    if _es_intencion_inversion(texto_lc):
        return _asesorar_inversion(prompt_usuario, usuario_id)

    # 0b) Consultas financieras
    if _parse_listar_categorias(texto_lc):
        return handle_listar_categorias(texto_lc, usuario_id, es_audio)

    if _parse_analisis_financiero(texto_lc):
        return handle_analisis_financiero(texto_lc, usuario_id, es_audio)

    if _parse_sobrante(texto_lc):
        return handle_sobrante(texto_lc, usuario_id, es_audio)

    if _parse_ajustar_balance(texto_lc):
        return handle_ajustar_balance(texto_lc, usuario_id, es_audio)

    # 1) LIMPIAR BASE DATOS
    if any(k in texto_lc for k in ["borra", "limpia", "reinicia"]) and any(
        k in texto_lc for k in ["datos", "base", "historial"]
    ):
        return handle_limpiar_base_datos(texto_lc, usuario_id, es_audio)

    # 2) PRESUPUESTOS / BLOQUE
    if "---" in texto_lc and any(
        m in texto_lc.upper()
        for m in ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    ):
        return handle_bloque_presupuesto_mensual(prompt_usuario, usuario_id, es_audio)

    # 2b) CONFIGURACIÓN MASIVA
    if "configura" in texto_lc or ("presupuestos" in texto_lc and "transacciones" in texto_lc):
        return handle_configuracion_masiva(prompt_usuario, usuario_id, es_audio)

    # 3) TAREAS PENDIENTES
    if any(k in texto_lc for k in ["tarea", "tareas"]) and any(
        k in texto_lc for k in ["listar", "mostrar", "ver", "pendientes"]
    ):
        return handle_tareas_pendientes(texto_lc, usuario_id, es_audio)

    # 4) BALANCE / FINANZAS
    if any(
        k in texto_lc
        for k in ["balance", "finanzas", "ingresos", "gastos", "dinero", "plata", "fondos", "capital"]
    ) and any(
        k in texto_lc
        for k in ["cual", "cuál", "cuanto", "cuánto", "ver", "mostrar", "consultar", "tengo", "disponible"]
    ):
        return handle_balance_finanzas(texto_lc, usuario_id, es_audio)

    # 4a) CUENTAS KEB0
    if any(k in texto_lc for k in ["cuenta", "cuentas"]):
        result = handle_cuentas_kebo(texto_lc, usuario_id, es_audio)
        if result:
            return result

    # 4b) RENOMBRAR PRESUPUESTO
    rename_data = _parse_renombrar_presupuesto(texto_lc)
    if rename_data:
        year = detectar_year(texto_lc)
        mes_num = detectar_mes_num(texto_lc)
        cat_ant = rename_data["cat_antigua"]
        cat_nue = rename_data["cat_nueva"]
        nuevo_limite = rename_data.get("nuevo_limite")
        nuevo_limite = normalizar_limite_audio_audio(es_audio, nuevo_limite)

        exito = renombrar_presupuesto_mes(usuario_id, cat_ant, cat_nue, year, f"{mes_num:02d}")
        if exito:
            if nuevo_limite is not None:
                modificar_presupuesto_mes(usuario_id, cat_nue, nuevo_limite, year, f"{mes_num:02d}")
                return (
                    f"✏️ Presupuesto de *{cat_ant}* renombrado a **{cat_nue}** "
                    f"con nuevo monto de **${nuevo_limite:,.0f}** ({nombre_mes(mes_num)} {year})"
                )
            return f"✏️ Presupuesto de *{cat_ant}* renombrado a **{cat_nue}** ({nombre_mes(mes_num)} {year})"
        return f"⚠️ No encontré presupuesto de *{cat_ant}* en {nombre_mes(mes_num)} {year} para renombrar."

    # 4b-edit: EDITAR PRESUPUESTO EXISTENTE
    editar_data = _parse_editar_presupuesto(texto_lc)
    if editar_data:
        year = detectar_year(texto_lc)
        mes_num = detectar_mes_num(texto_lc)
        cat = editar_data["categoria"]
        nuevo_limite = normalizar_limite_audio_audio(es_audio, editar_data["nuevo_limite"])

        exito = modificar_presupuesto_mes(usuario_id, cat, nuevo_limite, year, f"{mes_num:02d}")
        if exito:
            return (
                f"✅ Presupuesto de *{cat}* actualizado a **${nuevo_limite:,.0f}** ({nombre_mes(mes_num)} {year})"
            )
        return f"⚠️ No encontré presupuesto de *{cat}* en {nombre_mes(mes_num)} {year}. ¿Quieres crearlo?"

    # 4b-del: BORRAR PRESUPUESTO
    borrar_data = _parse_borrar_presupuesto(texto_lc)
    if borrar_data:
        year = detectar_year(texto_lc)
        mes_num = detectar_mes_num(texto_lc)

        if borrar_data.get("todos"):
            from modules.nlp.confirmations import request_budget_deletion

            request_budget_deletion(usuario_id, year, mes_num)
            return (
                f"⚠️ Vas a borrar **todos** los presupuestos de {nombre_mes(mes_num)} {year}. "
                "Esta acción no se puede deshacer. "
                "Escribe `confirmar presupuestos` en los próximos 5 minutos para continuar, "
                "o `cancelar presupuestos` para abortar."
            )

        cats = borrar_data.get("categorias") or (
            [borrar_data.get("categoria")] if borrar_data.get("categoria") else []
        )
        if not cats:
            return None

        eliminados = []
        no_encontrados = []
        for cat in cats:
            exito = eliminar_presupuesto_mes(usuario_id, cat, year, f"{mes_num:02d}")
            if exito:
                eliminados.append(cat)
            else:
                no_encontrados.append(cat)

        mensajes = []
        if eliminados:
            cats_str = ", ".join(f"*{c}*" for c in eliminados)
            mensajes.append(f"🗑️ Presupuesto de {cats_str} eliminado ({nombre_mes(mes_num)} {year}).")
        if no_encontrados:
            cats_str = ", ".join(f"*{c}*" for c in no_encontrados)
            mensajes.append(f"⚠️ No encontré presupuesto de {cats_str} en {nombre_mes(mes_num)} {year}.")

        return "\n".join(mensajes) if mensajes else "⚠️ No se pudo procesar la eliminación."

    # 4b-nuevo: CREAR PRESUPUESTOS (múltiples)
    tiene_verbo_creacion = any(k in texto_lc for k in ["pon", "crea", "establece", "configura", "ponme", "ponte"])
    tiene_palabras_excluyentes = any(
        k in texto_lc
        for k in [
            "renombra",
            "renombrar",
            "renombralo",
            "renómbralo",
            "cambia el nombre",
            "cámbiale el nombre",
            "borra",
            "borres",
            "elimina",
            "elimines",
            "quita",
            "quites",
            "cuanto",
            "cuánto",
            "mostrar",
            "dame",
        ]
    )
    tiene_presupuesto_con_monto = (
        not tiene_palabras_excluyentes
        and "presupuesto" in texto_lc
        and bool(re.search(r"\d[\d.,]*(?:k|m)?\b", texto_lc))
    )

    if tiene_verbo_creacion or tiene_presupuesto_con_monto:
        presupuestos_data = _parse_presupuesto_multiple(texto_lc)
        if presupuestos_data:
            year = detectar_year(texto_lc)

            if es_audio:
                for p in presupuestos_data:
                    if p["limite"] < 1000:
                        p["limite"] *= 1000

            resultados = []
            for p in presupuestos_data:
                mes_num = p.get("mes") or datetime.now().month
                cat = p["categoria"]
                monto = p["limite"]

                exito = establecer_presupuesto_mes(usuario_id, cat, monto, year, f"{mes_num:02d}")
                if exito:
                    resultados.append(f"✅ {cat}: ${monto:,.0f} ({nombre_mes(mes_num)} {year})")
                else:
                    resultados.append(f"⚠️ Error guardando presupuesto de {cat}")

            return "🎯 **Presupuestos configurados:**\n" + "\n".join(resultados)

    # 4b/ver presupuestos (solo rama existente básica)
    if "presupuesto" in texto_lc or "presupuestos" in texto_lc:
        mes_num = None
        for nombre, num in meses_spanish().items():
            if nombre in texto_lc:
                mes_num = num
                break

        if mes_num:
            anio = detectar_year(texto_lc)
            mes_formato = f"{anio}-{mes_num:02d}"
            try:
                presupuestos_mes = obtener_resumen_presupuestos(usuario_id, mes_formato)
            except TypeError:
                presupuestos_mes = obtener_resumen_presupuestos(usuario_id)

            if presupuestos_mes:
                total = sum(presupuestos_mes.values())
                msg = f"📊 **PRESUPUESTOS {nombre_mes(mes_num)} {anio}**\n\n"
                for cat, limite in presupuestos_mes.items():
                    msg += f"• {cat}: ${limite:,.0f}\n"
                msg += f"\n💰 **Total: ${total:,.0f}**"
                return msg
            return f"📋 No hay presupuestos registrados para {nombre_mes(mes_num)} {anio}."

    # 5) TRANSFERENCIAS
    transferencia_data = _parse_transferencia(texto_lc)
    if transferencia_data:
        from modules.db import registrar_transferencia
        result = registrar_transferencia(
            usuario_id,
            transferencia_data["origen"],
            transferencia_data["destino"],
            transferencia_data["monto"],
            transferencia_data.get("descripcion", ""),
            0.0,
        )
        tx_id, msg = result if isinstance(result, tuple) else (result, None)
        if tx_id:
            return f"💸 Transferencia registrada: **-${transferencia_data['monto']:,.0f}** de *{transferencia_data['origen']}* a *{transferencia_data['destino']}*."
        return "⚠️ Error al registrar transferencia."

    # 6) PERFIL
    perfil = handle_perfil_usuario(texto_lc, usuario_id, es_audio)
    if perfil:
        return perfil

    # 6b) METAS FINANCIERAS
    if _parse_meta(texto_lc):
        return handle_meta_financiera(texto_lc, usuario_id, es_audio)

    # 7) TAREAS (más específicas)
    if _parse_tarea(texto_lc):
        return handle_nueva_tarea(texto_lc, usuario_id, es_audio)
    if _parse_completar_tarea(texto_lc):
        return handle_completar_tarea(texto_lc, usuario_id, es_audio)
    if _parse_recordatorio(texto_lc):
        return handle_recordatorio(texto_lc, usuario_id, es_audio)

    # 8) SUBCATEGORÍAS
    if _parse_subcategoria(texto_lc):
        from modules.nlp.parsers import _parse_subcategoria
        from modules.db import crear_subcategoria
        sub_data = _parse_subcategoria(texto_lc)
        if sub_data:
            result = crear_subcategoria(
                usuario_id,
                sub_data["sub_nombre"],
                sub_data["cat_nombre"]
            )
            if result:
                return f"📁 Subcategoría creada: *{sub_data['sub_nombre']}* bajo *{sub_data['cat_nombre']}*."
            return "⚠️ Error al crear subcategoría."

    # 9) PAGO FIJO
    if _parse_pago_fijo(texto_lc):
        return handle_pago_fijo(texto_lc, usuario_id, es_audio)

    # 10) TASA DE CAMBIO
    if _parse_tasa_cambio(texto_lc):
        return handle_tasa_cambio(texto_lc, usuario_id, es_audio)

    # 11) TRANSACCIÓN (genérica)
    if _parse_transaccion(texto_lc):
        return handle_transaccion(texto_lc, usuario_id, es_audio)

    # 12) TRANSACTION FUTURA
    if _parse_transaccion_futura(texto_lc):
        from modules.nlp.actions import handle_transacciones_futuras
        return handle_transacciones_futuras(texto_lc, usuario_id, es_audio)

    # 13) SPLIT
    if _parse_split(texto_lc):
        from modules.nlp.actions import handle_transaccion  # split uses transaccion handler internally
        return handle_transaccion(texto_lc, usuario_id, es_audio)

    # No match found in deterministic router; return None to let Gemini handle it.
    return None
