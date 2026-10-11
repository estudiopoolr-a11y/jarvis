"""Backward-compatible, lazy public surface for NLP and Gemini."""
from __future__ import annotations
from importlib import import_module
import json
import re

_EXPORTS = {
    "MODEL_NAME": "modules.gemini.client", "SYSTEM_INSTRUCTION": "modules.gemini.client",
    "_API_KEYS": "modules.gemini.client", "_esperar_por_rpm": "modules.gemini.client",
    "_gemini_call_with_fallback": "modules.gemini.client", "_key_index": "modules.gemini.client",
    "_asesorar_inversion": "modules.gemini.inversion", "_es_intencion_inversion": "modules.gemini.inversion",
    "analizar_inversion": "modules.gemini.inversion", "pensar_respuesta": "modules.gemini.think",
    "analizar_intencion_mensaje": "modules.gemini.think",
    "pensar_respuesta_audio": "modules.gemini.think", "pensar_respuesta_imagen": "modules.gemini.think",
    "transcribir_audio": "modules.gemini.transcribe", "_normalizar_monto": "modules.nlp.amounts",
    "PALABRAS_CLAVE_INTENCION": "modules.nlp.models", "ItemIntencion": "modules.nlp.models",
    "procesar_intencion_natural": "modules.nlp.router",
}
for _name in (
    "_parse_ajustar_balance", "_parse_analisis_financiero", "_parse_bloque_presupuesto_mensual", "_parse_borrar_presupuesto", "_parse_busqueda", "_parse_completar_tarea", "_parse_configuracion_masiva", "_parse_editar_presupuesto", "_parse_listar_categorias", "_parse_meta", "_parse_pago_fijo", "_parse_perfil", "_parse_presupuesto", "_parse_presupuesto_modificar", "_parse_presupuesto_multiple", "_parse_recordatorio", "_parse_renombrar_presupuesto", "_parse_sobrante", "_parse_split", "_parse_subcategoria", "_parse_tarea", "_parse_tasa_cambio", "_parse_transaccion", "_parse_transaccion_futura", "_parse_ver_presupuesto", "_parse_transferencia",
):
    _EXPORTS[_name] = "modules.nlp.parsers"

__all__ = list(_EXPORTS) + ["analizar_intencion_mensaje"]


def __getattr__(name: str):
    """Lazy import resolver: dynamically imports names listed in _EXPORTS."""
    if name in _EXPORTS:
        module_path = _EXPORTS[name]
        from importlib import import_module
        module = import_module(module_path)
        obj = getattr(module, name)
        globals()[name] = obj
        return obj
    raise AttributeError(f"module 'modules.ai' has no attribute '{name}'")


def pensar_respuesta(texto: str) -> str:
    """Interface for thinking/generating a natural response."""
    from modules.gemini.think import pensar_respuesta as _pensar
    return _pensar(texto)

