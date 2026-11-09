"""D55 OPEN_DRIVE (user button, NOT verified → paper accounts only): opening-drive pullback on MNQ. PURE.

Research (docs/results/session9/agents/meanrev/mr.py, g_drive(0.35, 1.0)): 2019–2023 139 trades 51.8% win PF 1.00;
2024–2026 108 trades 58.3% win PF 1.29. R:R ≈ 0.95 (below the 1.5 pillar — the user's explicit choice).
Rules (minute index k from 09:30 ET, as in engine/noise.py):
  at the close of the 09:59 bar (k = 29): move = close − RTH open; trade only if |move| ≥ frac × average RTH range
  of the previous `range_days` sessions (≥ min_range_days known). Direction = sign(move).
  extreme = 09:30–09:59 high (long) / low (short); leg = |extreme − open|
  limit entry = extreme − d·0.382·leg (fills only when traded through by 1 tick), valid until the bar opening 12:30
  stop = extreme − d·0.786·leg; target = entry + target_frac·(extreme − entry); time stop on the 13:00 bar's close.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.engine.trade_plan import Direction, round_to_tick


@dataclass(frozen=True)
class DriveSetup:
    direction: Direction
    entry: Decimal  # resting limit
    stop: Decimal
    take_profit: Decimal
    risk_pts: Decimal
    rr: Decimal
    move: Decimal
    avg_range: Decimal


def avg_range(ranges: Sequence[Decimal], days: int, min_days: int) -> Decimal | None:
    """Mean RTH high−low of the last `days` sessions; None with fewer than `min_days`."""
    last = list(ranges)[-days:]
    if len(last) < min_days:
        return None
    return sum(last, Decimal(0)) / len(last)


def setup(
    *,
    rth_open: Decimal,
    drive_high: Decimal,
    drive_low: Decimal,
    close_0959: Decimal,
    avg_rng: Decimal | None,
    frac: Decimal,
    entry_retrace: Decimal,
    stop_retrace: Decimal,
    target_frac: Decimal,
    tick: Decimal,
    min_risk_ticks: int = 4,
) -> DriveSetup | None:
    if avg_rng is None or avg_rng <= 0:
        return None
    move = close_0959 - rth_open
    if abs(move) < frac * avg_rng or move == 0:
        return None
    d = Direction.LONG if move > 0 else Direction.SHORT
    s = d.sign
    ext = drive_high if d is Direction.LONG else drive_low
    leg = abs(ext - rth_open)
    entry = round_to_tick(ext - s * entry_retrace * leg, tick, toward=rth_open)
    stop = round_to_tick(ext - s * stop_retrace * leg, tick, away_from=entry)
    tp = round_to_tick(entry + target_frac * (ext - entry), tick, toward=entry)
    risk = (entry - stop) * s
    reward = (tp - entry) * s
    if risk < min_risk_ticks * tick or reward <= 0:
        return None
    return DriveSetup(d, entry, stop, tp, risk, (reward / risk).quantize(Decimal("0.01")), move, avg_rng)
