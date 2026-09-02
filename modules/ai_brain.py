import os
import json
import time
import hashlib
import yfinance as yf
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel
from typing import Literal, Optional
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import firestore
from modules.database import (
    guardar_tarea, registrar_transaccion, establecer_presupuesto,
    marcar_tarea_completada, inicializar_firebase, limpiar_y_cargar_datos_dinamicos,
    obtener_contexto_financiero,
    obtener_tareas_pendientes, obtener_balance_financiero, obtener_resumen_presupuestos,
    guardar_meta, obtener_metas, eliminar_meta, actualizar_progreso_meta, proyectar_meta
)
from datetime import datetime

# OPTIMIZACIÓN: Cache para búsquedas web (1 hora TTL)
_busquedas_cache = {}
_CACHE_WEB_TTL = 3600

# OPTIMIZACIÓN: Cliente de Gemini reutilizable por key
_clientes_cache = {}

load_dotenv()

# ---------- API Key Rotation Setup ----------
_api_keys_str = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
if not _api_keys_str:
    raise ValueError("No Gemini API key found.")
_API_KEYS = [k.strip() for k in _api_keys_str.split(',') if k.strip()]
_key_index = 0

def _get_current_client() -> genai.Client:
    """OPTIMIZADO: Reusa clientes existentes en cache."""
    global _clientes_cache
    key = _API_KEYS[_key_index]
    if key not in _clientes_cache:
        _clientes_cache[key] = genai.Client(api_key=key)
    return _clientes_cache[key]

def _rotate_key() -> None:
    """Rotate to the next API key (round-robin)."""
    global _key_index
    _key_index = (_key_index + 1) % len(_API_KEYS)

def _gemini_call_with_fallback(callable):
    """
    Execute a callable that takes a genai.Client and makes a Gemini API request.
    On APIError 429, rotate API key and retry (up to number of keys times).
    Propagates other APIError immediately.
    Returns the callable's result.
    """
    retries = len(_API_KEYS)
    for _ in range(retries):
        try:
            return callable(_get_current_client())
        except APIError as e:
            if e.code == 429:
                # Rotate key and try again
                _rotate_key()
                continue
            # For non-429 errors, re-raise immediately
            raise
    # If we exhausted all keys due to 429
    raise Exception(
        "⚠️ **Cuota de Gemini agotada en todas las keys.**\n\n"
        "Las 5 API keys de Gemini han alcanzado su límite diario.\n"
        "• Espera hasta la medianoche (hora Colombia) para que se resetee la cuota\n"
        "• O agrega nuevas API keys en el archivo .env (GEMINI_API_KEYS)\n"
        "• Por ahora, los comandos básicos (!finanzas, !tareas) seguirán funcionando."
    )

# -------------------------------------------

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

SYSTEM_INSTRUCTION = """
JARVIS: asistente financiero ejecutivo. Frío, analítico, directo. Responde con datos reales del usuario.
"""

class ItemIntencion(BaseModel):
    tipo: Literal["tarea", "gasto", "ingreso", "presupuesto", "completar_tarea", "configuracion_masiva", "ninguno"]
    tarea: Optional[str] = None
    prioridad: Optional[str] = "Media"
    fecha_limite: Optional[str] = "Pronto"
    monto: Optional[float] = 0.0
    categoria: Optional[str] = "General"
    descripcion: Optional[str] = None
    limite: Optional[float] = 0.0
    presupuestos_dict: Optional[dict] = None
    transacciones_list: Optional[list] = None

PALABRAS_CLAVE_INTENCION = [
    "gasto", "gasté", "compré", "pagué", "compra", "ingreso", "gané", "recibí",
    "pago", "tarea", "pendiente", "recordar", "presupuesto", "límite", "completé",
    "terminé", "hecho", "debo", "cuota", "finanzas", "gastos", "historial", "desglose",
    "borra", "limpia", "reinicia", "configura", "cargar"
]

