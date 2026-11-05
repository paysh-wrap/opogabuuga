"""Account selector (§12): trade N of M accounts in priority order; only selected + armed + not paused."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    id: int
    priority: int
    selected: bool
    armed: bool
    paused: bool
    stage: str
    sim: bool


def select(cands: list[Candidate], n: int, any_live: bool) -> list[Candidate]:
    """Priority order, max N (1–5). If any household account is LIVE, sim accounts are blocked (§10)."""
    n = max(1, min(5, n))
    ok = [c for c in cands if c.selected and c.armed and not c.paused and not (any_live and c.sim)]
    return sorted(ok, key=lambda c: (c.priority, c.id))[:n]


def exposure_warning(n: int) -> str | None:
    return f"{n} accounts on one signal = {n}× correlated exposure" if n > 1 else None
