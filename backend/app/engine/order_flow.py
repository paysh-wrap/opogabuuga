"""D95 ORDER_FLOW (user button, UNVERIFIED → paper accounts only): order-flow signals from the TradingView indicator
pine/Paytience_OrderFlow.pine, delivered as ORDER_FLOW webhook alerts. PURE (no I/O).

No order-flow backtest exists (docs/results/session18/order_flow/RESULTS.md: Databento locked, no tick data). The
alert carries the indicator's own entry / defended level / stop / target; this module NEVER trusts those prices — it
rebuilds the plan from entry + defended level only:
  stop  = defended − sign × buffer_ticks × tick (beyond the defended level), tick-rounded away from entry
  risk  = |entry − stop| must be within [min_risk_ticks, max_risk_ticks]
  TP    = entry + sign × rr × risk, tick-rounded toward entry; recheck rr ≥ rr_min after rounding

D101 (AR Model, docs/results/session18/order_flow/AR_MODEL_RULES.md): `check_ar` gates the alert's four layers in
order ENVIRONMENT → LOCATION → PATH → CONFIRMATION (codes OF_COMPRESSION / OF_ENVIRONMENT / OF_LOCATION /
OF_PATH_UNKNOWN / OF_PATH_EXHAUSTED / OF_NO_CONFIRM / OF_DELTA_ESTIMATED); `build_plan` anchors the stop beyond the
absorption zone (the far side of the absorbed aggressors) when the alert gives one; `trail_stop` is the AR trail
(behind the last closed 5m/15m candle, break-even after follow-through, ratchet only) — pure, not yet wired into the
order manager (no candle feed there; see D101).
Every other gate (window, news, hedge lock, DLL, consistency, flat times, paper-only) is applied by the callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.engine.trade_plan import Direction, round_to_tick

KINDS = frozenset({"ABSORPTION", "DELTA_DIVERGENCE", "STACKED_IMBALANCE", "SWEEP", "POC_MAGNET"})
ZONES = ("INSIDE", "L1", "AVR-", "AVR", "AVR+", "MAX")  # Asia range + ATR(20) path zones, in order


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
    layer: str = "PLAN"  # ENVIRONMENT | LOCATION | PATH | CONFIRMATION | PLAN


@dataclass(frozen=True)
class ArFields:
    """The AR-Model layer values one alert carries (None = the indicator did not send it)."""

    env: str | None = None  # EXPANSION | ROTATION | COMPRESSION
    fib: Decimal | None = None  # retracement depth of the swing range on the bias side (0 = swing extreme)
    value_side: str | None = None  # BELOW_VAL | IN_VALUE | ABOVE_VAH (fixed-range profile of the swing)
    path_zone: str | None = None  # INSIDE | L1 | AVR- | AVR | AVR+ | MAX
    path_side: str | None = None  # ABOVE | BELOW | INSIDE (close vs the Asia range)
    delta_source: str | None = None  # real | est
    confirm_time_ms: int | None = None

    @property
    def present(self) -> bool:
        return self.env is not None and self.confirm_time_ms is not None


@dataclass(frozen=True)
class ArRules:
    required: bool
    allowed_envs: tuple[str, ...]
    location_filter: bool
    fib_min: Decimal
    fib_max: Decimal
    value_side: str  # OUTSIDE_VALUE | NOT_OPPOSITE
    path_filter: bool
    path_block_zone: str
    confirm_max_age_min: int
    require_real_delta: bool


def check_ar(direction: Direction, bar_time_ms: int, ar: ArFields, rules: ArRules) -> OrderFlowSkip | None:
    """None = all AR layers agree; else the first failing layer's skip (signal comes LAST, never first)."""
    if not ar.present:
        if rules.required:
            return OrderFlowSkip("OF_NO_CONFIRM", "alert has no AR-Model fields (old indicator)", "CONFIRMATION")
        return None
    # 1. ENVIRONMENT (always on)
    if ar.env == "COMPRESSION":
        return OrderFlowSkip("OF_COMPRESSION", "low participation / compression: don't trade", "ENVIRONMENT")
    if ar.env not in rules.allowed_envs:
        return OrderFlowSkip("OF_ENVIRONMENT", f"environment {ar.env} not allowed", "ENVIRONMENT")
    # 2. LOCATION (switch)
    if rules.location_filter:
        if ar.fib is None or not rules.fib_min <= ar.fib <= rules.fib_max:
            return OrderFlowSkip("OF_LOCATION", f"fib {ar.fib} outside {rules.fib_min}–{rules.fib_max}", "LOCATION")
        good = "BELOW_VAL" if direction is Direction.LONG else "ABOVE_VAH"
        bad = "ABOVE_VAH" if direction is Direction.LONG else "BELOW_VAL"
        ok = ar.value_side == good if rules.value_side == "OUTSIDE_VALUE" else ar.value_side not in (None, bad)
        if not ok:
            return OrderFlowSkip("OF_LOCATION", f"value side {ar.value_side} ({rules.value_side})", "LOCATION")
    # 3. PATH (switch)
    if rules.path_filter:
        if ar.path_zone not in ZONES or ar.path_side not in ("ABOVE", "BELOW", "INSIDE"):
            return OrderFlowSkip("OF_PATH_UNKNOWN", f"path {ar.path_zone}/{ar.path_side}", "PATH")
        with_move = (ar.path_side == "ABOVE") == (direction is Direction.LONG) and ar.path_side != "INSIDE"
        if with_move and ZONES.index(ar.path_zone) >= ZONES.index(rules.path_block_zone):
            return OrderFlowSkip("OF_PATH_EXHAUSTED", f"{ar.path_zone} {ar.path_side} Asia: move exhausted", "PATH")
    # 4. CONFIRMATION (always on)
    c = ar.confirm_time_ms
    if c is None or c >= bar_time_ms or bar_time_ms - c > rules.confirm_max_age_min * 60_000:
        return OrderFlowSkip("OF_NO_CONFIRM", f"confirm {c} vs entry bar {bar_time_ms}", "CONFIRMATION")
    if rules.require_real_delta and ar.delta_source != "real":
        return OrderFlowSkip("OF_DELTA_ESTIMATED", f"delta_source {ar.delta_source}", "CONFIRMATION")
    return None


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
    absorption: tuple[Decimal, Decimal] | None = None,
) -> OrderFlowPlan | OrderFlowSkip:
    if kind not in KINDS:
        return OrderFlowSkip("OF_UNKNOWN_SIGNAL", kind)
    if entry <= 0 or defended <= 0 or tick <= 0:
        return OrderFlowSkip("OF_BAD_PRICE", f"entry {entry} defended {defended}")
    sign = direction.sign
    entry = round_to_tick(entry, tick)
    if absorption is not None:  # D101: the stop goes beyond where the absorption happened
        lo, hi = absorption
        if lo <= 0 or hi < lo:
            return OrderFlowSkip("OF_BAD_PRICE", f"absorption zone {lo}–{hi}")
        far = lo if sign > 0 else hi
        if (entry - far) * sign <= 0:
            return OrderFlowSkip("OF_LEVEL_WRONG_SIDE", f"absorption zone {lo}–{hi} vs entry {entry}")
        defended = min(defended, far) if sign > 0 else max(defended, far)
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


def trail_stop(
    direction: Direction,
    entry: Decimal,
    risk_pts: Decimal,
    current_stop: Decimal,
    best: Decimal,
    last_candle: tuple[Decimal, Decimal] | None,
    be_after_r: Decimal,
    fee_cover_ticks: int,
    tick: Decimal,
    last: Decimal | None = None,
) -> Decimal:
    """D101 AR trail: break-even (entry + fee cover) once best ≥ be_after_r × R; after that the stop follows the last
    CLOSED 5m/15m candle (low − 1 tick for a long, high + 1 tick for a short). Ratchet only — never loosens; a
    candidate at/through the current price `last` is dropped (the stop is never placed through the market)."""
    s = direction.sign
    new = current_stop
    if (best - entry) * s < be_after_r * risk_pts:
        return new
    cands = [entry + s * fee_cover_ticks * tick]
    if last_candle is not None:
        hi, lo = last_candle
        cands.append(round_to_tick((lo - tick) if s > 0 else (hi + tick), tick, away_from=best))
    for c in cands:
        if last is not None and (c - last) * s >= 0:
            continue
        if (c - new) * s > 0:
            new = c
    return new