def _parse_configuracion_masiva(texto: str) -> tuple[dict, list] | None:
    """
    Parser directo para el formato de configuración masiva.
    Formatos soportados:
      Formato estructurado (preferido):
        - tipo: ingreso, monto: 806199.03, categoria: Salario, descripcion: Salario mensual
        - tipo: gasto, monto: 332540, categoria: Women, descripcion: Gastos categoría Women
      Formato simple:
        - Salario +806199.03
        - Gasto Women 332540
    Retorna (presupuestos_dict, transacciones_list) o None si no coincide.
    """
    import re

    presupuestos = {}
    transacciones = []

    # Buscar sección de presupuestos
    match_pres = re.search(r'presupuestos?[:\s]+(.+?)(?=transacciones?[:\s]|$)', texto, re.IGNORECASE | re.DOTALL)
    if match_pres:
        pres_text = match_pres.group(1)
        for cat_match in re.finditer(r'(\w+)\s*:\s*([\d,.]+)', pres_text):
            cat = cat_match.group(1).strip()
            try:
                monto = float(cat_match.group(2).replace(',', ''))
                if monto > 0:
                    presupuestos[cat] = monto
            except ValueError:
                pass

    # Buscar sección de transacciones
    match_trans = re.search(r'transacciones?[:\s]+(.+?)(?=$)', texto, re.IGNORECASE | re.DOTALL)
    if match_trans:
        trans_text = match_trans.group(1)

        # Parsear cada línea de transacción (formato estructurado)
        lineas = trans_text.strip().split('\n')
        for linea in lineas:
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue

            # Intentar parsear formato estructurado primero
            # Ejemplo: "- tipo: ingreso, monto: 806199.03, categoria: Salario, descripcion: Salario mensual"
            trans_match = re.search(
                r'tipo:\s*(ingreso|gasto)\s*,\s*monto:\s*([\d,.]+)\s*,\s*categoria:\s*([^,]+?)\s*(?:,\s*descripcion:\s*(.+))?$',
                linea, re.IGNORECASE
            )

            if trans_match:
                tipo = trans_match.group(1).lower()
                monto = float(trans_match.group(2).replace(',', ''))
                cat = trans_match.group(3).strip()
                desc = (trans_match.group(4) or cat).strip()

                if monto > 0:
                    transacciones.append({
                        'tipo': tipo,
                        'monto': monto,
                        'categoria': cat.title() if cat else 'General',
                        'descripcion': desc
                    })
                continue

            # Fallback al formato simple: "Palabra +/-Monto" o "Gasto Palabra Monto"
            simple_match = re.search(r'([\w\s]+?)\s*([+-])?\s*\$?\s*([\d,.]+)$', linea)
            if simple_match:
                desc = simple_match.group(1).strip()
                try:
                    monto = float(simple_match.group(3).replace(',', ''))
                    if monto > 0:
                        desc_lower = desc.lower()
                        if desc_lower.startswith('gasto'):
                            tipo = 'gasto'
                            cat = desc[5:].strip() if len(desc) > 5 else 'General'
                        else:
                            tipo = 'ingreso'
                            cat = 'General'
                        transacciones.append({
                            'tipo': tipo,
                            'monto': monto,
                            'categoria': cat.title() if cat else 'General',
                            'descripcion': desc
                        })
                except ValueError:
                    pass

    if presupuestos or transacciones:
        return presupuestos, transacciones
    return None


# ============================================================
# PARSERS DETERMINÍSTICOS (evitan llamadas a Gemini)
# ============================================================

import re


def _parse_tarea(texto: str) -> dict | None:
    """Extrae tarea, prioridad y fecha de un mensaje de tarea."""
    texto_lower = texto.lower()

    # Detectar prioridad
    prioridad = "Media"
    if any(w in texto_lower for w in ["urgente", "crítica", "crítico"]):
        prioridad = "Alta"
    elif any(w in texto_lower for w in ["baja", "cuando pueda"]):
        prioridad = "Baja"

    # Detectar fecha límite
    fecha = "Pronto"
    if any(w in texto_lower for w in ["mañana", "manana"]):
        fecha = "Mañana"
    elif "hoy" in texto_lower:
        fecha = "Hoy"
    elif "semana" in texto_lower:
        fecha = "Esta semana"

    # Extraer descripción de la tarea
    patrones = [
        r'(?:agrega?|crea?|nueva?)?\s*tarea\s+(.+?)(?:\s+(?:prioridad|prioridad|alt[ao]|baja|urgente|mañana|manana|manana|hoy|esta semana))?$',
        r'(?:agrega?|crea?)?\s*(.+?)\s+(?:como\s+)?(?:tarea|pendiente|recordar)',
        r'(?:recordar|recuerdame|recordame)\s+(.+?)$',
    ]
    for patron in patrones:
        match = re.search(patron, texto_lower)
        if match:
            tarea = match.group(1).strip()
            if len(tarea) > 2:
                return {"tarea": tarea.title(), "prioridad": prioridad, "fecha_limite": fecha}

    # Si no matcheó ningún patrón pero dice "tarea"
    if "tarea" in texto_lower:
        # Tomar todo después de "tarea" o "nueva tarea"
        tarea = re.sub(r'^.*?tarea\s+', '', texto_lower).strip()
        tarea = re.sub(r'\s*(prioridad|alt[ao]|baja|urgente|mañana|manana|manana|hoy|esta semana).*$', '', tarea).strip()
        if len(tarea) > 2:
            return {"tarea": tarea.title(), "prioridad": prioridad, "fecha_limite": fecha}

    return None


