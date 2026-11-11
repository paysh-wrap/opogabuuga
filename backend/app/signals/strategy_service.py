"""D55 strategy runtime: NOISE (verified) and OPEN_DRIVE (unverified) signals from TradingView 1-minute heartbeat bars.

Called after every accepted 1-minute HEARTBEAT (non-negotiable #1: TradingView webhooks are the only signal source —
the bars stored by webhook/service.py). Decisions use app/engine/noise.py and app/engine/open_drive.py (pure, the same
code the parity test checks against the research script). Each entry decision becomes a Signal (PASS, or SKIP when a
G1-style gate blocks it) with exactly one TradePlanRow in its strategy's mode; exits are returned for the controller.
Strategy position state lives on the signal: features.state = OPEN | CLOSED | SKIPPED."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias import ledger
from app.bias import ta_mgc_research as TR
from app.bias.policy import Policy, combine
from app.clock import ET, Clock
from app.config import RulesConfig
from app.engine import ai_duo as DU
from app.engine import noise as N
from app.engine import open_drive as OD
from app.engine import order_flow as OF
from app.engine import pm_fade as PF
from app.engine import structure_filter as SF
from app.engine import ta_mgc as TM
from app.engine.filters import in_windows, news_block
from app.engine.trade_plan import Direction
from app.indicators.bars import Bar as IBar
from app.models import Bar, BiasDecision, Signal, SignalGate, Trade, TradePlanRow
from app.signals.service import CalendarProvider, SignalUpdate

HISTORY_CALENDAR_DAYS = 40  # enough for 14 RTH sessions plus holidays / missing days


@dataclass
class StrategyOutput:
    updates: list[SignalUpdate] = field(default_factory=list)
    exits: list[tuple[int, str]] = field(default_factory=list)  # (signal_id, reason)


@dataclass(frozen=True)
class DayBars:
    day: str
    bars: dict[int, Bar]  # minute index → bar

    def session(self) -> N.Session:
        return N.Session(self.day, self.bars[0].o, {k: b.c for k, b in self.bars.items()})

    def rth_range(self) -> Decimal:
        return max(b.h for b in self.bars.values()) - min(b.l for b in self.bars.values())


def load_days(s: Session, symbol: str, until: datetime) -> list[DayBars]:
    """RTH 1-minute TradingView bars of the last HISTORY_CALENDAR_DAYS, grouped by ET session (with a 09:30 bar)."""
    rows = s.execute(
        select(Bar)
        .where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time > until - timedelta(days=HISTORY_CALENDAR_DAYS))
        .where(Bar.close_time <= until)
        .order_by(Bar.close_time)
    ).scalars()
    by_day: dict[str, dict[int, Bar]] = defaultdict(dict)
    for b in rows:
        k = N.minute_index(b.close_time)
        if 0 <= k < N.RTH_BARS:
            by_day[b.close_time.astimezone(ET).date().isoformat()][k] = b
    return [DayBars(d, bars) for d, bars in sorted(by_day.items()) if 0 in bars]


def _today_signals(s: Session, symbol: str, tag: str, day: str) -> list[Signal]:
    prefix = f"{symbol}-{tag}-{day}"
    return list(s.execute(select(Signal).where(Signal.model_key.like(f"{prefix}%")).order_by(Signal.id)).scalars())


def _gate(
    rules: RulesConfig, symbol: str, at: datetime, calendar: CalendarProvider, enabled: bool | None = None
) -> tuple[bool, str, str]:
    """G1 for strategy entries: instrument on, trading window, calendar present, no news blackout.
    `enabled` overrides the instrument's own switch (AI Duo trades the markets in its own markets list)."""
    inst = rules.instrument(symbol)
    if not (inst.enabled if enabled is None else enabled):
        return False, "INSTRUMENT_DISABLED", ""
    if not in_windows(at, inst.windows or rules.internal.windows):
        return False, "OUTSIDE_WINDOW", ""
    cal = calendar(at.astimezone(ET).date())
    if cal is None:
        return False, "CALENDAR_MISSING", "no calendar data = no trading"
    after = inst.news_after_min if inst.news_after_min is not None else rules.eval.news_breach_min_after
    ev = news_block(at, cal, rules.internal.no_entry_before_news_min, after)
    if ev is not None:
        return False, "NEWS_BLACKOUT", ev.title
    return True, "OK", ""


def _new_signal(
    s: Session,
    clock: Clock,
    *,
    symbol: str,
    key: str,
    direction: Direction,
    at: datetime,
    gate: tuple[bool, str, str],
    features: dict[str, object],
    plan: tuple[str, Decimal, Decimal, Decimal, Decimal, Decimal],
) -> Signal:
    ok, code, detail = gate
    mode, entry, stop, tp, risk, rr = plan
    sig = Signal(
        symbol=symbol,
        profile="TIGHT",  # 1-minute bars
        direction=direction.value,
        model_key=key,
        bar_time=at,
        status="PASS" if ok else "SKIP",
        passed=ok,
        skip_reason=None if ok else code,
        features={
            **features,
            "strategy": mode,
            "state": "OPEN" if ok else "SKIPPED",
            "invalid": str(stop),
            "t2": str(tp),
            "rr_max": str(rr),
        },
        updated_at=clock.now(),
        entry_bar_time=at if ok else None,
    )
    s.add(sig)
    s.flush()
    s.add(SignalGate(signal_id=sig.id, gate="G1", passed=ok, detail={"code": code, "hard": True, "detail": detail}))
    s.add(
        TradePlanRow(
            signal_id=sig.id,
            direction=direction.value,
            entry=entry,
            stop=stop,
            take_profit=tp,
            risk_pts=risk,
            rr=rr,
            mode=mode,
        )
    )
    if ok:
        audit.record(s, clock, "engine", "signal.pass", key, {"strategy": mode, "entry": str(entry)})
    return sig


