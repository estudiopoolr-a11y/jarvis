import os
import json
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
    obtener_tareas_pendientes, obtener_balance_financiero, obtener_resumen_presupuestos
)
from datetime import datetime

load_dotenv()

# ---------- API Key Rotation Setup ----------
# Support multiple API keys via GEMINI_API_KEYS (comma-separated) or fallback to single GEMINI_API_KEY
_api_keys_str = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
if not _api_keys_str:
    raise ValueError("No Gemini API key found. Set GEMINI_API_KEY or GEMINI_API_KEYS environment variable.")
_API_KEYS = [k.strip() for k in _api_keys_str.split(',') if k.strip()]
if not _API_KEYS:
    raise ValueError("API key list is empty after parsing.")
_key_index = 0  # index of the current key in use

def _get_current_client() -> genai.Client:
    """Return a genai.Client configured with the current API key."""
    return genai.Client(api_key=_API_KEYS[_key_index])

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
Eres JARVIS, un asistente personal de inteligencia artificial de nivel ejecutivo, frío, analítico, eficiente, directo y sin filtros.
Ayudas al usuario a gestionar sus finanzas personales, presupuestos, tareas y análisis de inversiones con rigor absoluto.
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

        # Determinar mes actual para búsquedas
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        mes_actual = meses[datetime.now().month - 1]

        # Construir prompts para búsqueda web
        prompt_tasas = f"""
Eres un asesor financiero de Colombia. Busca información actualizada sobre:
1. Tasas de interés actuales de CDT en bancos colombianos (Bancolombia, Davivienda, Banco de Bogotá, Banco Popular, Scotiabank)
2. Tasas de fondos de inversión colectiva yemonedaros
3. Cifras actualizadas a {mes_actual} 2026

Responde con una tabla comparativa clara de tasas por banco y plazo (30, 60, 90, 180 y 360 días).
"""

        prompt_apps = f"""
Eres un experto en fintech de Colombia. Busca información actualizada sobre:
1. Mejores apps para invertir en Colombia en 2026 (Tyba, Trii, Hapi, Nequi, otros)
2. Montos mínimos de inversión
3. Comisiones y costos
4. Si tienen protección de Fogafín
5. Tipos de productos disponibles (acciones, ETF, fondos, CDT digitales)

Responde con una comparativa clara de apps.
"""

        # Realizar búsquedas web en paralelo
        resultados_tasas = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_tasas,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                )
            ).text
        ) or "No se pudo obtener información de tasas."

        resultados_apps = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_apps,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                )
            ).text
        ) or "No se pudo obtener información de apps."

        # Generar respuesta personalizada con recomendación
        prompt_respuesta = f"""Eres JARVIS, un asesor financiero ejecutivo frío y analítico.

CONTEXTO DEL USUARIO:
- Balance neto: ${balance_neto:,.0f} COP
- Capacidad de inversión recomendada (20%): ${capacidad_inversion:,.0f} COP
- Ingresos totales: ${ingresos:,.0f} COP
- Gastos totales: ${gastos:,.0f} COP

INFORMACIÓN DE TASAS CDT COLOMBIA:
{resultados_tasas}

INFORMACIÓN DE APPS DE INVERSIÓN COLOMBIA:
{resultados_apps}

PREGUNTA DEL USUARIO: {prompt_usuario}

INSTRUCCIONES:
1. Genera una respuesta completa en español
2. Incluye una tabla de tasas CDT por banco
3. Incluye comparativa de apps recomendadas
4. Da una recomendación personalizada según la capacidad del usuario
5. Si el balance es menor a $500.000, sugiere empezar con Nequi o apps sin monto mínimo
6. Si el balance es mayor a $1.000.000, sugiere diversificar: CDT + app de inversión
7. IMPORTANTE: Al final, incluye una sección "TAREAS CREADAS" con exactamente estas tareas a crear:
   - Formato: TAREAS CREADAS: [tarea1] | [tarea2] | [tarea3]
   - Máximo 4 tareas
   - Las tareas deben ser acciones concretas como:
     * "Crear cuenta en Tyba para invertir desde $1.000"
     * "Comparar tasas CDT en Bancolombia y Davivienda"
     * "Revisar tasas de CDT en 30 días"
     * "Separar ${int(capacidad_inversion):,} para fondo de emergencia"
"""

        respuesta = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_respuesta,
                config=types.GenerateContentConfig(
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        ) or "No se pudo generar la asesoría."

        # Extraer tareas de la respuesta y crearlas en Firebase
        if "TAREAS CREADAS:" in respuesta:
            parte_tareas = respuesta.split("TAREAS CREADAS:")[1].split("---")[0].split("___")[0].strip()
            tareas = [t.strip() for t in parte_tareas.split("|") if t.strip()]

            for tarea in tareas[:4]:  # Máximo 4 tareas
                if len(tarea) > 5 and len(tarea) < 100:
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

    # =========================================
    # 6. NADA MATCHEÓ → USAR GEMINI
    # =========================================
    # Solo para preguntas complejas que no matchearon ningún parser
    return None

def pensar_respuesta(prompt_usuario: str, usuario_id: str = "default") -> str:
    """Responde preguntas generales inyectando el contexto de Firebase y Google Search."""
    try:
        contexto_db = obtener_contexto_financiero(usuario_id)
        prompt_completo = f"{SYSTEM_INSTRUCTION}{contexto_db}\n\nMensaje del usuario: {prompt_usuario}"

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_completo,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
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
                    tools=[{"google_search": {}}]
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
        prompt = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            "El usuario te envía esta imagen. Si se trata de un recibo, factura o comprobante de pago: "
            "1. Extrae el monto total, el establecimiento/comercio y la categoría aproximada. "
            "2. Responde confirmando los datos extraídos y realiza un juicio analítico sobre el gasto.\n\n"
            f"Comentario del usuario: {prompt_adicional}"
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, imagen_file],
                config=types.GenerateContentConfig(
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

        prompt_completo = (
            f"{SYSTEM_INSTRUCTION}{contexto_db}\n\n"
            "Escucha el audio adjunto del usuario. Si pregunta por sus finanzas, gastos, historial o transacciones, "
            "DEBES responderle utilizando ÚNICAMENTE los datos reales de la base de datos proporcionados arriba. "
            "Prohibido inventar montos, fechas o categorías que no estén en esa lista."
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt_completo, audio_file],
                config=types.GenerateContentConfig(
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