def _parse_transaccion(texto: str) -> dict | None:
    """Extrae tipo (gasto/ingreso), monto y categoría de un mensaje."""
    texto_lower = texto.lower()

    # Patrones de gasto: "gasto 5000 en comida", "gasté 5000 supermercado", "compré 5000"
    gasto_patterns = [
        r'gast[oáé]\s+([\d,.]+)\s*(?:en\s+)?(.+?)(?:\s*$|$)',
        r'compr[oóé]\s+([\d,.]+)\s*(?:en\s+)?(.+?)(?:\s*$|$)',
        r'pag[uú][oóé]\s+([\d,.]+)\s*(?:en\s+)?(.+?)(?:\s*$|$)',
        r'compr[oóé]\s+([\d,.]+)\s*(?:en\s+)?(.+?)(?:\s*$|$)',
    ]
    for patron in gasto_patterns:
        match = re.search(patron, texto_lower)
        if match:
            monto = float(match.group(1).replace(',', ''))
            cat = match.group(2).strip() or "General"
            # Limpiar categoría
            cat = re.sub(r'^(en|del|de|la|el|los|las)\s+', '', cat).strip()
            cat = cat.title() if cat else "General"
            return {"tipo": "gasto", "monto": monto, "categoria": cat}

    # Patrones de ingreso: "ingreso 50000", "gané 50000", "recibí 50000", "salario +50000"
    ingreso_patterns = [
        r'ingreso\s+([\d,.]+)',
        r'gan[oé]\s+([\d,.]+)',
        r'recib[oí]\s+([\d,.]+)',
        r'salario\s*\+?\s*([\d,.]+)',
        r'\+\s*([\d,.]+)\s*(?:pesos?|cop)?',
    ]
    for patron in ingreso_patterns:
        match = re.search(patron, texto_lower)
        if match:
            monto = float(match.group(1).replace(',', ''))
            return {"tipo": "ingreso", "monto": monto, "categoria": "Ingreso"}

    return None


def _parse_presupuesto(texto: str) -> dict | None:
    """Extrae categoría y límite de presupuesto."""
    texto_lower = texto.lower()

    # Patrones: "presupuesto Comida 50000", "límite Comida 50000", "presupuesto para Comida 50000"
    patrones = [
        r'presupuesto\s+(?:para\s+)?(\w+)\s+([\d,.]+)',
        r'l[íi]mite\s+(\w+)\s+([\d,.]+)',
        r'(\w+)\s+(?:presupuesto\s+)?([\d,.]+)',
    ]
    for patron in patrones:
        match = re.search(patron, texto_lower)
        if match:
            cat = match.group(1).strip()
            limite = float(match.group(2).replace(',', ''))
            # Filtrar palabras que no son categorías
            if cat not in ["el", "la", "los", "las", "de", "del", "en", "un", "una"]:
                return {"categoria": cat.title(), "limite": limite}

    return None


def _parse_completar_tarea(texto: str) -> str | None:
    """Extrae el nombre de la tarea a completar."""
    texto_lower = texto.lower()

    patrones = [
        r'complet[oéé]\s+(.+)',
        r'hecho\s+(.+)',
        r'termin[oé]\s+(.+)',
        r'borrar\s+(.+)',
        r'eliminar\s+(.+)',
        r'done\s+(.+)',
    ]
    for patron in patrones:
        match = re.search(patron, texto_lower)
        if match:
            tarea = match.group(1).strip()
            if len(tarea) > 1:
                return tarea

    return None


def _parse_meta(texto: str) -> dict | None:
    """Extrae nombre, monto y fecha de una meta financiera."""
    import re
    texto_lower = texto.lower()

    # Patrones para crear meta
    # "meta vacaciones 3000000 diciembre"
    # "crear meta casa 50000000"
    # "quiero ahorrar 1 millon para navidad"
    # "meta 1 millon"
    patrones = [
        r'meta\s+(\w+(?:\s+\w+)?)\s+([\d,.]+)',
        r'crear\s+meta\s+(\w+(?:\s+\w+)?)\s+([\d,.]+)',
        r'ahorrar\s+(?:para\s+)?(?:un[ao]?\s+)?(\w+(?:\s+\w+)?)\s+([\d,.]+)',
        r'quiero\s+ahorrar\s+([\d,.]+)\s+(?:para\s+)?(.+?)(?:\s+(?:en|hasta|para)\s+(.+))?$',
        r'(\w+(?:\s+\w+)?)\s+([\d,.]+)',
    ]

    for i, patron in enumerate(patrones):
        match = re.search(patron, texto_lower)
        if match:
            if i == 3:  # "quiero ahorrar 1 millon para X"
                monto_str = match.group(1).replace(',', '')
                nombre = match.group(2).strip()
            else:
                nombre = match.group(1).strip()
                monto_str = match.group(2).replace(',', '')

            try:
                monto = float(monto_str)
            except ValueError:
                continue

            # Detectar fecha
            fecha = ""
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                     "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            mes_encontrado = next((m for m in meses if m in texto_lower), None)
            if mes_encontrado:
                from datetime import datetime
                mes_num = meses.index(mes_encontrado) + 1
                fecha = f"2026-{mes_num:02d}-28"

            return {"nombre": nombre.title(), "monto": monto, "fecha": fecha}
    return None


