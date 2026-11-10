"""Order blocks (OB). PURE, Decimal, closed bars only, no lookahead.

Definition (all numbers from config, see ObConfig):
  displacement bar = a bar whose body >= body_atr * ATR(atr_period) AND whose close breaks the highest high (bull) / lowest
  low (bear) of the previous `swing_bars` bars.
  bullish OB = the last BEARISH bar before a bullish displacement (zone = its [low, high]); bearish OB = mirror.
  The OB is CONFIRMED on the close of the displacement bar (event time = that bar's close_ms, never the OB bar's).
  Mitigated (dead) once any later closed bar closes through the far edge of the zone (below the low of a bull OB,
  above the high of a bear OB). Expired after max_age_bars.
`live_blocks(bars)` returns the OBs alive after the last bar. A bar's own displacement is only used after it closed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.indicators.atr import WilderATR
from app.indicators.bars import Bar


@dataclass(frozen=True)
class ObConfig:
    atr_period: int = 14
    body_atr: Decimal = Decimal("1.0")
    swing_bars: int = 10
    max_age_bars: int = 120


@dataclass(frozen=True)
class OrderBlock:
    bullish: bool
    low: Decimal
    high: Decimal
    origin_ms: int  # open_ms of the OB candle
    confirm_ms: int  # close_ms of the displacement bar (event timestamp)
    confirm_index: int


def find_blocks(bars: Sequence[Bar], cfg: ObConfig) -> list[OrderBlock]:
    """Every OB confirmed in `bars` that is still alive after the last bar."""
    atr = WilderATR(cfg.atr_period)
    alive: list[OrderBlock] = []
    for i, b in enumerate(bars):
        a_prev = atr.value  # ATR known BEFORE this bar (no lookahead into the bar itself)
        atr.push(b)
        # mitigation / expiry first (only by bars strictly after confirmation)
        alive = [
            ob
            for ob in alive
            if i - ob.confirm_index <= cfg.max_age_bars and not (b.c < ob.low if ob.bullish else b.c > ob.high)
        ]
        if a_prev is None or a_prev <= 0 or i < cfg.swing_bars + 1:
            continue
        body = abs(b.c - b.o)
        if body < cfg.body_atr * a_prev:
            continue
        window = bars[i - cfg.swing_bars : i]
        up = b.bullish and b.c > max(x.h for x in window)
        dn = b.bearish and b.c < min(x.l for x in window)
        if not (up or dn):
            continue
        for j in range(i - 1, max(i - 1 - cfg.swing_bars, -1), -1):
            x = bars[j]
            if (up and x.bearish) or (dn and x.bullish):
                alive.append(OrderBlock(up, x.l, x.h, x.open_ms, b.close_ms, i))
                break
    return alive


def blocked_by_opposing(
    direction_sign: int, price: Decimal, blocks: Sequence[OrderBlock], max_dist: Decimal
) -> OrderBlock | None:
    """FILTER: a LONG (sign +1) is blocked when a live bearish OB sits within max_dist ABOVE price (supply in the way,
    or price already inside it); a SHORT when a live bullish OB sits within max_dist BELOW price."""
    for ob in blocks:
        if direction_sign > 0 and not ob.bullish and ob.low - price <= max_dist and price <= ob.high:
            return ob
        if direction_sign < 0 and ob.bullish and price - ob.high <= max_dist and price >= ob.low:
            return ob
    return None


def anchor_stop(
    direction_sign: int, entry: Decimal, stop: Decimal, blocks: Sequence[OrderBlock], buffer: Decimal, tick: Decimal
) -> Decimal:
    """STOP ANCHOR: nearest live same-side OB below (long) / above (short) the entry; stop = its far edge -/+ buffer, tick
    rounded away from entry. Returned ONLY if it is closer to entry than `stop` (risk never widens); else `stop` is kept."""
    best: Decimal | None = None
    for ob in blocks:
        if direction_sign > 0 and ob.bullish and ob.low < entry:
            cand = ((ob.low - buffer) / tick).to_integral_value(rounding="ROUND_FLOOR") * tick
            if cand < entry and (best is None or cand > best):
                best = cand
        if direction_sign < 0 and not ob.bullish and ob.high > entry:
            cand = ((ob.high + buffer) / tick).to_integral_value(rounding="ROUND_CEILING") * tick
            if cand > entry and (best is None or cand < best):
                best = cand
    if best is None:
        return stop
    tighter = best > stop if direction_sign > 0 else best < stop
    return best if tighter else stop
