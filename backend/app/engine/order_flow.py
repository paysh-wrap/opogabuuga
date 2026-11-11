"""D95 ORDER_FLOW (user button, UNVERIFIED → paper accounts only): order-flow signals from the TradingView indicator
pine/Paytience_OrderFlow.pine, delivered as ORDER_FLOW webhook alerts. PURE (no I/O).

No order-flow backtest exists (docs/results/session18/order_flow/RESULTS.md: Databento locked, no tick data). The
alert carries the indicator's own entry / defended level / stop / target; this module NEVER trusts those prices — it
rebuilds the plan from entry + defended level only:
  stop  = defended − sign × buffer_ticks × tick (beyond the defended level), tick-rounded away from entry
  risk  = |entry − stop| must be within [min_risk_ticks, max_risk_ticks]
  TP    = entry + sign × rr × risk, tick-rounded toward entry; recheck rr ≥ rr_min after rounding
Every other gate (window, news, hedge lock, DLL, consistency, flat times, paper-only) is applied by the callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.engine.trade_plan import Direction, round_to_tick

KINDS = frozenset({"ABSORPTION", "DELTA_DIVERGENCE", "STACKED_IMBALANCE", "SWEEP", "POC_MAGNET"})


@dataclass(frozen=True)
class OrderFlowPlan:
    direction: Direction
    kind: str
    entry: Decimal
    defended: Decimal
    stop: Decimal
    take_profit: Decimal
    risk_pts: Decimal
    rr: Decimal


@dataclass(frozen=True)
class OrderFlowSkip:
    code: str
    detail: str


def build_plan(
    *,
    kind: str,
    direction: Direction,
    entry: Decimal,
    defended: Decimal,
    tick: Decimal,
    buffer_ticks: int,
    rr: Decimal,
    rr_min: Decimal,
    min_risk_ticks: int,
    max_risk_ticks: int,
    alert_stop: Decimal | None = None,
) -> OrderFlowPlan | OrderFlowSkip:
    if kind not in KINDS:
        return OrderFlowSkip("OF_UNKNOWN_SIGNAL", kind)
    if entry <= 0 or defended <= 0 or tick <= 0:
        return OrderFlowSkip("OF_BAD_PRICE", f"entry {entry} defended {defended}")
    sign = direction.sign
    entry = round_to_tick(entry, tick)
    if (entry - defended) * sign <= 0:  # the defended level must sit on the stop side of the entry
        return OrderFlowSkip("OF_LEVEL_WRONG_SIDE", f"defended {defended} vs entry {entry}")
    if alert_stop is not None and (defended - alert_stop) * sign <= 0:
        return OrderFlowSkip("STOP_INVALID", f"alert stop {alert_stop} is not beyond the defended level {defended}")
    stop = round_to_tick(defended - sign * buffer_ticks * tick, tick, away_from=entry)
    risk = abs(entry - stop)
    ticks = risk / tick
    if ticks < min_risk_ticks:
        return OrderFlowSkip("STOP_TOO_TIGHT", f"{ticks} ticks < {min_risk_ticks}")
    if ticks > max_risk_ticks:
        return OrderFlowSkip("STOP_TOO_WIDE", f"{ticks} ticks > {max_risk_ticks}")
    tp = round_to_tick(entry + sign * rr * risk, tick, toward=entry)
    got = abs(tp - entry) / risk
    if got < rr_min:
        return OrderFlowSkip("RR_BELOW_MIN", f"{got} < {rr_min}")
    return OrderFlowPlan(direction, kind, entry, defended, stop, tp, risk, got)