# ============================================================
# ASESOR DE INVERSIONES COLOMBIA
# ============================================================

def _es_intencion_inversion(texto: str) -> bool:
    """Detecta si el usuario está preguntando sobre inversiones."""
    palabras = [
        "invertir", "inversion", "inverti", "cdt", "renta fija", "dónde meto",
        "plata", "tasas", "app", "broker", "banco", "ahorrar",
        "donde invierto", "fondo", "etf", "bolsa", "acciones",
        "rendimientos", "intereses", "deposito", "ahorro"
    ]
    return any(p in texto for p in palabras)


def _asesorar_inversion(prompt_usuario: str, usuario_id: str):
    """Genera asesoría de inversión para Colombia usando búsqueda web en tiempo real."""
    try:
        # Obtener datos financieros del usuario
        balance_neto, ingresos, gastos, _ = obtener_balance_financiero(usuario_id)

        # Calcular capacidad de inversión (20% del balance disponible, mínimo $100.000)
        capacidad_inversion = max(balance_neto * 0.20, 100000)

        # OPTIMIZADO: 1 sola llamada con todo incluido (antes 3 llamadas)
        prompt_unificado = f"""Eres JARVIS, asesor financiero ejecutivo de Colombia.

CONTEXTO: Balance=${balance_neto:,.0f} COP | Capacidad sugerida=${capacidad_inversion:,.0f} COP (20%)

PREGUNTA: {prompt_usuario}

INSTRUCCIONES (responde en español):
1. Busca en la web: tasas CDT Colombia {datetime.now().month}/{datetime.now().year} (Bancolombia, Davivienda, Banco de Bogotá)
2. Busca en la web: mejores apps invertir Colombia 2026 (Tyba, Trii, Hapi, Nequi)
3. Genera respuesta con: tabla tasas CDT | comparativa apps | recomendación personalizada
4. Finaliza con: TAREAS: [tarea1] | [tarea2] | [tarea3]

Si balance < $500.000, recomienda apps sin monto mínimo.
Si balance > $1.000.000, recomienda diversificar CDT + app."""

        response = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_unificado,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    max_output_tokens=2000
                )
            )
        )

        respuesta = response.text or "No se pudo generar la asesoría."

        # Extraer y crear tareas si existen
        if "TAREAS:" in respuesta:
            parte_tareas = respuesta.split("TAREAS:")[1].strip()
            # Tomar solo la primera línea de tareas
            parte_tareas = parte_tareas.split("\n")[0]
            tareas = [t.strip() for t in parte_tareas.split("|") if t.strip()]

            for tarea in tareas[:3]:  # Máximo 3 tareas
                if 5 < len(tarea) < 100:
                    guardar_tarea(usuario_id, tarea, "Media", "Esta semana")

        return respuesta

    except Exception as e:
        return f"⚠️ Error generando asesoría de inversión: {e}"


# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def procesar_intencion_natural(prompt_usuario: str, usuario_id: str):
    texto_lc = prompt_usuario.lower().strip()

    # =========================================
    # 0. ASESORÍA DE INVERSIÓN
    # =========================================
    if _es_intencion_inversion(texto_lc):
        return _asesorar_inversion(prompt_usuario, usuario_id)

    # =========================================
    # 1. LIMPIAR BASE DE DATOS
    # =========================================
    if any(k in texto_lc for k in ["borra", "limpia", "reinicia"]) and any(k in texto_lc for k in ["datos", "base", "historial"]):
        result = limpiar_y_cargar_datos_dinamicos(usuario_id, {}, [])
        return f"🤖 **[SISTEMA REINICIADO POR JARVIS]**\n{result}\n\n*He limpiado la basura anterior.*"

    # =========================================
    # 2. CONFIGURACIÓN MASIVA
    # =========================================
    if "configura" in texto_lc or ("presupuestos" in texto_lc and "transacciones" in texto_lc):
        parsed = _parse_configuracion_masiva(prompt_usuario)
        if parsed:
            presupuestos, transacciones = parsed
            result = limpiar_y_cargar_datos_dinamicos(usuario_id, presupuestos, transacciones)
            return f"🤖 **[CONFIGURACIÓN MASIVA CARGADA]**\n{result}"
        return "⚠️ No pude parsear la configuración. Verifica el formato."

    # =========================================
    # 3. VER TAREAS PENDIENTES
    # =========================================
    if any(k in texto_lc for k in ["tarea", "tareas"]) and any(k in texto_lc for k in ["listar", "mostrar", "ver", "pendientes"]):
        tareas = obtener_tareas_pendientes(usuario_id)
        if not tareas:
            return "📋 No tienes tareas pendientes."
        lista = "\n".join([f"• [{t['prioridad']}] {t['tarea']} (Vence: {t['fecha_limite']})" for t in tareas])
        return f"📋 **Tareas pendientes ({len(tareas)}):**\n{lista}"

    # =========================================
    # 4. VER BALANCE/FINANZAS
    # =========================================
    if any(k in texto_lc for k in ["balance", "finanzas", "ingresos", "gastos"]) and \
       any(k in texto_lc for k in ["cual", "cúal", "cuanto", "cuánto", "ver", "mostrar", "consultar", "cuánto"]):
        balance, ingresos, gastos, _ = obtener_balance_financiero(usuario_id)
        presupuestos = obtener_resumen_presupuestos(usuario_id)
        msg = f"💰 **Balance financiero:**\n- Ingresos: +${ingresos:,.0f}\n- Gastos: -${gastos:,.0f}\n- Neto: ${balance:,.0f}\n"
        if presupuestos:
            msg += "- Presupuestos: " + ", ".join([f"{k}: ${v:,.0f}" for k, v in presupuestos.items()])
        else:
            msg += "- No hay presupuestos establecidos."
        return msg

    # =========================================
    # 5. PARSERS DETERMINÍSTICOS
    # =========================================

    # 5a. Completar tarea
    completada_texto = _parse_completar_tarea(texto_lc)
    if completada_texto:
        completada = marcar_tarea_completada(usuario_id, completada_texto)
        if completada:
            return f"✅ Tarea completada: *'{completada}'*. Avanza con el siguiente pendiente."
        return "⚠️ No encontré tarea que coincida."

    # 5b. Nueva tarea
    tarea_data = _parse_tarea(texto_lc)
    if tarea_data:
        guardar_tarea(usuario_id, tarea_data["tarea"], tarea_data["prioridad"], tarea_data["fecha_limite"])
        return f"📌 Tarea registrada: *{tarea_data['tarea']}* [Prioridad: {tarea_data['prioridad']}, Vence: {tarea_data['fecha_limite']}]"

    # 5c. Transacción (gasto/ingreso)
    transaccion = _parse_transaccion(texto_lc)
    if transaccion:
        monto = transaccion["monto"]
        cat = transaccion["categoria"]
        tipo = transaccion["tipo"]
        if tipo == "gasto":
            alerta = registrar_transaccion(usuario_id, "gasto", monto, cat, "Registro directo")
            return f"💸 Gasto registrado: **-${monto:,.0f}** en *{cat}*.{alerta or ''}"
        else:
            registrar_transaccion(usuario_id, "ingreso", monto, cat, "Registro directo")
            return f"💰 Ingreso registrado: **+${monto:,.0f}** en *{cat}*."

    # 5d. Presupuesto
    presupuesto_data = _parse_presupuesto(texto_lc)
    if presupuesto_data:
        establecer_presupuesto(usuario_id, presupuesto_data["categoria"], presupuesto_data["limite"])
        return f"🎯 Presupuesto: *{presupuesto_data['categoria']}* = **${presupuesto_data['limite']:,.0f}**"

    # 5e. Meta financiera
    if any(k in texto_lc for k in ["meta", "objetivo", "ahorrar para", "quiero ahorrar", "crear meta"]):
        meta_data = _parse_meta(texto_lc)
        if meta_data:
            guardar_meta(usuario_id, meta_data["nombre"], meta_data["monto"], meta_data["fecha"])

            # Calcular capacidad de ahorro
            balance, ingresos, gastos, _ = obtener_balance_financiero(usuario_id)
            capacidad_mensual = max(0, ingresos - gastos) / 1  # Aproximado

            # Proyectar
            from modules.database import proyectar_meta
            proy = proyectar_meta({"monto_objetivo": meta_data["monto"], "monto_actual": 0, "fecha_limite": meta_data["fecha"]}, capacidad_mensual)

            msg = f"🎯 **META CREADA**\n\n"
            msg += f"✅ **{meta_data['nombre']}**\n"
            msg += f"   Meta: ${meta_data['monto']:,.0f}\n"
            if meta_data["fecha"]:
                msg += f"   📅 Fecha límite: {meta_data['fecha']}\n"
            msg += f"   💰 Tu capacidad de ahorro: ${capacidad_mensual:,.0f}/mes\n"

            if proy["atrasado"] and meta_data["fecha"]:
                msg += f"\n⚠️ **ALERTA:** Necesitas ahorrar ${proy['ahorro_necesario']:,.0f}/mes para llegar a tiempo\n"
                msg += f"💡 Reduce gastos o aumenta ingresos en ${proy['ahorro_necesario'] - capacidad_mensual:,.0f}/mes"

            return msg

        # Si dice "metas" (ver todas)
        if "metas" in texto_lc or "mis metas" in texto_lc:
            metas = obtener_metas(usuario_id)
            if not metas:
                return "📋 No tienes metas. Crea una con: `@Jarvis meta <nombre> <monto> [fecha]`"

            balance, ingresos, gastos, _ = obtener_balance_financiero(usuario_id)
            capacidad = max(0, ingresos - gastos)

            msg = "🎯 **TUS METAS**\n\n"
            for m in metas:
                from modules.database import proyectar_meta
                p = proyectar_meta(m, capacidad)
                barra_llena = int(p["porcentaje"] / 10)
                barra = "█" * barra_llena + "░" * (10 - barra_llena)
                estado = "✅" if m.get("completada") else ("⚠️" if p["atrasado"] else "🎯")
                msg += f"{estado} **{m['nombre']}**\n"
                msg += f"   {barra} {p['porcentaje']:.0f}%\n"
                msg += f"   ${m['monto_actual']:,.0f} / ${m['monto_objetivo']:,.0f}\n"
                if p["falta"] > 0 and not m.get("completada"):
                    msg += f"   Falta: ${p['falta']:,.0f}\n"
                msg += "\n"
            return msg

    # =========================================
    # 6. NADA MATCHEÓ → USAR GEMINI
    # =========================================
    # Solo para preguntas complejas que no matchearon ningún parser
    return None