def _close(s: Session, sig: Signal, reason: str, at: datetime, clock: Clock) -> None:
    """Strategy exit decided. Session 14: the signal does NOT turn CLOSED while a trade of it is still open - it keeps
    state OPEN with an `exit_requested` marker (reason + time) until the controller books the real close
    (controller._close_trade). The watchdog re-issues the exit for any such marker. No open trade → CLOSED now."""
    open_trade = s.execute(select(Trade.id).where(Trade.signal_id == sig.id, Trade.closed_at.is_(None))).first()
    if open_trade is None:
        sig.features = {**sig.features, "state": "CLOSED", "exit_reason": reason, "exit_at": at.isoformat()}
    elif "exit_requested" not in sig.features:
        sig.features = {**sig.features, "exit_requested": {"reason": reason, "at": at.isoformat()}}
    sig.updated_at = clock.now()


def _ibars(rows: list[Bar]) -> list[IBar]:
    out = []
    for b in rows:
        ms = int(b.close_time.timestamp() * 1000)
        out.append(IBar(ms - 60_000, ms, b.o, b.h, b.l, b.c, b.v))
    return out


def structure_check(
    s: Session,
    rules: RulesConfig,
    symbol: str,
    at: datetime,
    today_bars: dict[int, Bar],
    k: int,
    direction: Direction,
    price: Decimal,
    fixed_stop: Decimal,
    gate: tuple[bool, str, str],
) -> tuple[tuple[bool, str, str], dict[str, object]]:
    """D76 OB/SMT FILTER. Default OFF: returns the gate unchanged; with shadow_log the verdict is stored on the signal.
    A veto can only turn a passing gate into a skip (never adds a trade)."""
    cfg = rules.strategy.structure_filters
    if not (cfg.enabled or cfg.shadow_log):
        return gate, {}
    mnq = _ibars([b for kk, b in sorted(today_bars.items()) if kk <= k])
    mes_rows = list(
        s.execute(
            select(Bar)
            .where(Bar.symbol == "MES", Bar.tf == "1", Bar.close_time > at - timedelta(minutes=len(mnq) + 1))
            .where(Bar.close_time <= at)
            .order_by(Bar.close_time)
        ).scalars()
    )
    v = SF.evaluate(
        cfg,
        direction.sign,
        price,
        fixed_stop,
        rules.instrument(symbol).tick,
        mnq,
        _ibars(mes_rows) or None,
        rules.indicators.mso.enabled,
    )
    feats: dict[str, object] = {
        "structure": {"would_block": v.veto, "ob_anchor_stop": None if v.anchor_stop is None else str(v.anchor_stop)}
    }
    if cfg.enabled and v.veto and gate[0]:
        gate = (False, v.veto, "order block / SMT structure is against this side (D76 filter)")
    return gate, feats


