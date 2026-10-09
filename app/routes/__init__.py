"""HTTP routes — Enrutador principal consolidado bajo Atomic Design.

Nota de robustez (Vercel serverless):
- En cold start, si alguna ruta/import falla (por dependencias pesadas, keys
  ausentes, etc.), NO debemos tumbar todo el despliegue.
- Por eso, cargamos routers en modo "best-effort" y dejamos el resto para
  que el app principal tenga fallback.
"""

import logging

from app.api import app

logger = logging.getLogger("JARVIS")


def _safe_import_router(module_path: str, router_attr: str = "router"):
    """Intenta importar un módulo y devolver su router (o None)."""
    try:
        module = __import__(module_path, fromlist=[router_attr])
        router = getattr(module, router_attr, None)
        if router is None:
            raise AttributeError(f"{module_path} no expone {router_attr}")
        return router
    except Exception:
        logger.exception("No se pudo cargar %s.%s", module_path, router_attr)
        return None


# Importación de los endpoints activos en la arquitectura simplificada #
telegram_router = _safe_import_router("app.routes.telegram")  # Cargar router de Telegram #
if telegram_router is not None:
    app.include_router(telegram_router)  # Registrar Webhook de Telegram (prefijo ya incluido) #

widgets_router = _safe_import_router("app.routes.widgets")  # Cargar router de Widgets iOS #
if widgets_router is not None:
    app.include_router(widgets_router)  # Registrar Endpoint de Widgets (prefijo ya incluido) #

# Nuevos routers Kebo y Préstamos #
kebo_accounts = _safe_import_router("app.routes.kebo.accounts")  # Cargar router de Cuentas Kebo #
if kebo_accounts is not None:
    app.include_router(kebo_accounts)  # Registrar Cuentas Kebo #

kebo_budgets = _safe_import_router("app.routes.kebo.budgets")  # Cargar router de Presupuestos Kebo #
if kebo_budgets is not None:
    app.include_router(kebo_budgets)  # Registrar Presupuestos Kebo #

kebo_txs = _safe_import_router("app.routes.kebo.transactions")  # Cargar router de Transacciones Kebo #
if kebo_txs is not None:
    app.include_router(kebo_txs)  # Registrar Transacciones Kebo #

prestamos_router = _safe_import_router("app.routes.prestamos")  # Cargar router de Préstamos #
if prestamos_router is not None:
    app.include_router(prestamos_router)  # Registrar Módulo de Préstamos #

__all__ = ["app"]