def _gemini_call_with_cache(prompt: str, usar_web: bool = True, max_tokens: int = 1500):
    """Llama a Gemini con cache de búsquedas web para evitar repetir la misma query."""
    cache_key = hashlib.md5(f"{prompt}|{usar_web}".encode()).hexdigest()
    ahora = time.time()

    # Verificar cache
    if cache_key in _busquedas_cache:
        timestamp, resultado = _busquedas_cache[cache_key]
        if ahora - timestamp < _CACHE_WEB_TTL:
            return resultado

    # Hacer llamada real
    tools = [{"google_search": {}}] if usar_web else None
    resultado = _gemini_call_with_fallback(
        lambda c: c.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=tools,
                max_output_tokens=max_tokens
            )
        ).text
    )

    if resultado:
        _busquedas_cache[cache_key] = (ahora, resultado)

    return resultado


def _necesita_busqueda_web(texto: str) -> bool:
    """Determina si la pregunta requiere búsqueda web en tiempo real."""
    texto_lower = texto.lower()
    palabras_web = [
        "noticia", "actual", "hoy", "ayer", "esta semana", "último", "ultimo",
        "precio", "vale", "cuesta", "tasa", "cdt", "inflación", "inflacion",
        "dolar", "dólar", "trm", "bolsa", "mercado", "invertir", "inversion",
        "noticias", "2026", "2025", "reciente"
    ]
    return any(p in texto_lower for p in palabras_web)


def pensar_respuesta(prompt_usuario: str, usuario_id: str = "default") -> str:
    """Responde preguntas generales inyectando el contexto de Firebase y Google Search."""
    try:
        contexto_db = obtener_contexto_financiero(usuario_id)
        prompt_completo = f"{SYSTEM_INSTRUCTION}{contexto_db}\n\nMensaje del usuario: {prompt_usuario}"

        # OPTIMIZADO: Solo usar google_search si es necesario
        usar_web = _necesita_busqueda_web(prompt_usuario)
        tools = [{"google_search": {}}] if usar_web else None

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_completo,
                config=types.GenerateContentConfig(
                    tools=tools,
                    max_output_tokens=1500,
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )
        return response_text or "Sin respuesta disponible."
    except APIError as e:
        if e.code == 429:
            retry_delay_seconds = None
            try:
                # Try to extract retry delay from error details
                if hasattr(e, 'details') and e.details:
                    import json
                    if isinstance(e.details, str):
                        try:
                            details = json.loads(e.details)
                        except:
                            details = {}
                    elif isinstance(e.details, dict):
                        details = e.details
                    else:
                        details = {}

                    if isinstance(details, dict) and 'retryDelay' in details:
                        delay_str = details['retryDelay']
                        if isinstance(delay_str, str) and delay_str.endswith('s'):
                            try:
                                retry_delay_seconds = int(delay_str[:-1])
                            except ValueError:
                                pass

                # Fallback: check error message for retry delay patterns
                if retry_delay_seconds is None and hasattr(e, 'message'):
                    msg = str(e.message)
                    import re
                    # Look for patterns like "retry after 60 seconds" or "60s"
                    match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                    if match:
                        retry_delay_seconds = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)s', msg)
                        if match:
                            retry_delay_seconds = int(match.group(1))

                # Determine appropriate response based on delay
                if retry_delay_seconds is not None and retry_delay_seconds <= 300:  # 5 minutes or less
                    return f"⚠️ Límite de tasa alcanzado. Por favor, espera {retry_delay_seconds} segundos antes de intentarlo nuevamente."
                else:
                    return "⚠️ Se ha agotado la cuota diaria gratuita de la API de Gemini. La cuota se reinicia a medianoche (hora del Pacífico). Por favor, intenta nuevamente mañana."
            except Exception as parse_error:
                # If parsing fails, fall back to safe message
                print(f"Error parsing 429 details in pensar_respuesta: {parse_error}")
                return "⚠️ Se ha alcanzado el límite de la API de Gemini. Verifica tu consumo y vuelve a intentar en unos minutos."
        return f"Error en la API de Gemini: {e.message}"
    except Exception as e:
        return f"Error en sistemas: {e}"