def analizar_intencion_mensaje(texto: str) -> dict:
    """
    Clasifica el texto libre en intenciones estructuradas usando Gemini API.
    Retorna dict con intención y entidades extraídas.
    """
    try:
        # Prompt de sistema para Gemini
        system_prompt = """
Eres un clasificador de intenciones financieras para JARVIS.
Clasifica el mensaje del usuario en UNA de estas intenciones exactas:

1. REGISTRAR_PRESTAMO: 
   - tipo: "prestado" (yo doy) | "cobrado" (me deben) | "pagado" (ya lo pagaron)
   - persona: nombre de la persona
   - monto: número flotante (ej: 50000.0)
   - concepto/nota: texto opcional
   - Ejemplo: "Le presté $50k a Carlos" -> {"intent":"REGISTRAR_PRESTAMO","tipo":"prestado","persona":"Carlos","monto":50000.0}

2. REGISTRAR_GASTO:
   - monto: número flotante
   - categoria: string (ej: "Transporte", "Comida")
   - cuenta: string opcional (ej: "Nequi", "Bancolombia")
   - descripcion: string opcional
   - Ejemplo: "Gasté 15k en taxi con Nequi" -> {"intent":"REGISTRAR_GASTO","monto":15000.0,"categoria":"Transporte","cuenta":"Nequi","descripcion":"taxi"}

3. ACTUALIZAR_CUENTA_KEBO:
   - cuenta: string (nombre de cuenta)
   - nuevo_saldo: número flotante
   - Ejemplo: "Ajustar saldo Nequi a 250mil" -> {"intent":"ACTUALIZAR_CUENTA_KEBO","cuenta":"Nequi","nuevo_saldo":250000.0}

4. CONSULTAR_BALANCE:
   - filtro: "general" | "gastos_mes" | "prestamos_por_cobrar"

5. CONVERSACION_GENERAL: Para todo lo demás

IMPORTANTE: 
- Siempre retorna un JSON válido
- Si no estás seguro, usa CONVERSACION_GENERAL
- Los montos deben ser números (sin símbolos de moneda)
- Responde SOLO con el JSON, sin texto adicional
"""

        # Llamada a Gemini API usando el cliente existente
        from modules.gemini.client import _gemini_call_with_fallback
        from google.genai import types
        
        def _call_gemini(client):
            return client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=[system_prompt, texto],
                config=types.GenerateContentConfig(
                    max_output_tokens=500,
                    temperature=0.1
                )
            ).text
        
        response = _gemini_call_with_fallback(_call_gemini)

        # Parsear respuesta JSON con fallback
        try:
            # Limpiar la respuesta para extraer solo el JSON
            response_clean = response.strip()
            # Buscar el primer { y último } para extraer el JSON
            start_idx = response_clean.find('{')
            end_idx = response_clean.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_clean[start_idx:end_idx]
                result = json.loads(json_str)
            else:
                result = json.loads(response_clean)
            
            # Validar estructura mínima
            if "intent" not in result:
                return {"intent": "CONVERSACION_GENERAL"}

            # Si Gemini responde de forma demasiado genérica para consultas financieras,
            # priorizar el parser por regex ya que es más estable en mensajes tipo
            # "q cuentas tengo" / "cuantas cuentas tengo" / "balance".
            intent = result.get("intent")
            if intent == "CONVERSACION_GENERAL":
                fallback = _fallback_regex_parsing(texto)
                if fallback.get("intent") != "CONVERSACION_GENERAL":
                    return fallback

            # Establecer valores por defecto para campos comunes según la intención
            if intent == "REGISTRAR_PRESTAMO":
                result.setdefault("tipo", "prestado")
                result.setdefault("persona", "desconocido")
                result.setdefault("monto", 0.0)
                result.setdefault("concepto", "")
                result.setdefault("nota", "")
            elif intent == "REGISTRAR_GASTO":
                result.setdefault("monto", 0.0)
                result.setdefault("categoria", "Sin categoría")
                result.setdefault("cuenta", "")
                result.setdefault("descripcion", "")
            elif intent == "ACTUALIZAR_CUENTA_KEBO":
                result.setdefault("cuenta", "")
                result.setdefault("nuevo_saldo", 0.0)
            elif intent == "CONSULTAR_BALANCE":
                result.setdefault("filtro", "general")
            
            return result
        except (json.JSONDecodeError, Exception) as e:
            # Si falla el parsing JSON, intentar extraer información con regex como fallback
            return _fallback_regex_parsing(texto)
            
    except Exception as e:
        # Log del error (en producción usar logging adecuado)
        print(f"[NLP Error] Fallo en análisis de intención: {e}")
        # Forzamos el fallback de regex si ocurre cualquier excepción en la llamada a Gemini
        return _fallback_regex_parsing(texto)


