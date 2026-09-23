"""NLP package exports without importing the router at package import time."""
from importlib import import_module

_EXPORTS = {
    "procesar_intencion_natural": "modules.nlp.router",
    "_normalizar_monto": "modules.nlp.amounts",
    "ItemIntencion": "modules.nlp.models",
    "PALABRAS_CLAVE_INTENCION": "modules.nlp.models",
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
