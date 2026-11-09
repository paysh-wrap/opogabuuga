"""Signal runtime: market state → confluence → stored Signal (+ gates, plan) → WS. I/O lives here, logic in engine/.

Called after every accepted webhook event. Evaluates each live model of that symbol+profile on the latest bar for
which the HEARTBEAT (close price) has arrived, so the entry price is always that bar's close.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.clock import Clock, session_date
from app.config import RulesConfig
from app.engine.confluence import Bias, Decision, EvalInput, ModelView, evaluate
from app.engine.filters import CooldownState, NewsEvent, cooldown_on_model_event, entry_deadline_ms
from app.engine.market_state import ModelState, SymbolState
from app.engine.trade_plan import Direction, TradePlan
from app.indicators.bars import tf_minutes
from app.models import BiasDecision, Cooldown, Signal, SignalGate, TradePlanRow
from app.monitor.feed import feed_status
from app.signals.stats import StatsCache, atr_percentile, load_history, t1_rate

CalendarProvider = Callable[[date], list[NewsEvent] | None]
FINAL = {"PASS", "SKIP", "EXPIRED", "SHADOWED"}  # SHADOW = disabled instrument still being evaluated (A5)


def no_calendar(_: date) -> list[NewsEvent] | None:
    """Phase 7 wires the real economic calendar. Until then: no data = no trading (§15)."""
    return None


@dataclass(frozen=True)
class SignalUpdate:
    signal_id: int
    model_key: str
    status: str
    reason: str | None
    score: str | None


def _d(x: Any) -> Decimal | None:
    return None if x is None else Decimal(str(x))


def model_view(m: ModelState) -> ModelView | None:
    f = m.fields
    confirm = next((t for e, t in m.events if e == "MODEL_CONFIRMED"), None)
    if confirm is None or f.get("c3_close_time_ms") is None:
        return None
    return ModelView(
        model_key=m.model_key,
        direction=Direction(m.direction),
        events=tuple(m.events),
        c1_high=Decimal(str(f["c1_high"])),
        c1_low=Decimal(str(f["c1_low"])),
        c1_time_ms=int(f["c1_time_ms"]),
        htf_atr14=_d(f.get("htf_atr14")),
        t1=Decimal(str(f["t1"])),
        t2=Decimal(str(f["t2"])),
        invalid=Decimal(str(f["invalid"])),
        sweep_time_ms=int(f["sweep_time_ms"]),
        cisd_level=_d(f.get("cisd_level")),
        cisd_before_c2_close=bool(f.get("cisd_before_c2_close")),
        t1_preticked=bool(f.get("t1_preticked")),
        c3_close_time_ms=int(f["c3_close_time_ms"]),
        confirm_time_ms=confirm,
    )


def today_bias(s: Session, sess: date, proxy: str) -> Bias:
    """Bias computed on THIS instrument's proxy ETF (NQ→QQQ, ES→SPY, YM→DIA, GC→GLD). Missing → NO_TRADE."""
    row = s.execute(
        select(BiasDecision)
        .where(BiasDecision.session_date == sess, BiasDecision.proxy == proxy)
        .order_by(BiasDecision.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None or row.mapped not in ("LONG_ONLY", "SHORT_ONLY", "NEUTRAL"):
        return "NO_TRADE"
    return row.mapped  # type: ignore[return-value]


def _cooldown_row(s: Session, symbol: str, profile: str) -> Cooldown:
    row = s.execute(select(Cooldown).where(Cooldown.symbol == symbol, Cooldown.profile == profile)).scalar_one_or_none()
    if row is None:
        row = Cooldown(symbol=symbol, profile=profile, streak=0, until_session=None)
        s.add(row)
        s.flush()
    return row


def apply_cooldown_event(
    s: Session, clock: Clock, rules: RulesConfig, symbol: str, profile: str, event: str, at: datetime
) -> bool:
    """Returns True when this event starts a cooldown."""
    if event not in ("MODEL_FAILED", "T1_HIT", "T2_HIT"):
        return False
    row = _cooldown_row(s, symbol, profile)
    before = CooldownState(row.streak, row.until_session)
    sess = session_date(at)
    after = cooldown_on_model_event(
        before, event, sess, rules.filters.model_fail_cooldown.streak, rules.filters.model_fail_cooldown.sessions
    )
    row.streak, row.until_session = after.streak, after.until_session
    started = after.until_session != before.until_session and after.active(sess)
    if started:
        audit.record(
            s, clock, "engine", "cooldown.started", f"{symbol}-{profile}", {"until_session": str(after.until_session)}
        )
    return started


def cooldown_active(s: Session, symbol: str, profile: str, sess: date) -> bool:
    row = s.execute(select(Cooldown).where(Cooldown.symbol == symbol, Cooldown.profile == profile)).scalar_one_or_none()
    return row is not None and CooldownState(row.streak, row.until_session).active(sess)


def _store(s: Session, sig: Signal, dec: Decision, now: datetime, final_status: str | None) -> None:
    sig.status = final_status or ("PASS" if dec.outcome == "PASS" else "SKIP" if dec.outcome == "SKIP" else "WAIT")
    sig.skip_reason = dec.skip_reason
    sig.passed = dec.outcome == "PASS"
    sig.score = dec.score.score if dec.score else None
    sig.c1_range_atr = dec.c1_range_atr.quantize(Decimal("0.0001")) if dec.c1_range_atr is not None else None
    sig.features = {
        **dec.features,
        "score_items": {k: str(v) for k, v in (dec.score.earned if dec.score else {}).items()},
    }
    sig.updated_at = now
    for old in list(s.execute(select(SignalGate).where(SignalGate.signal_id == sig.id)).scalars()):
        s.delete(old)
    for g in dec.gates:
        s.add(
            SignalGate(
                signal_id=sig.id,
                gate=g.gate,
                passed=g.passed,
                detail={"code": g.code, "hard": g.hard, "detail": g.detail},
            )
        )


def _store_plan(s: Session, sig: Signal, p: TradePlan) -> None:
    s.add(
        TradePlanRow(
            signal_id=sig.id,
            direction=p.direction.value,
            entry=p.entry,
            stop=p.stop,
            take_profit=p.take_profit,
            risk_pts=p.risk_pts,
            rr=p.rr,
            partial_price=p.partial_price,
            breakeven_price=p.breakeven_price,
            lock_price=p.lock_price,
            mode=p.mode,
        )
    )


def shadow_rules(rules: RulesConfig, symbol: str) -> RulesConfig:
    """Same rules with this instrument enabled — used only to evaluate it in SHADOW (never traded)."""
    inst = rules.instruments[symbol].model_copy(update={"enabled": True})
    return rules.model_copy(update={"instruments": {**rules.instruments, symbol: inst}})


def process(
    s: Session,
    st: SymbolState,
    *,
    rules: RulesConfig,
    clock: Clock,
    calendar: CalendarProvider,
    event: str,
    event_time_ms: int,
    one_to_one: bool,
    cache: StatsCache | None = None,
) -> list[SignalUpdate]:
    now = clock.now()
    at_dt = datetime.fromtimestamp(event_time_ms / 1000, tz=UTC)
    if event == "MODEL_FAILED":
        # D33 (user-approved): only failures of models that qualified for a trade count toward the cooldown.
        failed = [m for m in st.models.values() if (event, event_time_ms) in m.events]
        qualified = any(
            s.execute(select(Signal.id).where(Signal.model_key == m.model_key, Signal.passed)).first() is not None
            for m in failed
        )
        if qualified:
            apply_cooldown_event(s, clock, rules, st.symbol, st.profile, event, at_dt)
    else:
        apply_cooldown_event(s, clock, rules, st.symbol, st.profile, event, at_dt)
    updates: list[SignalUpdate] = []
    if st.last_heartbeat_ms is None or st.last_price is None:
        s.commit()
        return updates
    bar_ms = st.last_heartbeat_ms
    if event_time_ms > bar_ms:
        s.commit()
        return updates  # this bar's close price hasn't arrived yet; the heartbeat will trigger evaluation
    at = datetime.fromtimestamp(bar_ms / 1000, tz=UTC)
    sess = session_date(at)
    tf_min = tf_minutes(st.tf)
    fresh = feed_status(bar_ms, tf_min, now, rules.webhook.stale_after_bar_multiple) == "FRESH"
    bias = today_bias(s, sess, rules.instrument(st.symbol).bias_proxy)
    cal = calendar(sess)
    mfc = rules.filters.model_fail_cooldown
    cooled = cooldown_active(s, st.symbol, st.profile, sess) and (mfc.in_scalp or not rules.scalp_mode.enabled)
    mso = st.mso or {}
    inst_on = rules.instrument(st.symbol).enabled
    enabled = inst_on and rules.strategy.lunqfx  # D55: LunqFX button off → its setups run in SHADOW only
    eval_rules = rules if enabled else shadow_rules(rules, st.symbol)
    hist = cache.get((st.symbol, st.profile), now) if cache else None
    if hist is None:
        hist = load_history(s, st.symbol, st.profile, now)
        if cache:
            cache.put((st.symbol, st.profile), hist, now)
    views = [(m, mv) for m in list(st.models.values()) if (mv := model_view(m)) is not None]
    # One lookup for every live model's signal (was one query per model per bar; model_key is unique).
    existing = {
        x.model_key: x
        for x in s.execute(select(Signal).where(Signal.model_key.in_([m.model_key for m, _ in views]))).scalars()
    }
    for m, mv in views:
        sig = existing.get(m.model_key)
        if sig is not None and sig.status in FINAL:
            continue
        if sig is None:
            sig = Signal(
                symbol=st.symbol,
                profile=st.profile,
                direction=m.direction,
                model_key=m.model_key,
                bar_time=datetime.fromtimestamp(mv.confirm_time_ms / 1000, tz=UTC),
                status="WAIT" if enabled else "SHADOW",
                features={},
            )
            s.add(sig)
            s.flush()
        traded = bool(sig.passed)  # same row the old per-model "passed" query found (model_key is unique)
        dec = evaluate(
            EvalInput(
                symbol=st.symbol,
                profile=st.profile,
                at=at,
                close=Decimal(str(st.last_price["c"])),
                tf_min=tf_min,
                model=mv,
                mso_trend=mso.get("trend"),
                mso_osc=_d(mso.get("osc")),
                htf_trend=mso.get("htf_trend"),
                mso_events=tuple(st.mso_events),
                bias=bias,
                feed_fresh=fresh,
                calendar=cal,
                cooldown_active=cooled,
                model_traded=traded,
                one_to_one=one_to_one,
                t1_rate=t1_rate(hist, mv.c1_time_ms),
                atr_pct=atr_percentile(hist, mv.htf_atr14),
                trend=st.trend.direction(),
            ),
            eval_rules,
        )
        deadline = entry_deadline_ms(mv.confirm_time_ms, mv.c3_close_time_ms, tf_min, rules.entry.max_wait_bars)
        final: str | None = None
        if dec.outcome == "WAIT" and bar_ms >= deadline:
            final = "EXPIRED"
        if not enabled:  # A5 shadow: record what WOULD have happened; never trade, never store a real plan
            _store(s, sig, dec, now, None)
            sp = dec.plan_one_to_one if one_to_one and dec.plan_one_to_one else dec.plan
            shadow_plan = (
                None
                if sp is None
                else {
                    "mode": sp.mode,
                    "entry": str(sp.entry),
                    "stop": str(sp.stop),
                    "take_profit": str(sp.take_profit),
                    "rr": str(sp.rr),
                }
            )
            sig.features = {
                **sig.features,
                "shadow": {"outcome": final or dec.outcome, "reason": dec.skip_reason, "plan": shadow_plan},
            }
            sig.status = "SHADOW" if dec.outcome == "WAIT" and final is None else "SHADOWED"
            sig.passed = False
            sig.skip_reason = "INSTRUMENT_DISABLED" if not inst_on else "STRATEGY_OFF"
            score_s = str(sig.score) if sig.score is not None else None
            updates.append(SignalUpdate(sig.id, m.model_key, sig.status, sig.skip_reason, score_s))
            continue
        _store(s, sig, dec, now, final)
        if dec.outcome == "PASS":
            sig.entry_bar_time = at
            plan = dec.plan_one_to_one if one_to_one and dec.plan_one_to_one else dec.plan
            if dec.plan is not None:
                _store_plan(s, sig, dec.plan)
            if dec.plan_one_to_one is not None:
                _store_plan(s, sig, dec.plan_one_to_one)
            audit.record(
                s,
                clock,
                "engine",
                "signal.pass",
                m.model_key,
                {"score": str(sig.score), "mode": plan.mode if plan else None},
            )
        updates.append(
            SignalUpdate(
                sig.id, m.model_key, sig.status, sig.skip_reason, str(sig.score) if sig.score is not None else None
            )
        )
    s.commit()
    return updates