def _fallback_regex_parsing(texto: str) -> dict:
    """
    Fallback usando regex para extraer intenciones cuando falla el JSON de Gemini.
    """
    # Patrones para REGISTRAR_PRESTAMO
    prestamo_patterns = [
        (r'(?:le|te|me)\s*prest[ée]\s*\$?(\d+[kK]?\.?\d*)\s*(?:a|para)\s+([a-zA-Z\s]+)', 
         lambda m, t: {
             "intent": "REGISTRAR_PRESTAMO", 
             "tipo": "prestado", 
             "persona": m.group(2).strip(), 
             "monto": _parse_monto(m.group(1))
         }, re.IGNORECASE),
        (r'(?:me\s+deben?|[a-zA-Z\s]+)\s+me\s+debe?\s*\$?(\d+[kK]?\.?\d*)', 
         lambda m, t: {
             "intent": "REGISTRAR_PRESTAMO", 
             "tipo": "cobrado", 
             "persona": "alguien", 
             "monto": _parse_monto(m.group(1))
         }, re.IGNORECASE),
        (r'(?:[a-zA-Z\s]+)\s+me\s+pag[óo]\s*\$?(\d+[kK]?\.?\d*)', 
         lambda m, t: {
             "intent": "REGISTRAR_PRESTAMO", 
             "tipo": "pagado", 
             "persona": "alguien", 
             "monto": _parse_monto(m.group(1))
         }, re.IGNORECASE)
    ]
    
    for pattern, constructor, flags in prestamo_patterns:
        match = re.search(pattern, texto, flags)
        if match:
            try:
                result = constructor(match, texto)
                # Asegurar que tengamos todos los campos requeridos
                if "persona" not in result or not result["persona"].strip():
                    result["persona"] = "desconocido"
                return result
            except Exception:
                continue
    
    # Patrones para REGISTRAR_GASTO
    gasto_patterns = [
        (r'(?:gast[ée]|pag[óo]|compr[ée])\s*\$?(\d+[kK]?\.?\d*)\s*(?:mil)?\s*(?:en|en\s+([a-zA-Z\s]+))?\s*(?:con\s+([a-zA-Z\s]+))?', 
         lambda m, t: {
             "intent": "REGISTRAR_GASTO", 
             "monto": _parse_monto(m.group(1) + ("k" if "mil" in t.lower() or "k" in m.group(1).lower() else "")),
             "categoria": m.group(2).strip() if m.group(2) else "Sin categoría",
             "cuenta": m.group(3).strip() if m.group(3) else "",
             "descripcion": ""
         }, re.IGNORECASE)
    ]
    
    for pattern, constructor, flags in gasto_patterns:
        match = re.search(pattern, texto, flags)
        if match:
            try:
                return constructor(match, texto)
            except Exception:
                continue
    
    # Patrones para ACTUALIZAR_CUENTA_KEBO
    actualizar_patterns = [
        (r'(?:ajustar|poner|actualizar)\s+(?:saldo\s+)?([a-zA-Z\s]+?)\s+(?:a|en|en\s+)\s*\$?(\d+[kK]?\.?\d*)', 
         lambda m, t: {
             "intent": "ACTUALIZAR_CUENTA_KEBO",
             "cuenta": m.group(1).strip(),
             "nuevo_saldo": _parse_monto(m.group(2))
         }, re.IGNORECASE),
        (r'(?:cuenta\s+)?([a-zA-Z\s]+?)\s+(?:a|en|en\s+)\s*\$?(\d+[kK]?\.?\d*)', 
         lambda m, t: {
             "intent": "ACTUALIZAR_CUENTA_KEBO",
             "cuenta": m.group(1).strip(),
             "nuevo_saldo": _parse_monto(m.group(2))
         }, re.IGNORECASE)
    ]
    
    for pattern, constructor, flags in actualizar_patterns:
        match = re.search(pattern, texto, flags)
        if match:
            try:
                return constructor(match, texto)
            except Exception:
                continue
    
    # Patrones para CONSULTAR_BALANCE
    consulta_patterns = [
        (r'(?:qu[eé]|q)\s*(?:cuantas?|cuántas?)\s+cuentas?\s+tengo',
         lambda m, t: {"intent": "CONSULTAR_BALANCE", "filtro": "general"},
         re.IGNORECASE),
        (r'(?:cuantas?|cuántas?)\s+cuentas?\s+tengo',
         lambda m, t: {"intent": "CONSULTAR_BALANCE", "filtro": "general"},
         re.IGNORECASE),
        (r'(?:qu[eé]|q)\s*(?:cuentas?|cuenta)\s+tengo',
         lambda m, t: {"intent": "CONSULTAR_BALANCE", "filtro": "general"},
         re.IGNORECASE),
        (r'(?:balance|saldo)(?:\s+general)?(?:\s+de\s+(?:mis\s+)?cuentas?)?',
         lambda m, t: {"intent": "CONSULTAR_BALANCE", "filtro": "general"},
         re.IGNORECASE),
        (r'(?:gastos?|gaste[ds]?)\s+(?:este\s+)?mes', 
         lambda m, t: {"intent": "CONSULTAR_BALANCE", "filtro": "gastos_mes"},
         re.IGNORECASE),
        (r'(?:qu[eé]\s+dinero\s+me\s+deben?|prestamos?\s+por\s+cobrar)', 
         lambda m, t: {"intent": "CONSULTAR_BALANCE", "filtro": "prestamos_por_cobrar"},
         re.IGNORECASE)
    ]
    
    for pattern, constructor, flags in consulta_patterns:
        match = re.search(pattern, texto, flags)
        if match:
            try:
                return constructor(match, texto)
            except Exception:
                continue
    
    # Si nada coincide, retornar conversación general
    return {"intent": "CONVERSACION_GENERAL", "texto": texto}


def _parse_monto(monto_str: str) -> float:
    """Convierte una cadena de monto a float, manejando k/K y mil como miles."""
    monto_str = monto_str.strip().lower()
    if monto_str.endswith('k') or 'mil' in monto_str:
        # Extract number part
        num_part = re.sub(r'[^\d.]', '', monto_str)
        try:
            return float(num_part) * 1000
        except ValueError:
            return 0.0
    else:
        # Remover posibles comas y puntos que no sean decimales
        monto_str = re.sub(r'[^\d.]', '', monto_str)
        try:
            return float(monto_str)
        except ValueError:
            return 0.0
