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
    guardar_meta, obtener_metas, eliminar_meta, actualizar_progreso_meta, proyectar_meta,
    modificar_presupuesto, guardar_pago_fijo, obtener_pagos_fijos, eliminar_pago_fijo,
    guardar_perfil, obtener_perfil
)
from modules.database_v2 import (
    registrar_transaccion_v2, obtener_balance_v2, obtener_presupuestos_v2,
    listar_cuentas, crear_cuenta, actualizar_presupuesto_categoria,
    registrar_transferencia, listar_metas_v2, guardar_meta_v2, agregar_aporte_meta,
    listar_recurrentes, guardar_recurrente, obtener_alertas_presupuesto
)
from datetime import datetime

# OPTIMIZACIÓN: Cache para búsquedas web (1 hora TTL)
_busquedas_cache = {}
_CACHE_WEB_TTL = 3600

# OPTIMIZACIÓN: Cliente de Gemini reutilizable por key
_clientes_cache = {}

# OPTIMIZACIÓN: Rate limiter local para evitar golpear RPM (15/min en flash-lite)
# Tracking de timestamps de las últimas llamadas
_llamadas_recientes = []
_RPM_MAX = 14  # Dejamos 1 de margen respecto al límite real de 15
_RPM_WINDOW = 60  # segundos

def _esperar_por_rpm():
    """Espera si estamos cerca del límite de Requests Per Minute.
    Esto evita los 429 por throttling, que es el caso más común.
    """
    global _llamadas_recientes
    ahora = time.time()

    # Limpiar llamadas fuera de la ventana de 60s
    _llamadas_recientes = [t for t in _llamadas_recientes if ahora - t < _RPM_WINDOW]

    # Si ya estamos en el límite, esperar hasta que la más vieja salga de la ventana
    if len(_llamadas_recientes) >= _RPM_MAX:
        mas_vieja = _llamadas_recientes[0]
        espera = _RPM_WINDOW - (ahora - mas_vieja) + 0.5  # +0.5s de margen
        if espera > 0:
            print(f"⏳ Rate limiter local: esperando {espera:.1f}s para respetar RPM={_RPM_MAX}")
            time.sleep(espera)
            # Re-evaluar después de esperar
            ahora = time.time()
            _llamadas_recientes = [t for t in _llamadas_recientes if ahora - t < _RPM_WINDOW]

    # Registrar esta llamada
    _llamadas_recientes.append(time.time())


def transcribir_audio(ruta_audio: str) -> str:
    """Transcribe audio a texto usando Gemini (solo transcripción, sin análisis)."""
    try:
        # Subir el archivo
        audio_file = _gemini_call_with_fallback(lambda c: c.files.upload(file=ruta_audio))

        # Prompt simple para transcripción
        prompt_transcripcion = "Transcribe exactamente lo que se dice en este audio. Solo devuelve el texto transcrito, sin comentarios."

        # Obtener transcripción
        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt_transcripcion, audio_file],
                config=types.GenerateContentConfig(
                    max_output_tokens=500,
                    temperature=0.1,  # Bajo para precisión
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )

        # Limpiar el archivo
        try:
            audio_file.delete()
        except Exception:
            pass

        return response_text.strip() if response_text else ""
    except Exception as e:
        print(f"Error en transcripción: {e}")
        return ""


def _manejar_error_api(e: APIError, contexto: str = "general") -> str:
    """Maneja errores de API de Gemini de forma centralizada."""
    import re as _re

    if e.code == 429:
        retry_seconds = None
        msg = str(e.message) if hasattr(e, 'message') else str(e)

        # Extraer retry delay
        match = _re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, _re.IGNORECASE)
        if match:
            retry_seconds = int(match.group(1))
        else:
            match = _re.search(r'(\d+)s', msg)
            if match:
                retry_seconds = int(match.group(1))

        if retry_seconds and retry_seconds <= 300:
            return f"⏳ Límite de velocidad (RPM). Espera {retry_seconds}s o vuelve en 1-2 minutos."
        return "⚠️ Cuota diaria de Gemini agotada. Se reinicia a medianoche (hora Colombia)."

    # Otros errores de API
    msg = str(e.message) if hasattr(e, 'message') else str(e)

    # Casos especiales con mensajes amigables
    if "high demand" in msg.lower():
        return "⏳ Gemini tiene alta demanda en este momento. Espera 1-2 minutos e intenta de nuevo."
    if "upload" in msg.lower() and "terminated" in msg.lower():
        return "⏳ Error con el archivo. Intenta enviar el audio/imagen de nuevo."
    if "quota" in msg.lower() or "limit" in msg.lower():
        return "⚠️ Cuota de Gemini agotada. Se reinicia a medianoche (hora Colombia)."

    # Mensaje genérico para otros errores
    print(f"Error de API en {contexto}: {msg}")
    return "⏳ Error temporal. Espera 1-2 minutos e intenta de nuevo."


