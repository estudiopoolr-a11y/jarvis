"""Kebo HTTP routes. Importing this package registers the endpoints."""
from app.routes.kebo import accounts, budgets, export, reports, seed, transactions  # noqa: F401

__all__ = ["accounts", "budgets", "export", "reports", "seed", "transactions"]
