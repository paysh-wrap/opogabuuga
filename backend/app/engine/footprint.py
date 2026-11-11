"""D98 Order Flow chart: footprint grid, bar delta, cumulative delta (CVD) and session volume profile. PURE (no I/O,
Decimal only). Display / research only — nothing here sizes, gates or places a trade.

HONESTY: the app holds OHLCV bars, not aggressor-side ticks. Without ticks the per-price buy/sell split is ESTIMATED:
  * the bar's volume is spread evenly over the price rows the bar traded through (low..high);
  * buy share = close location in the range ((close − low) / (high − low)); a bar with high == low uses the tick
    rule vs the previous close (up → all buy, down → all sell, unchanged → half/half).
Every result carries `source = "estimated"`. A bar that brings real aggressor-side levels (`BarIn.ticks`) is used
as-is and marked `source = "tick"`, so a real tick feed can be plugged in later without changing callers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, Decimal
from typing import Literal

Source = Literal["estimated", "tick"]
VOL_Q = Decimal("0.01")
VALUE_AREA = Decimal("0.70")


@dataclass(frozen=True)
class TickLevel:
    """Real aggressor-side volume at one price (bid = sold into the bid, ask = bought at the ask)."""

    price: Decimal
    bid: Decimal
    ask: Decimal


@dataclass(frozen=True)
class BarIn:
    time_ms: int  # bar OPEN time
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    v: Decimal
    ticks: tuple[TickLevel, ...] | None = None


@dataclass(frozen=True)
class Level:
    price: Decimal  # row low edge
    bid: Decimal
    ask: Decimal


@dataclass(frozen=True)
class FootprintBar:
    time_ms: int
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    v: Decimal
    levels: tuple[Level, ...]
    delta: Decimal
    cvd: Decimal
    source: Source


@dataclass(frozen=True)
class Profile:
    rows: tuple[tuple[Decimal, Decimal], ...]  # (row price, volume), ascending price
    poc: Decimal | None
    vah: Decimal | None
    val: Decimal | None
    hvn: tuple[Decimal, ...] = field(default_factory=tuple)
    lvn: tuple[Decimal, ...] = field(default_factory=tuple)


def row_of(price: Decimal, row: Decimal) -> Decimal:
    """Low edge of the row that holds `price`."""
    return (price / row).to_integral_value(rounding=ROUND_FLOOR) * row


def _buy_share(b: BarIn, prev_close: Decimal | None) -> Decimal:
    if b.h > b.l:
        return (b.c - b.l) / (b.h - b.l)
    if prev_close is None or b.c == prev_close:
        return Decimal("0.5")
    return Decimal(1) if b.c > prev_close else Decimal(0)


def bar_levels(b: BarIn, row: Decimal, prev_close: Decimal | None) -> tuple[tuple[Level, ...], Source]:
    if b.ticks is not None:
        agg: dict[Decimal, tuple[Decimal, Decimal]] = {}
        for t in b.ticks:
            k = row_of(t.price, row)
            bid, ask = agg.get(k, (Decimal(0), Decimal(0)))
            agg[k] = (bid + t.bid, ask + t.ask)
        return tuple(Level(k, bid, ask) for k, (bid, ask) in sorted(agg.items())), "tick"
    lo, hi = row_of(b.l, row), row_of(b.h, row)
    n = int((hi - lo) / row) + 1
    per = b.v / n
    share = _buy_share(b, prev_close)
    ask = (per * share).quantize(VOL_Q)
    bid = (per - per * share).quantize(VOL_Q)
    return tuple(Level(lo + i * row, bid, ask) for i in range(n)), "estimated"


def footprint(bars: Sequence[BarIn], row: Decimal) -> tuple[FootprintBar, ...]:
    """Per-bar footprint + delta + CVD (cumulative over the bars given — pass one session)."""
    if row <= 0:
        raise ValueError("row size must be > 0")
    out: list[FootprintBar] = []
    cvd = Decimal(0)
    prev: Decimal | None = None
    for b in bars:
        levels, src = bar_levels(b, row, prev)
        delta = sum((x.ask - x.bid for x in levels), Decimal(0))
        cvd += delta
        out.append(FootprintBar(b.time_ms, b.o, b.h, b.l, b.c, b.v, levels, delta, cvd, src))
        prev = b.c
    return tuple(out)


def volume_profile(fp: Sequence[FootprintBar], row: Decimal) -> Profile:
    """Session volume profile: POC (most volume; tie → lower price), 70% value area grown from the POC by the larger
    neighbouring row (tie → upper), HVN = local peaks ≥ 1.5× mean row volume, LVN = local troughs ≤ 0.5× mean that
    lie between two higher rows."""
    vol: dict[Decimal, Decimal] = {}
    for b in fp:
        for x in b.levels:
            vol[x.price] = vol.get(x.price, Decimal(0)) + x.bid + x.ask
    if not vol:
        return Profile((), None, None, None)
    lo, hi = min(vol), max(vol)
    n = int((hi - lo) / row) + 1
    prices = [lo + i * row for i in range(n)]
    vols = [vol.get(p, Decimal(0)) for p in prices]
    total = sum(vols, Decimal(0))
    pi = max(range(n), key=lambda i: (vols[i], -i))
    a = z = pi
    acc = vols[pi]
    while acc < total * VALUE_AREA and (a > 0 or z < n - 1):
        up = vols[z + 1] if z < n - 1 else Decimal(-1)
        dn = vols[a - 1] if a > 0 else Decimal(-1)
        if up >= dn:
            z += 1
            acc += up
        else:
            a -= 1
            acc += dn
    mean = total / n
    hvn = tuple(
        prices[i]
        for i in range(n)
        if vols[i] >= mean * Decimal("1.5")
        and (i == 0 or vols[i] >= vols[i - 1])
        and (i == n - 1 or vols[i] >= vols[i + 1])
    )
    lvn = tuple(
        prices[i]
        for i in range(1, n - 1)
        if vols[i] <= mean * Decimal("0.5")
        and vols[i] < max(vols[:i])
        and vols[i] < max(vols[i + 1 :])
        and vols[i] <= vols[i - 1]
        and vols[i] <= vols[i + 1]
    )
    return Profile(tuple(zip(prices, vols, strict=True)), prices[pi], prices[z], prices[a], hvn, lvn)


def zone(close: Decimal, prior: Profile | None) -> Literal["premium", "discount", "value", "unknown"]:
    """Premium / discount vs the PRIOR session's value area (above VAH = premium, below VAL = discount)."""
    if prior is None or prior.vah is None or prior.val is None:
        return "unknown"
    if close > prior.vah:
        return "premium"
    if close < prior.val:
        return "discount"
    return "value"


def round_levels(low: Decimal, high: Decimal, step: Decimal) -> tuple[Decimal, ...]:
    """Round-number levels (multiples of `step`) inside [low, high]."""
    if step <= 0 or high < low:
        return ()
    first = (low / step).to_integral_value(rounding=ROUND_FLOOR) * step
    if first < low:
        first += step
    out: list[Decimal] = []
    p = first
    while p <= high:
        out.append(p)
        p += step
    return tuple(out)
