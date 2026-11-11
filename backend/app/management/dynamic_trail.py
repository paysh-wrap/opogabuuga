"""D122 intelligent dynamic trailing stop (user 2026-11-11, per-strategy toggle, default OFF, UNVERIFIED). PURE: no I/O,
no clock, Decimal prices.

Once the best price is ≥ activate_r × R in profit:
  breakeven  stop → entry + fee_cover_ticks (the guard's BE price)
  trail      stop → best − max(k × ATR, distance to the last closed swing bar's low/high ± 1 tick); the ATR comes from
             the trade's timeframe built from the heartbeat bars (1m → 5m inside this module), k comes from the profit
             steps (e.g. 2.0 until 2R, 1.5 until 3R, 1.0 after), × low_vol_mult when the current ATR sits in the low
             percentile of its recent history (compression), minus the cushion level's k reduction, never below k_floor
  of_trail   Order Flow (AR type) only: the D101 rule (BE after be_after_r, then behind the last closed 5m/15m candle)
Every candidate is (1) tick-rounded away from the market (looser, never over-claims), (2) pulled back so it is never
closer than min_distance_ticks to the current price, (3) put through `ratchet`: a stop only ever tightens. The take
profit is never touched. These are protective broker stop modifications (D8: no hold delay); a failed modify flattens
and pauses (order manager, §8).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.engine.order_flow import trail_stop
from app.engine.trade_plan import Direction, round_to_tick
from app.indicators.atr import WilderATR
from app.indicators.bars import Bar, HtfAggregator
from app.management.drawdown_guard import ratchet
from app.management.trade_manage import StopMove


@dataclass(frozen=True)
class TrailParams:
    activate_r: Decimal
    min_distance_ticks: int
    atr_tf_min: int
    atr_period: int
    swing_tf_min: int
    steps: tuple[tuple[Decimal | None, Decimal], ...]  # (until_r, k); the last until_r is None
    low_vol_percentile: Decimal
    low_vol_mult: Decimal
    low_vol_lookback: int
    k_floor: Decimal
    fee_cover_ticks: int
    k_minus: Decimal = Decimal(0)  # cushion level reduction (risk/cushion.py)
    of_trail: tuple[int, Decimal] | None = None  # D101 Order Flow AR trail: (candle minutes, be_after_r)


def closed_bars(bars: Sequence[Bar], tf_min: int) -> list[Bar]:
    """Completed tf_min candles built from the (1m) heartbeat bars; the unfinished last candle is left out."""
    agg = HtfAggregator(tf_min)
    out: list[Bar] = []
    for b in bars:
        out += agg.push(b)
    return out


def atr_values(bars: Sequence[Bar], period: int) -> list[Decimal]:
    atr = WilderATR(period)
    return [v for v in (atr.push(b) for b in bars) if v is not None]


def k_for(profit_r: Decimal, steps: Sequence[tuple[Decimal | None, Decimal]]) -> Decimal:
    for until, k in steps:
        if until is None or profit_r < until:
            return k
    return steps[-1][1]


def low_volatility(atrs: Sequence[Decimal], lookback: int, percentile: Decimal) -> bool:
    """True when the current ATR is in the lowest `percentile` of the last `lookback` values (too little history →
    False: no extra tightening on a guess)."""
    if len(atrs) < lookback:
        return False
    window = atrs[-lookback:]
    cur = window[-1]
    rank = Decimal(sum(1 for x in window if x <= cur)) / Decimal(len(window))
    return rank <= percentile


def dynamic_stop(
    direction: Direction,
    entry: Decimal,
    risk_pts: Decimal,
    best: Decimal,
    current_stop: Decimal,
    bars: Sequence[Bar],
    p: TrailParams,
    tick: Decimal,
    last: Decimal | None = None,
) -> StopMove | None:
    """The tightened stop and the rule that chose it, or None when nothing moves (yet)."""
    s = direction.sign
    mfe = (best - entry) * s
    cands: list[tuple[Decimal, str]] = []
    if p.of_trail is not None:
        candle_min, be_r = p.of_trail
        cb = closed_bars(bars, candle_min)
        hl = (cb[-1].h, cb[-1].l) if cb else None
        of = trail_stop(direction, entry, risk_pts, current_stop, best, hl, be_r, p.fee_cover_ticks, tick, last)
        if of != current_stop:
            cands.append((of, "OF_AR_TRAIL"))
    if risk_pts > 0 and mfe >= p.activate_r * risk_pts:
        cands.append((entry + s * p.fee_cover_ticks * tick, "BREAKEVEN"))
        dists: list[tuple[Decimal, str]] = []
        atrs = atr_values(closed_bars(bars, p.atr_tf_min), p.atr_period)
        if atrs:
            k, name = k_for(mfe / risk_pts, p.steps), "ATR"
            if low_volatility(atrs, p.low_vol_lookback, p.low_vol_percentile):
                k, name = k * p.low_vol_mult, "ATR_LOWVOL"
            dists.append((max(k - p.k_minus, p.k_floor) * atrs[-1], name))
        sb = closed_bars(bars, p.swing_tf_min)
        if sb:
            level = sb[-1].l - tick if s > 0 else sb[-1].h + tick
            dists.append(((best - level) * s, "SWING"))
        room = [x for x in dists if x[0] > 0]
        if room:
            d, name = max(room, key=lambda x: x[0])  # the wider of the two: room for the trade's normal noise
            cands.append((best - s * d, name))
    ref = last if last is not None else best
    cap = round_to_tick(ref - s * p.min_distance_ticks * tick, tick, away_from=ref)
    new, rule = current_stop, ""
    for price, name in cands:
        price = round_to_tick(price, tick, away_from=ref)
        capped = (price - cap) * s > 0
        price = cap if capped else price
        tightened = ratchet(new, price, direction)
        if tightened != new:
            new, rule = tightened, name + ("+MIN_DIST" if capped else "")
    return None if new == current_stop else StopMove(new, rule)
