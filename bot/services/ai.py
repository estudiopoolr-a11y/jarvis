"""Lazy bridge from Discord handlers to specialised AI modules."""
from __future__ import annotations

import modules.ai as _ai


def resolve_ai(name: str):
    """Return an AI capability without importing unrelated features."""
    return getattr(_ai, name)


def __getattr__(name: str):
    """Preserve legacy ``from bot.services.ai import name`` imports."""
    return resolve_ai(name)