def _manejar_error_generico(e: Exception, contexto: str = "general") -> str:
    """Maneja errores genéricos de forma centralizada."""
    msg = str(e)
    print(f"Error en {contexto}: {msg}")

    if "upload" in msg.lower() and "terminated" in msg.lower():
        return "⏳ Error con el archivo. Intenta enviar el audio/imagen de nuevo."
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return "⏳ Tiempo de espera agotado. Intenta de nuevo."
    if "connection" in msg.lower() or "network" in msg.lower():
        return "⏳ Error de conexión. Verifica tu internet e intenta de nuevo."

    return "⏳ Error temporal. Espera 1-2 minutos e intenta de nuevo."


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

    Diferencia entre:
    - RPM (rate per minute): recoverable en ~60s
    - Cuota diaria: solo se recupera a medianoche
    """
    import re as _re

    retries = len(_API_KEYS)
    errores_429 = []

    for intento in range(retries):
        try:
            # Respetar rate limit local antes de hacer la llamada
            _esperar_por_rpm()
            return callable(_get_current_client())
        except APIError as e:
            if e.code == 429:
                errores_429.append(str(e))
                # Intentar extraer retry delay del mensaje
                retry_seconds = None
                msg = str(e.message) if hasattr(e, 'message') else str(e)
                match = _re.search(r'(?:retry.*?|after\s*)?(\d+)\s*second', msg, _re.IGNORECASE)
                if match:
                    retry_seconds = int(match.group(1))

                if intento < retries - 1:
                    # Pequeña pausa antes de rotar (backoff exponencial)
                    if retry_seconds and retry_seconds <= 120:
                        print(f"⏳ 429 con retry={retry_seconds}s, esperando...")
                        time.sleep(min(retry_seconds, 5))  # máx 5s por intento
                    _rotate_key()
                    continue
                # Último intento falló
                if retry_seconds and retry_seconds <= 300:
                    # Es RPM, no cuota diaria
                    raise Exception(
                        f"⏳ **Límite de velocidad alcanzado (RPM).**\n\n"
                        f"Demasiadas solicitudes por minuto. Gemini permite {int(_RPM_MAX)} req/min por key.\n"
                        f"• Espera **{retry_seconds} segundos** y vuelve a intentar.\n"
                        f"• Este límite se libera automáticamente cada minuto."
                    )
                # No hay retry delay → probablemente cuota diaria agotada
                raise Exception(
                    "⚠️ **Cuota diaria de Gemini agotada en todas las keys.**\n\n"
                    "Las 5 API keys han alcanzado su límite diario.\n"
                    "• Espera hasta la medianoche (hora Colombia) para que se resetee la cuota\n"
                    "• O agrega nuevas API keys en el archivo .env (GEMINI_API_KEYS)\n"
                    "• Por ahora, los comandos básicos (!finanzas, !tareas) seguirán funcionando."
                )
            # For non-429 errors, re-raise immediately
            raise

    # Si llegamos aquí sin retornar, todas las keys dieron 429
    raise Exception(
        "⚠️ **Todas las API keys están bloqueadas por rate limit.**\n"
        f"Espera 1-2 minutos e intenta de nuevo. ({len(errores_429)} keys probadas)"
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


def _parse_presupuesto_modificar(texto: str) -> dict | None:
    """Detecta 'sube Women a 400000' o 'cambia Alimentación a 100000'."""
    import re
    texto_lower = texto.lower()

    # Patrones: "sube <cat> a <monto>", "cambia <cat> a <monto>", "baja <cat> a <monto>"
    patrones = [
        r'(?:sube|aumenta|incrementa)\s+(\w+)\s+(?:a|hasta)\s+([\d,.]+)',
        r'(?:baja|reduce|disminuye)\s+(\w+)\s+(?:a|hasta)\s+([\d,.]+)',
        r'(?:cambia|modifica|actualiza)\s+(\w+)\s+(?:a|hasta)\s+([\d,.]+)',
        r'(?:sube|aumenta)\s+(\w+)\s+([\d,.]+)\s*(?:más|adicional)?',
        r'(?:baja|reduce)\s+(\w+)\s+([\d,.]+)',
    ]

    for i, patron in enumerate(patrones):
        match = re.search(patron, texto_lower)
        if match:
            cat = match.group(1).strip()
            # Filtrar palabras que no son categorías
            if cat in ["el", "la", "los", "las", "de", "del", "en", "un", "una", "mi", "tu", "el", "presupuesto"]:
                continue
            try:
                monto = float(match.group(2).replace(',', ''))
                accion = "subir" if i < 1 or i == 3 else ("bajar" if i < 2 or i == 4 else "cambiar")
                return {"categoria": cat.title(), "nuevo_limite": monto, "accion": accion}
            except ValueError:
                continue
    return None


def _parse_pago_fijo(texto: str) -> dict | None:
    """Detecta 'pago fijo arriendo 1500000 día 5'."""
    import re
    texto_lower = texto.lower()

    # Patrón: "pago fijo <nombre> <monto> [día <N>]"
    patron = r'pago\s+fijo\s+(\w+(?:\s+\w+)?)\s+([\d,.]+)(?:\s+d[ií]a\s+(\d+))?'
    match = re.search(patron, texto_lower)
    if match:
        nombre = match.group(1).strip()
        try:
            monto = float(match.group(2).replace(',', ''))
            dia = int(match.group(3)) if match.group(3) else 1
            return {"nombre": nombre.title(), "monto": monto, "dia_mes": dia}
        except ValueError:
            pass
    return None


def _parse_perfil(texto: str) -> dict | None:
    """Detecta 'mi nombre es X', 'vivo en Y'."""
    import re
    texto_lower = texto.lower()

    # "mi nombre es Daniel"
    m = re.search(r'mi nombre es\s+(\w+)', texto_lower)
    if m:
        return {"nombre": m.group(1).title()}

    # "vivo en Bogotá"
    m = re.search(r'vivo en\s+(\w+(?:\s+\w+)?)', texto_lower)
    if m:
        return {"ciudad": m.group(1).title()}

    # "tengo X años"
    m = re.search(r'tengo\s+(\d+)\s+(?:a[ñn]os)', texto_lower)
    if m:
        return {"edad": int(m.group(1))}

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

    # Mapeo de meses (compartido entre varios parsers)
    _MESES = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        "sep": 9, "ago": 8, "dic": 12, "ene": 1, "feb": 2,
        "mar": 3, "abr": 4, "jun": 6, "jul": 7, "oct": 10, "nov": 11
    }
    _NOMBRES_MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

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
    # 4a. GESTIÓN DE CUENTAS (estructura Kebo)
    # =========================================
    if any(k in texto_lc for k in ["cuenta", "cuentas"]):
        # Listar cuentas: "mis cuentas", "lista mis cuentas", "ver cuentas"
        if any(k in texto_lc for k in ["mis", "lista", "mostrar", "ver", "cuales", "cuáles"]):
            cuentas = listar_cuentas(usuario_id)
            if not cuentas:
                return "💳 No tienes cuentas registradas. Di: 'crea cuenta [nombre]' para agregar una."
            msg = "💳 **Tus cuentas:**\n"
            total = 0.0
            for c in cuentas:
                icono = c.get("icono", "💳")
                balance = float(c.get("balance", 0))
                total += balance
                signo = "+" if balance >= 0 else ""
                msg += f"  {icono} {c.get('nombre')}: {signo}${balance:,.0f}\n"
            msg += f"\n💰 **Balance total: ${total:,.0f}**"
            return msg

        # Crear cuenta: "crea cuenta Nequi", "nueva cuenta débito 200k"
        crear_match = re.search(
            r'(?:crea|crear|nueva|agrega|agregar)\s+cuenta\s+(?:llamada\s+|de\s+)?(.+?)(?:\s+con\s+([\d,.]+))?\s*$',
            texto_lc
        )
        if crear_match:
            resto = crear_match.group(1).strip()
            saldo_inicial = 0.0
            if crear_match.group(2):
                saldo_inicial = float(crear_match.group(2).replace(',', ''))

            # Detectar tipo
            tipo = "cash"
            icono = "💵"
            color = "#10b981"
            if any(k in resto for k in ["credito", "crédito", "credit"]):
                tipo = "credit"
                icono = "💳"
                color = "#ef4444"
            elif any(k in resto for k in ["debito", "débito", "debit", "nequi", "daviplata", "bancolombia"]):
                tipo = "debit"
                icono = "💜"
                color = "#8b5cf6"
            elif any(k in resto for k in ["ahorro", "ahorros", "savings"]):
                tipo = "savings"
                icono = "🏦"
                color = "#3b82f6"

            # Limpiar nombre (quitar la palabra "tipo X")
            nombre = re.sub(r'\s+tipo\s+\w+', '', resto).strip()
            nombre = nombre.title()

            if not nombre:
                return "⚠️ Necesito el nombre. Ej: 'crea cuenta Nequi tipo débito'"

            cuenta_id = crear_cuenta(usuario_id, nombre, tipo, saldo_inicial, icono, color)
            if cuenta_id:
                saldo_str = f" con ${saldo_inicial:,.0f}" if saldo_inicial else ""
                return f"✅ Cuenta creada: {icono} **{nombre}** ({tipo}){saldo_str}."
            else:
                return "⚠️ Error al crear la cuenta."

        # Ver saldo de cuenta específica: "saldo nequi", "cuanto tengo en efectivo"
        saldo_match = re.search(r'(?:saldo|balance|cuanto\s+tengo|cuánto\s+tengo)\s+(?:en\s+|de\s+)?(.+)', texto_lc)
        if saldo_match:
            nombre_buscar = saldo_match.group(1).strip().title()
            cuentas = listar_cuentas(usuario_id)
            for c in cuentas:
                if nombre_buscar.lower() in c.get('nombre', '').lower():
                    balance = float(c.get("balance", 0))
                    icono = c.get("icono", "💳")
                    signo = "+" if balance >= 0 else ""
                    return f"{icono} **{c.get('nombre')}**: {signo}${balance:,.0f}"
            return f"⚠️ No encontré la cuenta '{nombre_buscar}'."

    # =========================================
    # 4b. VER PRESUPUESTOS DE UN MES ESPECÍFICO
    # =========================================
    if "presupuesto" in texto_lc or "presupuestos" in texto_lc:
        # Detectar mes mencionado
        mes_mencionado = None
        for nombre, num in _MESES.items():
            if nombre in texto_lc:
                mes_mencionado = num
                break

        if mes_mencionado:
            from datetime import datetime
            import re
            anio_actual = datetime.now().year
            anio_match = re.search(r'20(?:24|25|26)', texto_lc)
            anio = int(anio_match.group()) if anio_match else anio_actual

            mes_formato = f"{anio}-{mes_mencionado:02d}"
            try:
                # Intentar con parámetro mes (versión nueva)
                presupuestos_mes = obtener_resumen_presupuestos(usuario_id, mes_formato)
            except TypeError:
                # Fallback: versión vieja sin parámetro mes
                presupuestos_mes = obtener_resumen_presupuestos(usuario_id)

            if presupuestos_mes:
                total = sum(presupuestos_mes.values())
                msg = f"📊 **PRESUPUESTOS {_NOMBRES_MESES[mes_mencionado]} {anio}**\n\n"
                for cat, limite in presupuestos_mes.items():
                    msg += f"• {cat}: ${limite:,.0f}\n"
                msg += f"\n💰 **Total: ${total:,.0f}**"
                return msg
            else:
                return f"📋 No hay presupuestos registrados para {_NOMBRES_MESES[mes_mencionado]} {anio}."

    # =========================================
    # 4c. COMPARAR MESES
    # =========================================
    # Detecta: "comparar vs agosto", "compáralo con julio", "agosto vs septiembre", etc.
    if any(k in texto_lc for k in ["compar", "vs", "versus"]) or \
       ("respecto" in texto_lc and "mes" in texto_lc) or \
       ("con" in texto_lc and any(m in texto_lc for m in _MESES.keys())):

        # Buscar meses mencionados en el texto
        meses_encontrados = []
        for nombre, num in _MESES.items():
            if nombre in texto_lc:
                meses_encontrados.append(num)

        from datetime import datetime
        mes_actual = datetime.now().month

        if len(meses_encontrados) >= 2:
            # Dos meses mencionados: "agosto vs septiembre"
            mes1, mes2 = meses_encontrados[0], meses_encontrados[-1]
        elif len(meses_encontrados) == 1:
            # Un mes mencionado: comparar contra el otro
            # Si dice "respecto al de agosto" o "vs agosto" → mes1=agosto, mes2=actual
            # Si solo dice "comparar" → mes1=mes anterior, mes2=actual
            if "respecto" in texto_lc or "con" in texto_lc or "vs" in texto_lc:
                # El mentioned month es el de referencia, comparar contra actual
                mes1 = mes_actual
                mes2 = meses_encontrados[0]
            else:
                # Solo dice "comparar" sin especificar → vs mes anterior
                mes1 = mes_actual - 1 if mes_actual > 1 else 12
                mes2 = mes_actual
        else:
            # No se detectó ningún mes → intentar con mes anterior
            meses_encontrados = [mes_actual - 1 if mes_actual > 1 else 12]

        if len(meses_encontrados) >= 1:
            from datetime import datetime
            import re
            anio_actual = datetime.now().year
            anio_match = re.search(r'20(?:24|25|26)', texto_lc)
            anio = int(anio_match.group()) if anio_match else anio_actual

            mes1_fmt = f"{anio}-{mes1:02d}"
            mes2_fmt = f"{anio}-{mes2:02d}"

            # Llamadas defensivas: si la versión vieja no acepta mes, usar sin mes
            try:
                bal1, ing1, gas1, _ = obtener_balance_financiero(usuario_id, mes1_fmt)
            except TypeError:
                bal1, ing1, gas1, _ = obtener_balance_financiero(usuario_id)
            try:
                bal2, ing2, gas2, _ = obtener_balance_financiero(usuario_id, mes2_fmt)
            except TypeError:
                bal2, ing2, gas2, _ = obtener_balance_financiero(usuario_id)
            try:
                pres1 = obtener_resumen_presupuestos(usuario_id, mes1_fmt)
            except TypeError:
                pres1 = obtener_resumen_presupuestos(usuario_id)
            try:
                pres2 = obtener_resumen_presupuestos(usuario_id, mes2_fmt)
            except TypeError:
                pres2 = obtener_resumen_presupuestos(usuario_id)

            # Comparativa de PRESUPUESTOS por categoría
            n1 = _NOMBRES_MESES[mes1][:10]
            n2 = _NOMBRES_MESES[mes2][:10]

            # Unir todas las categorías de ambos meses
            todas_cats = set(pres1.keys()) | set(pres2.keys())

            if todas_cats:
                msg = f"📊 **PRESUPUESTOS: {n1} vs {n2} {anio}**\n\n"
                msg += f"```\n"
                msg += f"{'Categoría':<15}| {n1:<10} | {n2:<10} | Var\n"
                msg += f"{'='*14}+{'='*12}+{'='*12}+{'='*6}\n"

                total_pres1 = 0
                total_pres2 = 0

                for cat in sorted(todas_cats):
                    p1 = pres1.get(cat, 0)
                    p2 = pres2.get(cat, 0)
                    total_pres1 += p1
                    total_pres2 += p2

                    # Variación
                    if p1 > 0:
                        var = ((p2 - p1) / p1) * 100
                        var_str = f"{var:+.0f}%"
                    elif p2 > 0:
                        var_str = "NUEVO"
                    else:
                        var_str = "-"

                    emoji = "📈" if p2 > p1 else "📉" if p2 < p1 else "➡️"

                    msg += f"{cat:<15}| ${p1:>8,.0f} | ${p2:>8,.0f} | {var_str}\n"

                # Totales
                if len(todas_cats) > 1:
                    var_total = ((total_pres2 - total_pres1) / max(total_pres1, 1)) * 100
                    msg += f"{'-'*14}+{'-'*12}+{'-'*12}+{'-'*6}\n"
                    msg += f"{'TOTAL':<15}| ${total_pres1:>8,.0f} | ${total_pres2:>8,.0f} | {var_total:+.0f}%\n"
                msg += "```"
                return msg
            else:
                return f"📋 No hay presupuestos registrados para {n1} ni {n2} {anio}."

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

    # 5c. Transacción (gasto/ingreso) - USA NUEVA ESTRUCTURA KEBO
    transaccion = _parse_transaccion(texto_lc)
    if transaccion:
        monto = transaccion["monto"]
        cat = transaccion["categoria"]
        tipo = transaccion["tipo"]
        # Mapear: gasto -> expense, ingreso -> income
        tipo_db = "expense" if tipo == "gasto" else "income"
        tx_id = registrar_transaccion_v2(usuario_id, tipo_db, monto, cat, "Registro por voz", "Efectivo")
        if tx_id:
            if tipo == "gasto":
                return f"💸 Gasto registrado: **-${monto:,.0f}** en *{cat}*."
            else:
                return f"💰 Ingreso registrado: **+${monto:,.0f}** en *{cat}*."
        else:
            return "⚠️ Error al registrar transacción. Intenta de nuevo."

    # 5d. Presupuesto
    presupuesto_data = _parse_presupuesto(texto_lc)
    if presupuesto_data:
        establecer_presupuesto(usuario_id, presupuesto_data["categoria"], presupuesto_data["limite"])
        return f"🎯 Presupuesto: *{presupuesto_data['categoria']}* = **${presupuesto_data['limite']:,.0f}**"

    # 5d-2. Modificar presupuesto (sube/baja/cambia)
    mod_pres = _parse_presupuesto_modificar(texto_lc)
    if mod_pres:
        cat = mod_pres["categoria"]
        nuevo = mod_pres["nuevo_limite"]
        accion = mod_pres["accion"]
        modificar_presupuesto(usuario_id, cat, nuevo)
        emoji = "📈" if accion == "subir" else "📉" if accion == "bajar" else "🔄"
        return f"{emoji} **Presupuesto {accion}do:** *{cat}* = **${nuevo:,.0f}**"

    # =========================================
    # 5e. TRANSFERENCIAS ENTRE CUENTAS
    # =========================================
    transfer_match = re.search(
        r'(?:mov[íi]|transfer[íi]|mand[áa])\s+(?:de\s+)?(\d+[\d,.]*)\s*(?:k|m)?\s*(?:de\s+)?(\w+)\s*(?:a|hacia|para)\s+(\w+)',
        texto_lc
    )
    if not transfer_match:
        # Intentar: "mover 100k de nequi a efectivo"
        transfer_match = re.search(
            r'mover\s+(\d+[\d,.]*)\s*(?:k|m)?\s+de\s+(\w+)\s+a\s+(\w+)',
            texto_lc
        )
    if transfer_match:
        monto = float(transfer_match.group(1).replace(',', ''))
        origen = transfer_match.group(2).strip().title()
        destino = transfer_match.group(3).strip().title()
        # Extender abreviaturas
        if origen.lower() in ['efect', 'efectivo', 'cash']: origen = 'Efectivo'
        if destino.lower() in ['efect', 'efectivo', 'cash']: destino = 'Efectivo'
        tx_id, msg = registrar_transferencia(usuario_id, origen, destino, monto, "Transferencia por voz")
        if tx_id:
            return f"✅ {msg}"
        else:
            return f"⚠️ {msg}"

    # =========================================
    # 5f. METAS DE AHORRO
    # =========================================
    # Ver metas: "mis metas", "ver metas"
    if any(k in texto_lc for k in ["meta", "metas", "ahorro"]) and any(k in texto_lc for k in ["mis", "ver", "mostrar", "lista", "cuales"]):
        metas = listar_metas_v2(usuario_id)
        if not metas:
            return "🎯 No tienes metas de ahorro. Di: 'crea meta [nombre] $[monto]'"
        msg = "🎯 **Tus metas de ahorro:**\n"
        for m in metas:
            icono = "✅" if m.get("completada") else "🔄"
            nombre = m.get("nombre", "")
            obj = float(m.get("monto_objetivo", 0))
            cur = float(m.get("current_amount", 0))
            pct = m.get("porcentaje", 0)
            msg += f"  {icono} **{nombre}**: ${cur:,.0f} / ${obj:,.0f} ({pct}%)\n"
        return msg

    # Crear meta: "crea meta viaje 500k"
    crear_meta_match = re.search(r'crea(?:r)?\s+meta\s+(?:de\s+)?(\w+(?:\s+\w+)?)\s+\$?(\d+[\d,.]*)', texto_lc)
    if crear_meta_match:
        nombre = crear_meta_match.group(1).strip().title()
        monto = float(crear_meta_match.group(2).replace(',', ''))
        # Detectar fecha límite si se menciona
        fecha_limite = ""
        meta_id = guardar_meta_v2(usuario_id, nombre, monto, fecha_limite)
        if meta_id:
            return f"🎯 **Meta creada:** *{nombre}* = **${monto:,.0f}**"
        else:
            return "⚠️ Error al crear la meta."

    # Aportar a meta: "aportar 50k a viaje", "suma 100k meta ahorro"
    aporte_match = re.search(r'(?:aportar|sumar|agregar)\s+(\d+[\d,.]*)\s*(?:k|m)?\s+(?:a\s+)?(?:meta\s+)?(\w+)', texto_lc)
    if not aporte_match:
        aporte_match = re.search(r'meta\s+(\w+)\s+(?:con\s+)?(?:aportar\s+)?(\d+[\d,.]*)', texto_lc)
    if aporte_match:
        monto = float(aporte_match.group(1).replace(',', ''))
        nombre_meta = aporte_match.group(2).strip().title()
        ok, msg = agregar_aporte_meta(usuario_id, nombre_meta, monto)
        if ok:
            return f"✅ {msg}"
        else:
            return f"⚠️ {msg}"

    # =========================================
    # 5g. RECURRENTES
    # =========================================
    # Ver recurrentes: "mis pagos fijos", "pagos recurrentes"
    if any(k in texto_lc for k in ["recurrente", "recurrentes", "pago fijo", "pagos fijos", "suscripcion", "suscripciones"]):
        if any(k in texto_lc for k in ["mis", "ver", "mostrar", "lista", "cuales"]):
            recurrentes = listar_recurrentes(usuario_id)
            if not recurrentes:
                return "🔁 No tienes pagos recurrentes configurados."
            msg = "🔁 **Pagos recurrentes:**\n"
            for r in recurrentes:
                nombre = r.get("nombre", "")
                monto = float(r.get("monto", 0))
                freq = r.get("frecuencia", "monthly")
                dia = r.get("dia", 1)
                freq_emoji = "📅" if freq == "monthly" else "📆" if freq == "biweekly" else "📆"
                msg += f"  {freq_emoji} **{nombre}**: ${monto:,.0f} / "
                msg += f"día {dia}" if freq == "monthly" else freq
                msg += "\n"
            return msg

    # Crear recurrente: "cada 15 me sale arriendo 1.5M"
    recurrente_match = re.search(
        r'cada\s+(\d+)\s+(?:me\s+)?(?:sale|toca|paga)\s+(\w+)\s+(\d+[\d,.]*)',
        texto_lc
    )
    if not recurrente_match:
        recurrente_match = re.search(
            r'(?:crea|registrar)\s+(?:pago\s+)?recurrente\s+(?:de\s+)?(\w+)\s+(\d+[\d,.]*)\s+(?:el\s+)?(?:día?\s+)?(\d+)',
            texto_lc
        )
    if recurrente_match:
        dia = int(recurrente_match.group(1) if texto_lc.startswith("cada") else recurrente_match.group(3))
        nombre = recurrente_match.group(2).strip().title()
        monto = float(recurrente_match.group(2) if texto_lc.startswith("cada") else recurrente_match.group(2).replace(',', ''))
        rec_id = guardar_recurrente(usuario_id, nombre, monto, "monthly", dia)
        if rec_id:
            return f"🔁 **Recurrente creado:** *{nombre}* = ${monto:,.0f} el día {dia} de cada mes"
        else:
            return "⚠️ Error al crear recurrente."

    # =========================================
    # 5h. ALERTAS DE PRESUPUESTO
    # =========================================
    # "alertas", "cómo voy de presupuesto", "presupuestos alertas"
    if any(k in texto_lc for k in ["alerta", "alertas", "aviso", "avisos"]) or \
       ("presupuesto" in texto_lc and "como" in texto_lc) or \
       ("como" in texto_lc and "voy" in texto_lc and "presupuesto" in texto_lc):
        alertas = obtener_alertas_presupuesto(usuario_id)
        if not alertas:
            return "✅ **Sin alertas.** Todos tus presupuestos van bien."
        msg = "⚠️ **Alertas de presupuesto:**\n"
        for a in alertas:
            msg += f"  {a['mensaje']}\n"
        return msg

    # =========================================
    # 5a. Completar tarea
    pago_fijo = _parse_pago_fijo(texto_lc)
    if pago_fijo:
        guardar_pago_fijo(usuario_id, pago_fijo["nombre"], pago_fijo["monto"], pago_fijo["dia_mes"])
        return f"⏰ **Pago fijo creado:** {pago_fijo['nombre']} = ${pago_fijo['monto']:,.0f} (día {pago_fijo['dia_mes']} de cada mes)"

    # 5d-4. Perfil de usuario
    perfil_data = _parse_perfil(texto_lc)
    if perfil_data:
        guardar_perfil(usuario_id, **perfil_data)
        campo = list(perfil_data.keys())[0]
        valor = list(perfil_data.values())[0]
        return f"👤 **Perfil actualizado:** {campo} = {valor}"

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
        return _manejar_error_api(e, contexto="pensar_respuesta")
    except Exception as e:
        return _manejar_error_generico(e, contexto="pensar_respuesta")

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
        return _manejar_error_api(e, contexto=f"análisis de {ticker}")
    except Exception as e:
        return _manejar_error_generico(e, contexto=f"análisis de {ticker}")

def pensar_respuesta_imagen(ruta_imagen: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa una imagen (factura, recibo, captura) extrayendo transacciones automáticamente."""
    imagen_file = None
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

        return response_text or "Imagen procesada sin texto resultante."
    except APIError as e:
        return _manejar_error_api(e, contexto="imagen")
    except Exception as e:
        return _manejar_error_generico(e, contexto="imagen")
    finally:
        if imagen_file is not None:
            try:
                imagen_file.delete()
            except Exception:
                pass

