"""D58 PM_FADE (user button, paper first): afternoon VWAP-band fade on MNQ on days NOISE has not traded. PURE.

Research: docs/results/session10/five_year/stops_250.py (pm with mode "fixed"): with NOISE ($250 stop) on MNQ
2021-11 → 2026-10, 1 micro: 66% Pro 25K eval pass / 32% bust. Rules (minute index k from 09:30 ET, engine/noise.py):
  running VWAP_k = Σ typical·volume / Σ volume over today's RTH bars ≤ k (typical = (h + l + c) / 3)
  sd_k = population standard deviation of (close_i − VWAP_i) for i ≤ k
  close_k > VWAP_k + band·sd_k → SHORT; close_k < VWAP_k − band·sd_k → LONG (at market)
  target = VWAP_k (rounded toward entry), stop = entry ∓ stop_pts; skip when the target is < min_target_ticks away.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.engine.trade_plan import Direction, round_to_tick


@dataclass(frozen=True)
class FadePlan:
    direction: Direction
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    risk_pts: Decimal
    rr: Decimal
    vwap: Decimal
    sd: Decimal


def running_vwaps(bars: Sequence[tuple[Decimal, Decimal, Decimal, Decimal]]) -> list[Decimal | None]:
    """VWAP after each bar (h, l, c, v); None until volume is seen."""
    pv = vol = Decimal(0)
    out: list[Decimal | None] = []
    for h, low, c, v in bars:
        pv += (h + low + c) / 3 * v
        vol += v
        out.append(pv / vol if vol > 0 else None)
    return out


def dev_sd(closes: Sequence[Decimal], vwaps: Sequence[Decimal | None]) -> Decimal | None:
    """Population std of close − VWAP over the bars that have a VWAP."""
    d = [c - w for c, w in zip(closes, vwaps, strict=True) if w is not None]
    if not d:
        return None
    m = sum(d, Decimal(0)) / len(d)
    return (sum(((x - m) ** 2 for x in d), Decimal(0)) / len(d)).sqrt()


def decide(
    *,
    close: Decimal,
    vwap: Decimal | None,
    sd: Decimal | None,
    band: Decimal,
    tick: Decimal,
    stop_pts: Decimal,
    min_target_ticks: int,
) -> FadePlan | str | None:
    """None = no signal; "TARGET_TOO_CLOSE" = a signal whose VWAP target is too near (ends the day, like research)."""
    if vwap is None or sd is None or sd <= 0:
        return None
    if close > vwap + band * sd:
        d = Direction.SHORT
    elif close < vwap - band * sd:
        d = Direction.LONG
    else:
        return None
    tp = round_to_tick(vwap, tick, toward=close)
    reward = (tp - close) * d.sign
    if reward < min_target_ticks * tick:
        return "TARGET_TOO_CLOSE"
    stop = close - d.sign * stop_pts
    return FadePlan(d, close, stop, tp, stop_pts, (reward / stop_pts).quantize(Decimal("0.01")), vwap, sd)
