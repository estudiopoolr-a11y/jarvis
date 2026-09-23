"""Short-lived confirmations for destructive deterministic commands.

The store deliberately lives in memory.  A bot restart cancels pending work,
which is preferable to replaying a destructive request after a deployment.
"""
from __future__ import annotations

from dataclasses import dataclass
import time


CONFIRMATION_TTL_SECONDS = 300


@dataclass(frozen=True)
class PendingBudgetDeletion:
    year: str
    month: int
    created_at: float


_pending_budget_deletions: dict[str, PendingBudgetDeletion] = {}


def request_budget_deletion(usuario_id: str, year: str, month: int, *, now: float | None = None) -> None:
    """Store one pending deletion per user, replacing an older request."""
    _pending_budget_deletions[usuario_id] = PendingBudgetDeletion(
        year=str(year), month=int(month), created_at=time.time() if now is None else now
    )


def consume_budget_deletion(usuario_id: str, *, now: float | None = None) -> PendingBudgetDeletion | None:
    """Return and remove a valid request; expired requests are discarded."""
    pending = _pending_budget_deletions.pop(usuario_id, None)
    if pending is None:
        return None
    current_time = time.time() if now is None else now
    if current_time - pending.created_at > CONFIRMATION_TTL_SECONDS:
        return None
    return pending


def cancel_budget_deletion(usuario_id: str) -> bool:
    """Cancel a pending deletion, returning whether one existed."""
    return _pending_budget_deletions.pop(usuario_id, None) is not None
