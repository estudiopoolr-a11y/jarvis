"""HTTP routes. Importing this package registers all endpoints on app.api.app."""
from app.api import app
from app.routes import admin, comando, cron, dashboard, kebo, prestamos, widgets  # noqa: F401

__all__ = ["app"]
