"""Confluence engine (§6): hard gates G1–G7 + score + TradePlan for one model at one entry bar. Pure.

G8 (Phase + Guard + Risk + consistency + hedge lock) is evaluated per account in risk/ (Phase 4).
Transient failures (window, feed, structure not turned yet, R:R at this price) → WAIT for the next bar.
Hard failures (bias against, C1 too small, cooldown, model failed/traded, instrument disabled) → SKIP now.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.clock import to_et
from app.config import RulesConfig
from app.engine.filters import NewsEvent, c1_range_ok, in_windows, news_block, session_open_c1
from app.engine.scoring import ScoreInputs, ScoreResult, compute_score
from app.engine.trade_plan import (
    Direction,
    Skip,
    TradePlan,
    build_one_to_one_plan,
    build_trade_plan,
    fee_cover_ticks,
)

Bias = Literal["LONG_ONLY", "SHORT_ONLY", "NEUTRAL", "NO_TRADE"]
Outcome = Literal["PASS", "WAIT", "SKIP"]


@dataclass(frozen=True)
class ModelView:
    model_key: str
    direction: Direction
    events: tuple[tuple[str, int], ...]  # (event, bar close ms) in arrival order
    c1_high: Decimal
    c1_low: Decimal
    c1_time_ms: int
    htf_atr14: Decimal | None
    t1: Decimal
    t2: Decimal
    invalid: Decimal
    sweep_time_ms: int
    cisd_level: Decimal | None
    cisd_before_c2_close: bool
    t1_preticked: bool
    c3_close_time_ms: int
    confirm_time_ms: int


@dataclass(frozen=True)
class EvalInput:
    symbol: str
    profile: str
    at: datetime  # entry bar close (aware)
    close: Decimal  # entry bar close price
    tf_min: int
    model: ModelView
    mso_trend: str | None
    mso_osc: Decimal | None
    htf_trend: str | None
    mso_events: tuple[tuple[str, str, int], ...]  # (event, direction, confirm ms)
    bias: Bias
    feed_fresh: bool
    calendar: list[NewsEvent] | None  # None = no calendar data → no trading (§15)
    cooldown_active: bool
    model_traded: bool
    own_tp_rate: Decimal | None = None
    smt_divergence: bool = False
    one_to_one: bool = False
    t1_rate: tuple[Decimal | None, int] = (None, 0)  # (rate, resolved samples) for this symbol+profile
    atr_pct: tuple[Decimal | None, int] = (None, 0)  # (percentile 0–100 of this model's HTF ATR, samples)


@dataclass(frozen=True)
class Gate:
    gate: str
    passed: bool
    code: str  # "OK" or the failure reason code
    hard: bool = False
    detail: str = ""


@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    skip_reason: str | None
    gates: tuple[Gate, ...]
    score: ScoreResult | None
    plan: TradePlan | None
    plan_one_to_one: TradePlan | None
    c1_range_atr: Decimal | None
    features: dict[str, object] = field(default_factory=dict)


def _bias_ok(bias: Bias, d: Direction) -> tuple[bool, str, bool]:
    if bias == "NO_TRADE":
        return False, "BIAS_NO_TRADE", True
    if (bias == "LONG_ONLY" and d is Direction.SHORT) or (bias == "SHORT_ONLY" and d is Direction.LONG):
        return False, "BIAS_OPPOSITE", True
    return True, "OK", False


def evaluate(x: EvalInput, cfg: RulesConfig) -> Decision:
    m, d = x.model, x.model.direction
    at_ms = int(x.at.timestamp() * 1000)
    inst = cfg.instrument(x.symbol)
    gates: list[Gate] = []
    events = {e for e, _ in m.events}

    # ---- G1: window, news, feed, cooldown, instrument enabled
    def g1() -> Gate:
        if not inst.enabled:
            return Gate("G1", False, "INSTRUMENT_DISABLED", hard=True)
        if x.cooldown_active:
            return Gate("G1", False, "COOLDOWN", hard=True)
        if not x.feed_fresh:
            return Gate("G1", False, "FEED_STALE")
        if not in_windows(x.at, inst.windows or cfg.internal.windows):
            return Gate("G1", False, "OUTSIDE_WINDOW")
        if x.calendar is None:
            return Gate("G1", False, "CALENDAR_MISSING", detail="no calendar data = no trading")
        after = inst.news_after_min if inst.news_after_min is not None else cfg.eval.news_breach_min_after
        ev = news_block(x.at, x.calendar, cfg.internal.no_entry_before_news_min, after)
        if ev is not None:
            return Gate("G1", False, "NEWS_BLACKOUT", detail=ev.title)
        return Gate("G1", True, "OK")

    gates.append(g1())

    # ---- G2: bias
    ok, code, hard = _bias_ok(x.bias, d)
    gates.append(Gate("G2", ok, code, hard=hard))

    # ---- G3: model valid
    rng_ok, ratio = c1_range_ok(m.c1_high, m.c1_low, m.htf_atr14, cfg.filters.c1_min_range_atr)
    t1_after_confirm = any(e == "T1_HIT" and t >= m.confirm_time_ms for e, t in m.events)

    def g3() -> Gate:
        if "MODEL_FAILED" in events:
            return Gate("G3", False, "MODEL_FAILED", hard=True)
        if "C3_CLOSED" in events or at_ms >= m.c3_close_time_ms:
            return Gate("G3", False, "C3_CLOSED", hard=True)
        if "MODEL_CONFIRMED" not in events:
            return Gate("G3", False, "MODEL_NOT_CONFIRMED")
        if x.model_traded:
            return Gate("G3", False, "MODEL_ALREADY_TRADED", hard=True)
        if t1_after_confirm and not m.t1_preticked:
            return Gate("G3", False, "T1_TRADED_THROUGH", hard=True)
        if not rng_ok:
            return Gate(
                "G3",
                False,
                "C1_TOO_SMALL",
                hard=True,
                detail="no HTF ATR yet" if ratio is None else f"{ratio:.2f} × ATR",
            )
        return Gate("G3", True, "OK")

    gates.append(g3())

    # ---- G4: structure agrees
    if d is Direction.LONG:
        g4 = x.mso_trend == "BULL" and x.mso_osc is not None and x.mso_osc > 50
    else:
        g4 = x.mso_trend == "BEAR" and x.mso_osc is not None and x.mso_osc < 50
    gates.append(Gate("G4", g4, "OK" if g4 else "MSO_STRUCTURE_DISAGREES"))

    # ---- G5: CHoCH/BoS in direction confirmed at/after the sweep
    breaks = [
        (e, t)
        for e, dd, t in x.mso_events
        if dd == d.value and e in ("MSO_CHOCH", "MSO_BOS") and m.sweep_time_ms <= t <= at_ms
    ]
    choch = any(e == "MSO_CHOCH" for e, _ in breaks)
    bos = any(e == "MSO_BOS" for e, _ in breaks)
    gates.append(Gate("G5", bool(breaks), "OK" if breaks else "NO_STRUCTURE_BREAK"))

    # ---- G6: no opposing divergence within lookback
    opp = Direction.SHORT.value if d is Direction.LONG else Direction.LONG.value
    since = at_ms - cfg.score.div_lookback_bars * x.tf_min * 60_000
    div = any(e == "MSO_DIV" and dd == opp and since <= t <= at_ms for e, dd, t in x.mso_events)
    gates.append(Gate("G6", not div, "OPPOSING_DIVERGENCE" if div else "OK"))

    # ---- G7: valid trade plan at this bar's close
    tp_cfg = cfg.trade_plan
    buf = inst.stop_buffer_ticks or tp_cfg.stop_buffer_ticks
    min_stop = inst.min_stop_ticks or tp_cfg.min_stop_ticks
    entry = x.close
    if cfg.entry.mode == "limit_cisd" and m.cisd_level is not None:
        entry = m.cisd_level
    plan = build_trade_plan(d, entry, m.invalid, m.t2, inst.tick, buf, min_stop, tp_cfg.rr_min, tp_cfg.rr_max)
    plan11: TradePlan | Skip | None = None
    if x.one_to_one:
        o = cfg.one_to_one_mode
        plan11 = build_one_to_one_plan(
            d,
            entry,
            m.invalid,
            m.t2,
            inst.tick,
            buf,
            min_stop,
            o.partial_at_fraction_of_tp,
            o.single_contract_lock_r,
            fee_cover_ticks(inst.fee_rt, inst.tick_value),
            cfg.scalp_mode.target_r if cfg.scalp_mode.enabled else o.rr,
        )
    usable = plan11 if x.one_to_one else plan
    if isinstance(usable, TradePlan):
        gates.append(Gate("G7", True, "OK"))
    else:
        assert isinstance(usable, Skip)
        # stop distance only grows/shrinks with price, so every plan failure is retried on the next bar
        gates.append(Gate("G7", False, usable.reason, detail=usable.detail))

    # ---- score (sizing only; min score gates entry)
    score = compute_score(
        ScoreInputs(
            cisd_before_c2_close=m.cisd_before_c2_close,
            choch_after_sweep=choch,
            bos_after_sweep=bos,
            osc=x.mso_osc,
            own_tp_rate=x.own_tp_rate,
            bias_aligned=(x.bias == ("LONG_ONLY" if d is Direction.LONG else "SHORT_ONLY")),
            htf_agrees=x.htf_trend == ("BULL" if d is Direction.LONG else "BEAR"),
            session_open_c1=session_open_c1(m.c1_time_ms, cfg.score.session_open_times),
            smt_divergence=x.smt_divergence and cfg.smt.enabled,
        ),
        cfg.score.weights,
        cfg.score.osc_strength_min,
        cfg.score.tp_rate_min,
        cfg.score.session_open_c1_weight,
        cfg.score.smt_weight if cfg.smt.enabled else Decimal(0),
    )
    need = cfg.score.neutral_min_score if x.bias == "NEUTRAL" else cfg.score.min_score
    score_ok = score.score >= need
    gates.append(
        Gate(
            "SCORE",
            score_ok,
            "OK" if score_ok else ("NEUTRAL_SCORE_LOW" if x.bias == "NEUTRAL" else "SCORE_BELOW_MIN"),
            detail=f"{score.score} < {need}" if not score_ok else "",
        )
    )

    # ---- D16 1:1-mode win-rate filters (stricter-only). E2/E6 are hard (fixed for this model); rest transient.
    if x.one_to_one:
        gates.append(_one_to_one_filters(x, cfg, plan11, choch, score.score))

    failing = [g for g in gates if not g.passed]
    if not failing:
        outcome: Outcome = "PASS"
        reason = None
    else:
        reason = failing[0].code
        outcome = "SKIP" if any(g.hard for g in failing) else "WAIT"
        if outcome == "SKIP":
            reason = next(g.code for g in failing if g.hard)
    et = to_et(x.at)
    tags = {  # A4 regime / time-slice tags for the Lab
        "weekday": et.strftime("%a"),
        "slice": f"{et.hour:02d}:{0 if et.minute < 30 else 30:02d}",
        "atr_pct": str(x.atr_pct[0]) if x.atr_pct[0] is not None else None,
        "news_day": any(e.impact == "high" and e.currency == "USD" for e in x.calendar or []),
        "bias": x.bias,
        "one_to_one": x.one_to_one,
    }
    return Decision(
        outcome,
        reason,
        tuple(gates),
        score,
        plan if isinstance(plan, TradePlan) else None,
        plan11 if isinstance(plan11, TradePlan) else None,
        ratio,
        {
            "choch": choch,
            "bos": bos,
            "entry_price": str(entry),
            "entry_mode": cfg.entry.mode,
            "tags": tags,
            "invalid": str(m.invalid),
            "t2": str(m.t2),
        },
    )


def _one_to_one_filters(
    x: EvalInput, cfg: RulesConfig, plan11: TradePlan | Skip | None, choch: bool, score: Decimal
) -> Gate:
    f = cfg.one_to_one_mode.filters
    m, d = x.model, x.model.direction
    fails: list[tuple[str, bool]] = []  # (code, hard)
    if f.target_within_t1 and isinstance(plan11, TradePlan) and (plan11.take_profit - m.t1) * d.sign > 0:
        fails.append(("1TO1_TARGET_BEYOND_T1", False))  # E1
    rate, n = x.t1_rate
    if n < f.t1_rate_min_samples or rate is None:
        fails.append(("1TO1_T1_RATE_UNPROVEN", True))  # E2
    elif rate < f.t1_rate_min:
        fails.append(("1TO1_T1_RATE_LOW", True))
    if score < f.min_score:
        fails.append(("1TO1_SCORE_LOW", False))  # E3
    if f.require_choch and not choch:
        fails.append(("1TO1_NEEDS_CHOCH", False))  # E4
    if f.require_bias_and_htf:  # E5
        aligned = x.bias == ("LONG_ONLY" if d is Direction.LONG else "SHORT_ONLY")
        htf = x.htf_trend == ("BULL" if d is Direction.LONG else "BEAR")
        if not (aligned and htf):
            fails.append(("1TO1_BIAS_OR_HTF", not aligned))
    pct, an = x.atr_pct  # E6
    lo, hi = f.atr_pct_band
    if an < f.atr_pct_min_samples or pct is None:
        fails.append(("1TO1_ATR_UNPROVEN", True))
    elif not (lo <= pct <= hi):
        fails.append(("1TO1_ATR_EXTREME", True))
    if x.calendar is not None and news_block(x.at, x.calendar, 0, f.news_after_min) is not None:
        fails.append(("1TO1_NEWS_AFTER", False))  # E7
    if not fails:
        return Gate("F1TO1", True, "OK")
    return Gate("F1TO1", False, fails[0][0], hard=any(h for _, h in fails), detail=",".join(c for c, _ in fails))
