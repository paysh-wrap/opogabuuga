"""D122 cushion level controls (user 2026-11-11, per-strategy toggle, default OFF, UNVERIFIED). PURE: Decimal, no I/O.

cushion = equity incl. open P&L − current MLL (the same number as the risk base); its share of the plan's MLL
distance (max loss limit) picks a level:
  NORMAL   ≥ normal_min                       → nothing changes
  REDUCE   reduce_min ≤ share < normal_min     → −reduce_size_minus micros (min 1), trail k − reduce_k_minus
  MINIMAL  minimal_min ≤ share < reduce_min    → 1 micro only, trail k − minimal_k_minus, ≤ minimal_max_trades / day
  STOP     share < minimal_min                → no new entries until the next session (stays STOP all session)
TIGHTEN-ONLY: the size is only ever reduced (never above what every other check allowed — the D121 size tables,
the size-table brake, DLL, MLL worst case, consistency, split, kill switch all still run and are never loosened).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

Level = Literal["NORMAL", "REDUCE", "MINIMAL", "STOP"]


@dataclass(frozen=True)
class CushionLevels:
    normal_min: Decimal
    reduce_min: Decimal
    minimal_min: Decimal
    reduce_size_minus: int
    reduce_k_minus: Decimal
    minimal_k_minus: Decimal
    minimal_max_trades: int


def cushion_share(equity: Decimal, mll: Decimal, max_loss: Decimal) -> Decimal:
    """(equity − MLL) / max loss; a missing/zero max loss → 0 (the strictest level, never a guess upwards)."""
    if max_loss <= 0:
        return Decimal(0)
    return (equity - mll) / max_loss


def cushion_level(share: Decimal, lv: CushionLevels) -> Level:
    if share >= lv.normal_min:
        return "NORMAL"
    if share >= lv.reduce_min:
        return "REDUCE"
    if share >= lv.minimal_min:
        return "MINIMAL"
    return "STOP"


def cushion_contracts(level: Level, n: int, lv: CushionLevels) -> int:
    """Size after the cushion level — never more than n."""
    if level == "NORMAL":
        return n
    if level == "REDUCE":
        return min(n, max(1, n - lv.reduce_size_minus))
    if level == "MINIMAL":
        return min(n, 1)
    return 0


def cushion_k_minus(level: Level, lv: CushionLevels) -> Decimal:
    """How much tighter (k − x) the dynamic trail runs at this level."""
    return {"REDUCE": lv.reduce_k_minus, "MINIMAL": lv.minimal_k_minus, "STOP": lv.minimal_k_minus}.get(
        level, Decimal(0)
    )


def cushion_block(level: Level, trades_today: int, stopped_this_session: bool, lv: CushionLevels) -> str | None:
    """Skip code for a NEW entry, or None. STOP once this session → blocked until the next session."""
    if level == "STOP" or stopped_this_session:
        return "CUSHION_STOP"
    if level == "MINIMAL" and trades_today >= lv.minimal_max_trades:
        return "CUSHION_MAX_TRADES"
    return None