def pensar_respuesta_audio(ruta_audio: str, prompt_adicional: str = "", usuario_id: str = "default") -> str:
    """Procesa archivos de audio recibidos inyectando estrictamente el contexto de la base de datos.

    OPTIMIZADO: Una sola llamada API (sube audio + genera respuesta con contexto).
    """
    audio_file = None
    try:
        # Subir audio una sola vez
        audio_file = _gemini_call_with_fallback(lambda c: c.files.upload(file=ruta_audio))
        contexto_db = obtener_contexto_financiero(usuario_id)

        # Construir prompt: system + contexto + instrucción
        prompt_base = "Responde de forma concisa. Solo usa los datos proporcionados."
        if prompt_adicional:
            prompt_completo = f"{SYSTEM_INSTRUCTION}\n{contexto_db}\n{prompt_base}\n\nContexto adicional: {prompt_adicional}"
        else:
            prompt_completo = f"{SYSTEM_INSTRUCTION}\n{contexto_db}\n{prompt_base}"

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt_completo, audio_file],
                config=types.GenerateContentConfig(
                    max_output_tokens=1000,
                    temperature=0.3,
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )
        return response_text.strip() if response_text else "No pude procesar el audio. Intenta de nuevo."
    except APIError as e:
        return _manejar_error_api(e, contexto="audio")
    except Exception as e:
        return _manejar_error_generico(e, contexto="audio")
    finally:
        # SIEMPRE limpiar el archivo subido para evitar "Upload has already been terminated"
        if audio_file is not None:
            try:
                audio_file.delete()
            except Exception:
                pass