def analizar_inversion(ticker: str) -> str:
    """Analiza un activo bursátil combinando datos en vivo de yfinance y búsqueda web."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")

        datos_mercado = ""
        if not hist.empty:
            precio_actual = hist['Close'].iloc[-1]
            precio_anterior = hist['Close'].iloc[-2]
            cambio_pct = ((precio_actual - precio_anterior) / precio_anterior) * 100
            datos_mercado = f"Precio actual: ${precio_actual:,.2f} USD. Variación reciente: {cambio_pct:+.2f}%."
        else:
            datos_mercado = f"No se obtuvieron datos directos de yfinance para `{ticker}`."

        prompt_analisis = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            f"El usuario evalúa el activo o instrumento financiero: {ticker.upper()}.\n"
            f"Datos del mercado: {datos_mercado}\n"
            "Busca en la web el contexto reciente de este activo o empresa y realiza un análisis frío, objetivo y pragmático."
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_analisis,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    max_output_tokens=1500
                )
            ).text
        )
        return response_text or "Error analizando el activo."
    except APIError as e:
        if e.code == 429:
            retry_delay_seconds = None
            try:
                # Try to extract retry delay from error details
                if hasattr(e, 'details') and e.details:
                    import json
                    if isinstance(e.details, str):
                        try:
                            details = json.loads(e.details)
                        except:
                            details = {}
                    elif isinstance(e.details, dict):
                        details = e.details
                    else:
                        details = {}

                    if isinstance(details, dict) and 'retryDelay' in details:
                        delay_str = details['retryDelay']
                        if isinstance(delay_str, str) and delay_str.endswith('s'):
                            try:
                                retry_delay_seconds = int(delay_str[:-1])
                            except ValueError:
                                pass

                # Fallback: check error message for retry delay patterns
                if retry_delay_seconds is None and hasattr(e, 'message'):
                    msg = str(e.message)
                    import re
                    # Look for patterns like "retry after 60 seconds" or "60s"
                    match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                    if match:
                        retry_delay_seconds = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)s', msg)
                        if match:
                            retry_delay_seconds = int(match.group(1))

                # Determine appropriate response based on delay
                if retry_delay_seconds is not None and retry_delay_seconds <= 300:  # 5 minutes or less
                    return f"⚠️ Límite de tasa alcanzado. Por favor, espera {retry_delay_seconds} segundos antes de intentarlo nuevamente."
                else:
                    return "⚠️ Se ha agotado la cuota diaria gratuita de la API de Gemini. La cuota se reinicia a medianoche (hora del Pacífico). Por favor, intenta nuevamente mañana."
            except Exception as parse_error:
                # If parsing fails, fall back to safe message
                print(f"Error parsing 429 details in analizar_inversion: {parse_error}")
                return "⚠️ Se ha alcanzado el límite de la API de Gemini. Verifica tu consumo y vuelve a intentar en unos minutos."
        return f"Error de API: {e.message}"
    except Exception as e:
        return f"Error consultando el mercado para {ticker}: {e}"

def pensar_respuesta_imagen(ruta_imagen: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa una imagen (factura, recibo, captura) extrayendo transacciones automáticamente."""
    try:
        imagen_file = _gemini_call_with_fallback(lambda c: c.files.upload(file=ruta_imagen))
        # OPTIMIZADO: Prompt más corto + max_output_tokens
        prompt = (
            f"{SYSTEM_INSTRUCTION}\n"
            "Si es recibo/factura: extrae monto, establecimiento, categoría. "
            f"Comentario: {prompt_adicional}"
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, imagen_file],
                config=types.GenerateContentConfig(
                    max_output_tokens=1000,
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )

        if response_text:
            procesar_intencion_natural(response_text, usuario_id)

        try:
            imagen_file.delete()  # Assuming the file object has a delete method; if not, fallback
        except Exception:
            pass

        return response_text or "Imagen procesada sin texto resultante."
    except APIError as e:
        if e.code == 429:
            retry_delay_seconds = None
            try:
                # Try to extract retry delay from error details
                if hasattr(e, 'details') and e.details:
                    import json
                    if isinstance(e.details, str):
                        try:
                            details = json.loads(e.details)
                        except:
                            details = {}
                    elif isinstance(e.details, dict):
                        details = e.details
                    else:
                        details = {}

                    if isinstance(details, dict) and 'retryDelay' in details:
                        delay_str = details['retryDelay']
                        if isinstance(delay_str, str) and delay_str.endswith('s'):
                            try:
                                retry_delay_seconds = int(delay_str[:-1])
                            except ValueError:
                                pass

                # Fallback: check error message for retry delay patterns
                if retry_delay_seconds is None and hasattr(e, 'message'):
                    msg = str(e.message)
                    import re
                    # Look for patterns like "retry after 60 seconds" or "60s"
                    match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                    if match:
                        retry_delay_seconds = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)s', msg)
                        if match:
                            retry_delay_seconds = int(match.group(1))

                # Determine appropriate response based on delay
                if retry_delay_seconds is not None and retry_delay_seconds <= 300:  # 5 minutes or less
                    return f"⚠️ Límite de tasa alcanzado. Por favor, espera {retry_delay_seconds} segundos antes de intentarlo nuevamente."
                else:
                    return "⚠️ Se ha agotado la cuota diaria gratuita de la API de Gemini. La cuota se reinicia a medianoche (hora del Pacífico). Por favor, intenta nuevamente mañana."
            except Exception as parse_error:
                # If parsing fails, fall back to safe message
                print(f"Error parsing 429 details in pensar_respuesta_imagen: {parse_error}")
                return "⚠️ Se ha alcanzado el límite de la API de Gemini. Verifica tu consumo y vuelve a intentar en unos minutos."
        return f"Error de API al analizar imagen: {e.message}"
    except Exception as e:
        return f"Error analizando imagen: {e}"

