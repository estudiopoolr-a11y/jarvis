"""HTTP routes. Importing this package registers all endpoints on app.api.app."""
from app.api import app
from app.routes import admin, comando, cron, dashboard, kebo, prestamos, widgets, telegram  # noqa: F401

# Include routers that are defined
app.include_router(widgets.router)
app.include_router(telegram.router)

__all__ = ["app"]
