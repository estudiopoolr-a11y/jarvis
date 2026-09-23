"""Backward-compatible, lazy public surface for NLP and Gemini."""
from __future__ import annotations
from importlib import import_module

_EXPORTS = {
    "MODEL_NAME": "modules.gemini.client", "SYSTEM_INSTRUCTION": "modules.gemini.client",
    "_API_KEYS": "modules.gemini.client", "_esperar_por_rpm": "modules.gemini.client",
    "_gemini_call_with_fallback": "modules.gemini.client", "_key_index": "modules.gemini.client",
    "_asesorar_inversion": "modules.gemini.inversion", "_es_intencion_inversion": "modules.gemini.inversion",
    "analizar_inversion": "modules.gemini.inversion", "pensar_respuesta": "modules.gemini.think",
    "pensar_respuesta_audio": "modules.gemini.think", "pensar_respuesta_imagen": "modules.gemini.think",
    "transcribir_audio": "modules.gemini.transcribe", "_normalizar_monto": "modules.nlp.amounts",
    "PALABRAS_CLAVE_INTENCION": "modules.nlp.models", "ItemIntencion": "modules.nlp.models",
    "procesar_intencion_natural": "modules.nlp.router",
}
for _name in (
    "_parse_ajustar_balance", "_parse_analisis_financiero", "_parse_bloque_presupuesto_mensual", "_parse_borrar_presupuesto", "_parse_busqueda", "_parse_completar_tarea", "_parse_configuracion_masiva", "_parse_editar_presupuesto", "_parse_listar_categorias", "_parse_meta", "_parse_pago_fijo", "_parse_perfil", "_parse_presupuesto", "_parse_presupuesto_modificar", "_parse_presupuesto_multiple", "_parse_recordatorio", "_parse_renombrar_presupuesto", "_parse_sobrante", "_parse_split", "_parse_subcategoria", "_parse_tarea", "_parse_tasa_cambio", "_parse_transaccion", "_parse_transaccion_futura", "_parse_ver_presupuesto", "_parse_transferencia",
):
    _EXPORTS[_name] = "modules.nlp.parsers"

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    if name != "_key_index":
        globals()[name] = value
    return value