def pensar_respuesta_audio(ruta_audio: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa archivos de audio recibidos inyectando estrictamente el contexto de la base de datos."""
    try:
        audio_file = _gemini_call_with_fallback(lambda c: c.files.upload(file=ruta_audio))
        contexto_db = obtener_contexto_financiero(usuario_id)

        # OPTIMIZADO: Prompt más corto + max_output_tokens
        prompt_completo = (
            f"{SYSTEM_INSTRUCTION}{contexto_db}\n\n"
            "Escucha el audio. Responde usando SOLO los datos de arriba. NO inventes."
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt_completo, audio_file],
                config=types.GenerateContentConfig(
                    max_output_tokens=1000,
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )
        try:
            audio_file.delete()
        except Exception:
            pass
        return response_text or ""
    except APIError as e:
        if e.code == 429:
            retry_delay_seconds = None
            try:
                # Try to extract retry delay from error details
                if hasattr(e, 'details') and e.details:
                    import json
                    if isinstance(e.details, str):
                        try:
                            details = json.loads(e.details)
                        except:
                            details = {}
                    elif isinstance(e.details, dict):
                        details = e.details
                    else:
                        details = {}

                    if isinstance(details, dict) and 'retryDelay' in details:
                        delay_str = details['retryDelay']
                        if isinstance(delay_str, str) and delay_str.endswith('s'):
                            try:
                                retry_delay_seconds = int(delay_str[:-1])
                            except ValueError:
                                pass

                # Fallback: check error message for retry delay patterns
                if retry_delay_seconds is None and hasattr(e, 'message'):
                    msg = str(e.message)
                    import re
                    # Look for patterns like "retry after 60 seconds" or "60s"
                    match = re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, re.IGNORECASE)
                    if match:
                        retry_delay_seconds = int(match.group(1))
                    else:
                        match = re.search(r'(\d+)s', msg)
                        if match:
                            retry_delay_seconds = int(match.group(1))

                # Determine appropriate response based on delay
                if retry_delay_seconds is not None and retry_delay_seconds <= 300:  # 5 minutes or less
                    return f"⚠️ Límite de tasa alcanzado. Por favor, espera {retry_delay_seconds} segundos antes de intentarlo nuevamente."
                else:
                    return "⚠️ Se ha agotado la cuota diaria gratuita de la API de Gemini. La cuota se reinicia a medianoche (hora del Pacífico). Por favor, intenta nuevamente mañana."
            except Exception as parse_error:
                # If parsing fails, fall back to safe message
                print(f"Error parsing 429 details in pensar_respuesta_audio: {parse_error}")
                return "⚠️ Se ha alcanzado el límite de la API de Gemini. Verifica tu consumo y vuelve a intentar en unos minutos."
        return f"Error de API al procesar audio: {e.message}"
    except Exception as e:
        return f"Error al procesar audio: {e}"