"""HTTP routes.

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


# Cargar routers de forma tolerante a fallos.
# Telegram es crítico; widgets es secundario.
telegram_router = _safe_import_router("app.routes.telegram")
if telegram_router is not None:
    app.include_router(telegram_router)

widgets_router = _safe_import_router("app.routes.widgets")
if widgets_router is not None:
    app.include_router(widgets_router)

# Nuevos routers Kebo y Préstamos
kebo_accounts = _safe_import_router("app.routes.kebo.accounts")
if kebo_accounts is not None:
    app.include_router(kebo_accounts)

kebo_budgets = _safe_import_router("app.routes.kebo.budgets")
if kebo_budgets is not None:
    app.include_router(kebo_budgets)

kebo_txs = _safe_import_router("app.routes.kebo.transactions")
if kebo_txs is not None:
    app.include_router(kebo_txs)

prestamos_router = _safe_import_router("app.routes.prestamos")
if prestamos_router is not None:
    app.include_router(prestamos_router)

__all__ = ["app"]