def run_noise(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    cfg = rules.strategy.noise_cfg
    out = StrategyOutput()
    k = N.minute_index(at)
    check = N.is_check(k, cfg.check_minutes, cfg.first_check, cfg.last_check)
    flat_k = N.hhmm_to_k(cfg.flat_at)
    if not check and k != flat_k:
        return out
    days = load_days(s, cfg.symbol, at)
    day = at.astimezone(ET).date().isoformat()
    if not days or days[-1].day != day:
        return out
    today, history = days[-1], days[:-1]
    sigs = _today_signals(s, cfg.symbol, "NOISE", day)
    open_sig = next((x for x in sigs if x.features.get("state") == "OPEN"), None)
    position = Direction(open_sig.direction) if open_sig is not None else None
    if k == flat_k:
        if open_sig is not None:
            _close(s, open_sig, "NOISE_FLAT_1600", at, clock)
            out.exits.append((open_sig.id, "NOISE_FLAT_1600"))
        return out
    prior = next((d.session().last_close for d in reversed(history) if d.session().last_close is not None), None)
    sess = today.session()
    sig = N.sigma([d.session() for d in history], k, cfg.lookback_days, cfg.min_history_days, cfg.min_bars_per_day)
    if prior is None or sig is None or not N.roll_guard(sess.open, prior, cfg.roll_gap_pct):
        return out  # warm-up (fewer than min_history_days stored sessions), unknown prior close or roll day
    b = N.bands(sess.open, prior, sig)
    vw = N.vwap([(x.h, x.l, x.c, x.v) for kk, x in sorted(today.bars.items()) if kk <= k])
    close = today.bars[k].c if k in today.bars else None
    if close is None:
        return out
    entries = len(sigs)
    lock_exit = any(x.features.get("lock_exit") for x in sigs)  # D82: a locked-stop exit ends NOISE for the day
    inst = rules.instrument(cfg.symbol)
    for a in N.decide(
        k=k,
        close=close,
        b=b,
        vw=vw,
        position=position,
        entries_today=entries,
        max_entries=cfg.max_entries_per_day,
        allow_entry=check and not exits_only and not lock_exit,
    ):
        if a.kind == "EXIT" and open_sig is not None:
            _close(s, open_sig, a.reason, at, clock)
            out.exits.append((open_sig.id, a.reason))
            open_sig = None
        elif a.kind == "ENTER" and a.direction is not None:
            if any(x.bar_time == at for x in sigs):
                continue  # this bar was already decided (replay after a crash): never a second entry for one bar
            p = N.plan(
                a.direction, close, inst.tick, cfg.emergency_stop_pct, cfg.take_profit_pct, noise_stop_pts(rules)
            )
            entries += 1
            gate = _gate(rules, cfg.symbol, at, calendar)
            if gate[0] and hedge_lock_vs(s, cfg.symbol, "DUO", day, a.direction) is not None:
                gate = (False, "HEDGE_LOCK", "AI Duo holds the opposite side today (first position keeps the lock)")
            gate, sf = structure_check(s, rules, cfg.symbol, at, today.bars, k, a.direction, close, p.stop, gate)
            if gate[0]:  # the AI may block only once its record is proven (≥ 70% for NOISE) — else advisory
                why = ledger.may_block(
                    s,
                    inst.bias_proxy,
                    cfg.symbol,
                    at.astimezone(ET).date(),
                    a.direction.sign,
                    float(rules.strategy.ai_gate_min_accuracy),
                )
                if why:
                    gate = (False, why, "proven AI call (both tools agree) is against this side")
            new = _new_signal(
                s,
                clock,
                symbol=cfg.symbol,
                key=f"{cfg.symbol}-NOISE-{day}-{entries}",
                direction=a.direction,
                at=at,
                gate=gate,
                features={
                    "reason": a.reason,
                    "upper": str(b.upper),
                    "lower": str(b.lower),
                    "sigma": str(b.sigma),
                    "vwap": None if vw is None else str(vw),
                    "close": str(close),
                    "k": k,
                    **sf,
                },
                plan=("NOISE", p.entry, p.stop, p.take_profit, p.risk_pts, p.rr),
            )
            out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_open_drive(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    cfg = rules.strategy.open_drive_cfg
    out = StrategyOutput()
    k = N.minute_index(at)
    day = at.astimezone(ET).date().isoformat()
    if k == N.hhmm_to_k(cfg.time_stop):
        for x in _today_signals(s, cfg.symbol, "OD", day):
            if x.features.get("state") == "OPEN":
                _close(s, x, "OD_TIME_STOP", at, clock)
                out.exits.append((x.id, "OD_TIME_STOP"))
        return out
    if exits_only or k != N.hhmm_to_k(cfg.signal_time) or _today_signals(s, cfg.symbol, "OD", day):
        return out
    days = load_days(s, cfg.symbol, at)
    if not days or days[-1].day != day:
        return out
    today, history = days[-1], days[:-1]
    drive = [today.bars[i] for i in range(k + 1) if i in today.bars]
    if 0 not in today.bars or k not in today.bars or not history:
        return out
    prior = history[-1].session().last_close
    if prior is None or not N.roll_guard(today.bars[0].o, prior, rules.strategy.noise_cfg.roll_gap_pct):
        return out
    full = [d for d in history if len(d.bars) >= rules.strategy.noise_cfg.min_bars_per_day]
    rng = OD.avg_range([d.rth_range() for d in full], cfg.range_days, cfg.min_range_days)
    inst = rules.instrument(cfg.symbol)
    st = OD.setup(
        rth_open=today.bars[0].o,
        drive_high=max(b.h for b in drive),
        drive_low=min(b.l for b in drive),
        close_0959=today.bars[k].c,
        avg_rng=rng,
        frac=cfg.drive_min_range_frac,
        entry_retrace=cfg.entry_retrace,
        stop_retrace=cfg.stop_retrace,
        target_frac=cfg.target_frac,
        tick=inst.tick,
    )
    if st is None:
        return out
    h, m = (int(x) for x in cfg.entry_expires.split(":"))
    expires = at.astimezone(ET).replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(minutes=1)
    new = _new_signal(
        s,
        clock,
        symbol=cfg.symbol,
        key=f"{cfg.symbol}-OD-{day}",
        direction=st.direction,
        at=at,
        gate=_gate(rules, cfg.symbol, at, calendar),
        features={
            "move": str(st.move),
            "avg_range": str(st.avg_range),
            "entry_expires_at": expires.isoformat(),
            "paper_only": cfg.paper_only,
        },
        plan=("OPEN_DRIVE", st.entry, st.stop, st.take_profit, st.risk_pts, st.rr),
    )
    out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_order_flow(
    s: Session, *, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, symbol: str, payload: Any
) -> StrategyOutput:
    """D95: one ORDER_FLOW webhook alert (pine/Paytience_OrderFlow.pine) → at most one signal. Commits.
    The plan is rebuilt by engine/order_flow.py; G1 (window/news/calendar), a signal-level hedge lock and the daily
    cap are checked here; sizing, DLL, consistency, household hedge lock and opt-in paper-only: the controller."""
    out = StrategyOutput()
    st = rules.strategy
    cfg = st.order_flow_cfg
    of = payload.order_flow
    if not st.order_flow or symbol not in cfg.instruments or of is None or payload.direction not in ("LONG", "SHORT"):
        return out
    at = datetime.fromtimestamp(payload.bar_time_ms / 1000, tz=ET)
    day = at.date().isoformat()
    direction = Direction(payload.direction)
    inst = rules.instrument(symbol)
    ar = OF.ArFields(
        env=of.env,
        fib=of.fib,
        value_side=of.value_side,
        path_zone=of.path_zone,
        path_side=of.path_side,
        delta_source=of.delta_source,
        confirm_time_ms=of.confirm_time,
    )
    a = cfg.ar
    absorption = (
        (of.absorption_low, of.absorption_high)
        if of.absorption_low is not None and of.absorption_high is not None
        else None
    )
    # D101 AR Model: ENVIRONMENT → LOCATION → PATH → CONFIRMATION first ("the signal comes last"), then the plan
    res: OF.OrderFlowPlan | OF.OrderFlowSkip | None = OF.check_ar(
        direction,
        payload.bar_time_ms,
        ar,
        OF.ArRules(
            required=a.required,
            allowed_envs=tuple(a.allowed_envs),
            location_filter=a.location_filter,
            fib_min=a.fib_min,
            fib_max=a.fib_max,
            value_side=a.value_side,
            path_filter=a.path_filter,
            path_block_zone=a.path_block_zone,
            confirm_max_age_min=a.confirm_max_age_min,
            require_real_delta=a.require_real_delta,
        ),
    )
    res = res or OF.build_plan(
        kind=of.kind,
        direction=direction,
        entry=of.entry,
        defended=of.defended,
        tick=inst.tick,
        buffer_ticks=cfg.buffer_ticks,
        rr=cfg.rr,
        rr_min=cfg.rr_min,
        min_risk_ticks=max(cfg.min_risk_ticks, inst.min_stop_ticks or 0),  # D96: the market's own floor (MGC 16)
        max_risk_ticks=cfg.max_risk_ticks,
        alert_stop=of.stop,
        absorption=absorption,
    )
    layers = {
        "env": of.env,
        "location_zone": of.location_zone,
        "fib": None if of.fib is None else str(of.fib),
        "value_side": of.value_side,
        "path_zone": of.path_zone,
        "path_side": of.path_side,
        "delta_source": of.delta_source,
        "confirm_time": of.confirm_time,
    }
    if isinstance(res, OF.OrderFlowSkip):  # no valid plan → no signal row; the reason code is audited
        audit.record(
            s,
            clock,
            "engine",
            "order_flow.skip",
            f"{symbol}-OF-{day}",
            {
                "code": res.code,
                "detail": res.detail,
                "layer": res.layer,
                "direction": direction.value,
                "bar_time_ms": payload.bar_time_ms,
                **layers,
            },
        )
        s.commit()
        return out
    today = _today_signals(s, symbol, "OF", day)
    # D96: the per-strategy instrument list decides (MGC may be on for Order Flow only; the global switch stays off)
    gate = _gate(rules, symbol, at, calendar, enabled=symbol in cfg.instruments)
    if gate[0] and any(_holds_position(s, x) for x in today):
        gate = (False, "OF_POSITION_OPEN", "one order-flow position at a time")
    if gate[0] and sum(1 for x in today if x.status == "PASS") >= cfg.max_per_day:
        gate = (False, "OF_DAILY_CAP", f"max {cfg.max_per_day} per day")
    if gate[0]:
        for tag in ("NOISE", "DUO", "OD", "FADE", "AI"):
            lock = hedge_lock_vs(s, symbol, tag, day, direction)
            if lock is not None:
                gate = (False, "HEDGE_LOCK", lock.model_key)
                break
    key = f"{symbol}-OF-{day}-{payload.bar_time_ms}-{direction.value}"
    if s.execute(select(Signal.id).where(Signal.model_key == key)).first() is not None:
        return out  # same alert twice (one entry per model)
    new = _new_signal(
        s,
        clock,
        symbol=symbol,
        key=key,
        direction=direction,
        at=at,
        gate=gate,
        features={
            "kind": res.kind,
            "defended": str(res.defended),
            "paper_only": cfg.paper_only,
            "unverified": True,
            "ar": layers,  # D101: the four AR-Model layers this signal passed
        },
        plan=("ORDER_FLOW", res.entry, res.stop, res.take_profit, res.risk_pts, res.rr),
    )
    s.commit()
    out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def order_flow_exits(s: Session, rules: RulesConfig, clock: Clock, symbol: str, at: datetime) -> StrategyOutput:
    """D96: from cfg.flat_at (16:00 ET) every OPEN order-flow position of `symbol` is flattened (protective; runs even
    with the button off so a position opened before a switch-off still closes). Once per signal."""
    out = StrategyOutput()
    cfg = rules.strategy.order_flow_cfg
    et = at.astimezone(ET)
    if symbol not in cfg.instruments or et.hour * 60 + et.minute < _mod(cfg.flat_at):
        return out
    for x in _today_signals(s, symbol, "OF", et.date().isoformat()):
        if x.features.get("state") == "OPEN" and "exit_requested" not in x.features:
            _close(s, x, "OF_FLAT_1600", at, clock)
            out.exits.append((x.id, "OF_FLAT_1600"))
    return out


def noise_stop_pts(rules: RulesConfig) -> Decimal | None:
    """D58: NOISE fixed-dollar emergency stop in points (None = the % stop)."""
    cfg = rules.strategy.noise_cfg
    if cfg.emergency_stop_usd is None:
        return None
    inst = rules.instrument(cfg.symbol)
    slip = inst.slippage_ticks or rules.trade_plan.slippage_ticks
    return N.stop_pts_for_usd(cfg.emergency_stop_usd, inst.tick, inst.tick_value, inst.fee_rt, slip)


def run_pm_fade(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """D58: afternoon VWAP-band fade, only on a day NOISE has not traded (no NOISE PASS signal yet), 1 per day."""
    cfg = rules.strategy.pm_fade_cfg
    out = StrategyOutput()
    k = N.minute_index(at)
    day = at.astimezone(ET).date().isoformat()
    if k == N.hhmm_to_k(cfg.flat_at):
        for x in _today_signals(s, cfg.symbol, "FADE", day):
            if x.features.get("state") == "OPEN":
                _close(s, x, "FADE_FLAT_1555", at, clock)
                out.exits.append((x.id, "FADE_FLAT_1555"))
        return out
    if exits_only or not N.hhmm_to_k(cfg.first_signal) <= k <= N.hhmm_to_k(cfg.last_signal):
        return out
    if _today_signals(s, cfg.symbol, "FADE", day):
        return out  # one per day (a skipped signal also ends the day)
    if any(x.status == "PASS" for x in _today_signals(s, cfg.symbol, "NOISE", day)):
        return out  # NOISE traded today → no fade
    days = load_days(s, cfg.symbol, at)
    if not days or days[-1].day != day or k not in days[-1].bars:
        return out
    bars = [b for kk, b in sorted(days[-1].bars.items()) if kk <= k]
    vws = PF.running_vwaps([(b.h, b.l, b.c, b.v) for b in bars])
    inst = rules.instrument(cfg.symbol)
    slip = inst.slippage_ticks or rules.trade_plan.slippage_ticks
    stop_pts = N.stop_pts_for_usd(cfg.stop_usd, inst.tick, inst.tick_value, inst.fee_rt, slip)
    close = days[-1].bars[k].c
    d = PF.decide(
        close=close,
        vwap=vws[-1],
        sd=PF.dev_sd([b.c for b in bars], vws),
        band=cfg.band_sd,
        tick=inst.tick,
        stop_pts=stop_pts,
        min_target_ticks=cfg.min_target_ticks,
    )
    if d is None:
        return out
    if isinstance(d, str):  # research: a too-near target ends the fade for the day — record it as a skip
        sig = Signal(
            symbol=cfg.symbol,
            profile="TIGHT",
            direction=Direction.LONG.value if close < (vws[-1] or close) else Direction.SHORT.value,
            model_key=f"{cfg.symbol}-FADE-{day}",
            bar_time=at,
            status="SKIP",
            passed=False,
            skip_reason=d,
            features={"strategy": "PM_FADE", "state": "SKIPPED"},
            updated_at=clock.now(),
        )
        s.add(sig)
        s.flush()
        out.updates.append(SignalUpdate(sig.id, sig.model_key, sig.status, sig.skip_reason, None))
        return out
    fgate, sf = structure_check(
        s, rules, cfg.symbol, at, days[-1].bars, k, d.direction, close, d.stop, _gate(rules, cfg.symbol, at, calendar)
    )
    new = _new_signal(
        s,
        clock,
        symbol=cfg.symbol,
        key=f"{cfg.symbol}-FADE-{day}",
        direction=d.direction,
        at=at,
        gate=fgate,
        features={
            "vwap": str(d.vwap),
            "sd": str(d.sd),
            "close": str(close),
            "k": k,
            "paper_only": cfg.paper_only,
            **sf,
        },
        plan=("PM_FADE", d.entry, d.stop, d.take_profit, d.risk_pts, d.rr),
    )
    out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_ai_bias(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """D56: the day's TradingAgents + Vibe-Trading call is the ONLY input. Trades when both tools agree strongly."""
    cfg = rules.strategy.ai_bias_cfg
    out = StrategyOutput()
    k = N.minute_index(at)
    day = at.astimezone(ET).date().isoformat()
    if k == N.hhmm_to_k(cfg.flat_at):
        for x in _today_signals(s, cfg.symbol, "AI", day):
            if x.features.get("state") == "OPEN":
                _close(s, x, "AI_FLAT_1600", at, clock)
                out.exits.append((x.id, "AI_FLAT_1600"))
        return out
    if exits_only or k != N.hhmm_to_k(cfg.entry_time) or _today_signals(s, cfg.symbol, "AI", day):
        return out
    inst = rules.instrument(cfg.symbol)
    rows = s.execute(
        select(BiasDecision)
        .where(BiasDecision.proxy == inst.bias_proxy, BiasDecision.session_date == at.astimezone(ET).date())
        .order_by(BiasDecision.id)
    ).scalars()
    last = list(rows)[-1:]
    if not last:
        return out  # no AI call today → no trade
    ta, vd, vc = ledger.parse_label(last[0].raw_rating)
    call = combine(ta, vd, vc, Policy(bias_matters=True))
    if not call.agree_strong or call.direction == 0:
        return out  # tools disagree / not strong → no trade
    direction = Direction.LONG if call.direction > 0 else Direction.SHORT
    days = load_days(s, cfg.symbol, at)
    bar = days[-1].bars.get(k) if days and days[-1].day == day else None
    if bar is None:
        return out
    p = N.plan(direction, bar.c, inst.tick, cfg.stop_pct, cfg.take_profit_pct)
    new = _new_signal(
        s,
        clock,
        symbol=cfg.symbol,
        key=f"{cfg.symbol}-AI-{day}",
        direction=direction,
        at=at,
        gate=_gate(rules, cfg.symbol, at, calendar),
        features={"label": last[0].raw_rating, "prob_up": call.prob_up, "paper_only": cfg.paper_only},
        plan=("AI_BIAS", p.entry, p.stop, p.take_profit, p.risk_pts, p.rr),
    )
    out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def _holds_position(s: Session, sig: Signal) -> bool:
    """A strategy signal that still holds (or is about to hold) a position: state OPEN and either no trade was
    booked yet (pending execution) or a trade of it is still open. A stopped-out trade no longer holds the lock."""
    if sig.features.get("state") != "OPEN":
        return False
    rows = list(s.execute(select(Trade.closed_at).where(Trade.signal_id == sig.id)).scalars())
    return not rows or any(c is None for c in rows)


def hedge_lock_vs(s: Session, symbol: str, tag: str, day: str, direction: Direction) -> Signal | None:
    """D83: an OPEN position/signal of strategy `tag` (NOISE / DUO) today in the OPPOSITE direction → HEDGE_LOCK.
    Same direction is allowed. This mirrors the household hedge lock (risk/hedge_lock, unchanged) at signal level."""
    for x in _today_signals(s, symbol, tag, day):
        if x.direction != direction.value and x.direction in ("LONG", "SHORT") and _holds_position(s, x):
            return x
    return None


def _duo_log(s: Session, clock: Clock, day: str, code: str, detail: dict[str, object]) -> None:
    """Every Duo decision (taken or skipped) is audited with its reason code (ledger.duo_decisions lists them)."""
    audit.record(s, clock, "engine", "ai_duo.decision", f"DUO-{day}", {"code": code, **detail})


def _duo_skip(
    s: Session, clock: Clock, symbol: str, day: str, at: datetime, code: str, detail: dict[str, object]
) -> StrategyOutput:
    """A Duo day with no trade: one SKIP signal (direction NONE) carrying the reason code. No plan, never executed."""
    out = StrategyOutput()
    sig = Signal(
        symbol=symbol,
        profile="TIGHT",
        direction="NONE",
        model_key=f"{symbol}-DUO-{day}",
        bar_time=at,
        status="SKIP",
        passed=False,
        skip_reason=code,
        features={**detail, "strategy": "AI_DUO", "state": "SKIPPED"},
        updated_at=clock.now(),
    )
    s.add(sig)
    s.flush()
    s.add(SignalGate(signal_id=sig.id, gate="G1", passed=False, detail={"code": code, "hard": True, "detail": ""}))
    _duo_log(s, clock, day, code, {"symbol": symbol, **detail})
    out.updates.append(SignalUpdate(sig.id, sig.model_key, "SKIP", code, None))
    return out


def _mod(hhmm: str) -> int:
    h, m = (int(x) for x in hhmm.split(":"))
    return h * 60 + m


def _bars_by_minute(s: Session, symbol: str, at: datetime) -> dict[int, Bar]:
    """Today's (ET) 1-minute bars from midnight to `at`, keyed by the minute of day at which each bar CLOSES."""
    et = at.astimezone(ET)
    start = et.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = s.execute(
        select(Bar)
        .where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time > start, Bar.close_time <= at)
        .order_by(Bar.close_time)
    ).scalars()
    return {(b.close_time.astimezone(ET).hour * 60 + b.close_time.astimezone(ET).minute): b for b in rows}


def _duo_research(
    s: Session,
    rules: RulesConfig,
    clock: Clock,
    calendar: CalendarProvider,
    at: datetime,
    symbol: str,
    m: int,
    day: str,
    data: dict[str, Any] | None,
) -> StrategyOutput:
    """D84 AI Duo on MGC from the TradingAgents research setup: validated → Vibe-Trading must agree (shared rule) →
    enter at the 1-minute close inside the entry zone before valid_until, stop beyond the invalidation, rr 1.5R floor /
    2R preferred. One decision per day (trade or one SKIP with a reason code); everything stored in the ledger."""
    cfg, tcfg = rules.strategy.ai_duo_cfg, rules.strategy.ta_mgc_cfg
    out = StrategyOutput()
    data = data or {}
    vtd = data.get("vt") or {}
    info: dict[str, object] = {
        "mode": "RESEARCH",
        "ta_side": (data.get("setup") or {}).get("side") if isinstance(data.get("setup"), dict) else None,
        "vt": vtd.get("direction"),
        "vt_conf": vtd.get("confidence"),
        "vt_note": data.get("vt_note", ""),
    }
    if data.get("error"):  # the job retries every 30 min; only the window end turns this into the day's skip
        if m < _mod(cfg.window_for(symbol)[1]):
            return out
        return _duo_skip(s, clock, symbol, day, at, "RESEARCH_FAILED", {**info, "error": str(data["error"])[:200]})
    setup = TM.parse_setup(data.get("setup"), tcfg.min_confidence)
    if isinstance(setup, str):
        return _duo_skip(s, clock, symbol, day, at, setup, info)
    code = TM.vibe_agrees(setup, vtd.get("direction"), vtd.get("confidence"), cfg.vt_min_conf)
    if code != "AI_AGREE":
        return _duo_skip(s, clock, symbol, day, at, code, info)
    until = TM.valid_until_at(setup.valid_until, day)
    if until is None:
        return _duo_skip(s, clock, symbol, day, at, "SETUP_MALFORMED", info)
    if at > until:
        return _duo_skip(s, clock, symbol, day, at, "SETUP_EXPIRED", info)
    last = _mod(cfg.window_for(symbol)[1])
    bar = _bars_by_minute(s, symbol, at).get(m)
    if bar is None:
        return _duo_skip(s, clock, symbol, day, at, "FEED_GAP", info) if m >= last else out
    code2 = TM.past_levels(setup, bar.c)
    if code2 is not None:
        return _duo_skip(s, clock, symbol, day, at, code2, info)
    if not TM.in_zone(setup, bar.c):
        return _duo_skip(s, clock, symbol, day, at, "NO_ENTRY_IN_ZONE", info) if m >= last else out
    inst = rules.instrument(symbol)
    nc = rules.strategy.noise_cfg
    slip = inst.slippage_ticks or rules.trade_plan.slippage_ticks
    cap = (
        N.stop_pts_for_usd(nc.emergency_stop_usd, inst.tick, inst.tick_value, inst.fee_rt, slip)
        if nc.emergency_stop_usd
        else bar.c * nc.emergency_stop_pct
    )
    sp = TM.build_plan(
        setup,
        bar.c,
        tick=inst.tick,
        buffer_ticks=tcfg.stop_buffer_ticks,
        min_stop_ticks=inst.min_stop_ticks or rules.trade_plan.min_stop_ticks,
        cap_pts=cap,
        rr_min=max(cfg.rr_min, rules.trade_plan.rr_min),
        rr_max=rules.trade_plan.rr_max,
        rr_preferred=tcfg.rr_preferred,
    )
    if isinstance(sp, str):
        return _duo_skip(s, clock, symbol, day, at, sp, info)
    p = sp.plan
    gate = _gate(rules, symbol, at, calendar, enabled=symbol in cfg.markets)
    new = _new_signal(
        s,
        clock,
        symbol=symbol,
        key=f"{symbol}-DUO-{day}",
        direction=setup.direction,
        at=at,
        gate=gate,
        features={
            **info,
            "confidence": setup.confidence,
            "zone": [str(setup.entry_low), str(setup.entry_high)],
            "valid_until": setup.valid_until,
            "lock_price": None if setup.lock_price is None else str(setup.lock_price),
            "reasons": list(setup.reasons),
            "below_preferred_2r": sp.below_preferred,  # allowed (>= 1.5R) but under the preferred 2R: tagged
            "paper_only": cfg.paper_only,
        },
        plan=("AI_DUO", p.entry, p.stop, p.take_profit, p.risk_pts, p.rr),
    )
    _duo_log(s, clock, day, "TAKEN" if gate[0] else gate[1], {"symbol": symbol, **info, "entry": str(p.entry)})
    out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_ai_duo(
    s: Session,
    rules: RulesConfig,
    clock: Clock,
    calendar: CalendarProvider,
    at: datetime,
    symbol: str,
    exits_only: bool = False,
) -> StrategyOutput:
    """D83 AI Duo on one market: both AIs must pick the same side; entry on the first 5-minute VWAP pullback close in
    that direction inside the entry window (03:00–11:30 ET by default, 09:30–09:35 excluded); one decision per market
    per day (a trade or one SKIP with a reason code). PAPER only (config + controller)."""
    cfg = rules.strategy.ai_duo_cfg
    out = StrategyOutput()
    et = at.astimezone(ET)
    m, day = et.hour * 60 + et.minute, et.date().isoformat()  # m = minute of day at which this bar CLOSES
    if m == _mod(cfg.flat_at):
        for x in _today_signals(s, symbol, "DUO", day):
            if x.features.get("state") == "OPEN":
                _close(s, x, "DUO_FLAT_1600", at, clock)
                out.exits.append((x.id, "DUO_FLAT_1600"))
        return out
    n, first, last = cfg.bar_minutes, _mod(cfg.window_for(symbol)[0]), _mod(cfg.window_for(symbol)[1])
    if exits_only or not first < m <= last:
        return out
    if symbol == "MGC" and not _today_signals(s, symbol, "DUO", day):
        research = TR.latest(s, rules.strategy.ta_mgc_cfg.proxy, et.date())
        if research is not None:  # D84: the TradingAgents MGC research setup (part of AI Duo) is today's plan
            if any(_mod(a) < m and m - 1 < _mod(b) for a, b in cfg.excluded):
                return out
            return _duo_research(s, rules, clock, calendar, at, symbol, m, day, TR.payload(research))
    if m % n != 0:
        return out
    if any(_mod(a) < m and m - n < _mod(b) for a, b in cfg.excluded):
        return out  # the bar covers excluded minutes (09:30–09:35): never a trigger
    if _today_signals(s, symbol, "DUO", day):
        return out  # one decision per market per day
    inst = rules.instrument(symbol)
    last_call = list(
        s.execute(
            select(BiasDecision)
            .where(BiasDecision.proxy == inst.bias_proxy, BiasDecision.session_date == et.date())
            .order_by(BiasDecision.id)
        ).scalars()
    )[-1:]
    if not last_call:
        return _duo_skip(s, clock, symbol, day, at, "AI_MISSING", {"label": None})
    label = last_call[0].raw_rating
    ta, vd, vc = ledger.parse_label(label)
    side, code = DU.ai_side(ta, vd, vc, cfg.vt_min_conf)
    info: dict[str, object] = {"label": label, "ta": ta, "vt": vd, "vt_conf": vc}
    if side is None:
        return _duo_skip(s, clock, symbol, day, at, code, info)
    bars = _bars_by_minute(s, symbol, at)
    win = [bars.get(i) for i in range(m - n + 1, m + 1)]
    if any(b is None for b in win):
        if m >= last:
            return _duo_skip(s, clock, symbol, day, at, "FEED_GAP", info)
        return out  # a missing bar: wait for the next 5-minute close
    cur = [b for b in win if b is not None]
    since = [b for i, b in sorted(bars.items()) if i > first]  # session VWAP anchored at the window start
    vw = N.vwap([(b.h, b.l, b.c, b.v) for b in since])
    bar = DU.aggregate([(b.o, b.h, b.l, b.c) for b in cur])
    prev_win = [bars.get(i) for i in range(m - 2 * n + 1, m - n + 1)]
    prev = DU.aggregate([(b.o, b.h, b.l, b.c) for b in prev_win if b is not None]) if None not in prev_win else None
    if not DU.pullback_trigger(side, bar, vw):
        if m >= last:
            return _duo_skip(s, clock, symbol, day, at, "NO_PULLBACK", info)
        return out
    nc = rules.strategy.noise_cfg
    slip = inst.slippage_ticks or rules.trade_plan.slippage_ticks
    cap = (
        N.stop_pts_for_usd(nc.emergency_stop_usd, inst.tick, inst.tick_value, inst.fee_rt, slip)
        if nc.emergency_stop_usd
        else bar.c * nc.emergency_stop_pct
    )
    p = DU.plan(
        side,
        bar.c,
        bar,
        prev,
        tick=inst.tick,
        buffer_ticks=cfg.stop_buffer_ticks,
        min_stop_ticks=inst.min_stop_ticks or rules.trade_plan.min_stop_ticks,
        cap_pts=cap,
        rr_target=cfg.rr_target,
        rr_min=max(cfg.rr_min, rules.trade_plan.rr_min),
    )
    if isinstance(p, str):
        return _duo_skip(s, clock, symbol, day, at, p, info)
    gate = _gate(rules, symbol, at, calendar, enabled=symbol in cfg.markets)
    # household hedge lock (unchanged rule): an open NOISE position/signal on the opposite side blocks Duo. NOISE is MNQ
    # only; on MGC (METALS) there is nothing to clash with. Same-bar tie: NOISE ran first → NOISE wins.
    if gate[0] and hedge_lock_vs(s, symbol, "NOISE", day, side) is not None:
        gate = (False, "HEDGE_LOCK", "NOISE holds the opposite side today")
    agrees = any(x.direction == side.value and x.status == "PASS" for x in _today_signals(s, symbol, "NOISE", day))
    new = _new_signal(
        s,
        clock,
        symbol=symbol,
        key=f"{symbol}-DUO-{day}",
        direction=side,
        at=at,
        gate=gate,
        features={
            **info,
            "prob_up": combine(ta, vd, vc, Policy(bias_matters=True)).prob_up,
            "stop_capped": p.stop_capped,
            "below_preferred_2r": p.rr < cfg.rr_target,  # allowed (>= 1.5R) but under the preferred target: tagged
            "agrees_with_noise": agrees,
            "paper_only": cfg.paper_only,
        },
        plan=("AI_DUO", p.entry, p.stop, p.take_profit, p.risk_pts, p.rr),
    )
    _duo_log(s, clock, day, "TAKEN" if gate[0] else gate[1], {"symbol": symbol, **info, "entry": str(p.entry)})
    out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run(
    s: Session,
    *,
    rules: RulesConfig,
    clock: Clock,
    calendar: CalendarProvider,
    symbol: str,
    tf: str,
    at: datetime,
    exits_only: bool = False,
) -> StrategyOutput:
    """Entry point after a 1-minute HEARTBEAT has been stored. Commits. exits_only: a replayed (late) heartbeat may
    only EXIT / manage - a stale bar must never open a new position."""
    out = StrategyOutput()
    if tf != "1":
        return out
    st = rules.strategy
    if st.noise and symbol == st.noise_cfg.symbol:
        r = run_noise(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.open_drive and symbol == st.open_drive_cfg.symbol:
        r = run_open_drive(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.pm_fade and symbol == st.pm_fade_cfg.symbol:
        r = run_pm_fade(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.ai_bias and symbol == st.ai_bias_cfg.symbol:
        r = run_ai_bias(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.ai_duo and symbol in st.ai_duo_cfg.markets:  # after NOISE: on a same-bar tie NOISE wins (D83)
        r = run_ai_duo(s, rules, clock, calendar, at, symbol, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    out.exits += order_flow_exits(s, rules, clock, symbol, at).exits
    s.commit()
    return out
