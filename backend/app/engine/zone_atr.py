"""D111 ATR-zone Order Flow type (docs/results/session18/order_flow/ICEBERG_ATR_RULES.md). PURE (no I/O, no clock).

The trader's "iceberg / stop event" needs CME MBO data we do not have: the event here is an iceberg PROXY — a
footprint absorption / large-volume cluster sent by pine/Paytience_OrderFlow.pine (kind ZONE, zone = the event bar's
range, ATR = Wilder ATR(14) of the last closed 5-minute bar). UNVERIFIED.

POSITION  (event proven by a move out of the zone): LONG entry ≥ zone_hi + entry_atr_pct × ATR; stop = zone_lo −
          stop_atr_pct × ATR (back through the whole zone and 115% beyond); target = rr × risk (or the AMT level).
          Trail ONLY to a new same-direction event (its 115% line), ratchet only, NEVER to breakeven.
REVERSION (fade the run-away back to the zone): LONG at k ATR below zone_lo (k ∈ 1/2/3), target = zone_lo, stop at
          the next ATR line (k + 1); A+ = entry in front of a PRIOR event. Exit on an opposing event.
Filters: dead zone (relative volume), last minutes of RTH, price-change confirm, TICK program-day no-fade, min event
size. Every R:R / risk rule of the Order Flow plan still applies (rr_min ≥ 1.5, TP ≤ 3R).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.engine.order_flow import OrderFlowPlan, OrderFlowSkip
from app.engine.trade_plan import Direction, round_to_tick


@dataclass(frozen=True)
class ZoneFields:
    signal: str | None = None  # EVENT | POSITION | REVERSION
    zone_hi: Decimal | None = None
    zone_lo: Decimal | None = None
    event_size: Decimal | None = None
    atr5: Decimal | None = None
    rev_level: int | None = None
    prior_hi: Decimal | None = None
    prior_lo: Decimal | None = None
    rvol: Decimal | None = None
    range5_atr: Decimal | None = None
    tick: int | None = None


@dataclass(frozen=True)
class ZoneRules:
    modes: frozenset[str] = frozenset({"POSITION"})
    entry_atr_pct: Decimal = Decimal("1.15")
    stop_atr_pct: Decimal = Decimal("1.15")
    reversion_levels: frozenset[int] = frozenset({1, 2, 3})
    a_plus_only: bool = False
    min_event_size: int = 150
    dead_zone_filter: bool = True
    dead_zone: tuple[int, int] = (11 * 60 + 15, 13 * 60 + 30)  # ET minutes of day
    dead_zone_min_rvol: Decimal = Decimal("1.5")
    last_minutes_filter: bool = True
    rth_close: int = 16 * 60
    last_minutes: int = 10
    price_change_confirm: bool = True
    price_change_pct: Decimal = Decimal("0.70")
    tick_filter: bool = True
    tick_extreme: int = 1000


def _z(code: str, detail: str, layer: str = "ZONE") -> OrderFlowSkip:
    return OrderFlowSkip(f"OF_ZONE_{code}", detail, layer)


def check_zone(
    direction: Direction, entry: Decimal, minute_et: int, f: ZoneFields, r: ZoneRules
) -> OrderFlowSkip | None:
    """None = every active ZONE gate agrees for an entry alert (POSITION / REVERSION)."""
    if f.signal not in ("POSITION", "REVERSION"):
        return _z("NOT_ENTRY", f"zone signal {f.signal}")
    if f.signal not in r.modes:
        return _z("MODE_OFF", f"{f.signal} not in {sorted(r.modes)}")
    if f.zone_hi is None or f.zone_lo is None or f.atr5 is None or f.zone_hi < f.zone_lo or f.atr5 <= 0:
        return _z("NO_EVENT", "event zone / ATR(5m) missing", "EVENT")
    if f.event_size is None or f.event_size < r.min_event_size:
        return _z("EVENT_SMALL", f"event size {f.event_size} < {r.min_event_size} (iceberg proxy)", "EVENT")
    if r.last_minutes_filter and r.rth_close - r.last_minutes <= minute_et < r.rth_close:
        return _z("LAST_MINUTES", f"no new trades in the last {r.last_minutes} min of RTH", "TIME")
    in_dead = r.dead_zone_filter and r.dead_zone[0] <= minute_et < r.dead_zone[1]
    if in_dead and (f.rvol is None or f.rvol < r.dead_zone_min_rvol):
        return _z("DEAD_ZONE", f"relative volume {f.rvol} < {r.dead_zone_min_rvol} in the dead zone", "TIME")
    s = direction.sign
    if f.signal == "POSITION":
        line = (f.zone_hi if s > 0 else f.zone_lo) + s * r.entry_atr_pct * f.atr5
        if (entry - line) * s < 0:
            return _z("NOT_PROVEN", f"entry {entry} not beyond the {r.entry_atr_pct} ATR line {line}")
        return None
    # REVERSION: LONG fades a drop below the zone, SHORT a rise above it
    edge = f.zone_lo if s > 0 else f.zone_hi
    k = f.rev_level
    if k is None or k not in r.reversion_levels or (edge - entry) * s < k * f.atr5 * Decimal("0.95"):
        return _z("REV_LEVEL", f"entry {entry} not at a {sorted(r.reversion_levels)} ATR level (k={k})")
    if r.price_change_confirm and (f.range5_atr is None or f.range5_atr < r.price_change_pct):
        return _z("NO_PRICE_CHANGE", f"5-min range {f.range5_atr} ATR < {r.price_change_pct}", "CONFIRM")
    if r.tick_filter and f.tick is not None and -s * f.tick >= r.tick_extreme:
        return _z("PROGRAM_DAY", f"TICK {f.tick} — program day, no fade", "CONFIRM")
    if r.a_plus_only:
        tol = f.atr5 * Decimal("0.25")
        if f.prior_hi is None or f.prior_lo is None or not (f.prior_lo - tol <= entry <= f.prior_hi + tol):
            return _z("NOT_A_PLUS", "entry is not in front of a prior event", "CONFIRM")
    return None


def plan_zone(
    direction: Direction,
    entry: Decimal,
    f: ZoneFields,
    r: ZoneRules,
    *,
    tick: Decimal,
    rr: Decimal,
    rr_min: Decimal,
    min_risk_ticks: int,
    max_risk_ticks: int,
    max_rr: Decimal = Decimal("3"),
) -> OrderFlowPlan | OrderFlowSkip:
    """Stop / target from the ATR zone (call after check_zone passed). TP ≤ max_rr R, ≥ rr_min R after rounding."""
    assert f.zone_hi is not None and f.zone_lo is not None and f.atr5 is not None
    s = direction.sign
    entry = round_to_tick(entry, tick)
    if f.signal == "POSITION":
        far = f.zone_lo if s > 0 else f.zone_hi
        raw_stop = far - s * r.stop_atr_pct * f.atr5
        defended = far
    else:
        k = f.rev_level or 1
        edge = f.zone_lo if s > 0 else f.zone_hi
        raw_stop = edge - s * (k + 1) * f.atr5
        if r.a_plus_only and f.prior_lo is not None and f.prior_hi is not None:  # stop outside the prior event
            raw_stop = min(raw_stop, f.prior_lo - tick) if s > 0 else max(raw_stop, f.prior_hi + tick)
        defended = edge - s * k * f.atr5
    stop = round_to_tick(raw_stop, tick, away_from=entry)
    if (entry - stop) * s <= 0:
        return OrderFlowSkip("STOP_INVALID", f"stop {stop} vs entry {entry}")
    risk = abs(entry - stop)
    if risk / tick < min_risk_ticks:
        return OrderFlowSkip("STOP_TOO_TIGHT", f"{risk / tick} ticks < {min_risk_ticks}")
    if risk / tick > max_risk_ticks:
        return OrderFlowSkip("STOP_TOO_WIDE", f"{risk / tick} ticks > {max_risk_ticks}")
    if f.signal == "POSITION":
        target = entry + s * rr * risk
    else:
        target = f.zone_lo if s > 0 else f.zone_hi
        if (target - entry) * s > max_rr * risk:
            target = entry + s * max_rr * risk
    tp = round_to_tick(target, tick, toward=entry)
    got = (tp - entry) * s / risk
    if got < rr_min:
        return OrderFlowSkip("RR_BELOW_MIN", f"{got} < {rr_min}")
    return OrderFlowPlan(direction, f"ZONE_{f.signal}", entry, defended, stop, tp, risk, got)


def zone_trail(
    direction: Direction,
    current: Decimal,
    event_hi: Decimal,
    event_lo: Decimal,
    atr5: Decimal,
    pct: Decimal,
    tick: Decimal,
) -> Decimal | None:
    """New same-direction event → stop to its pct × ATR line beyond the event (LONG: below its low). Ratchet only;
    None = no improvement. Never a breakeven move: the line comes only from the new event."""
    s = direction.sign
    raw = (event_lo if s > 0 else event_hi) - s * pct * atr5
    new = round_to_tick(raw, tick, toward=current) if (raw - current) * s > 0 else None
    return new if new is not None and (new - current) * s > 0 else None


def trail_hit(direction: Direction, trail: Decimal, close: Decimal) -> bool:
    """A closed bar beyond the trail line exits (the wide broker stop stays as the protective stop)."""
    return (close - trail) * direction.sign <= 0
