"""D55 strategy runtime: NOISE (verified) and OPEN_DRIVE (paper-only) signals from TradingView 1-minute heartbeat bars.

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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias import ledger
from app.bias.policy import Policy, combine
from app.clock import ET, Clock
from app.config import RulesConfig
from app.engine import noise as N
from app.engine import open_drive as OD
from app.engine import pm_fade as PF
from app.engine import structure_filter as SF
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


def _gate(rules: RulesConfig, symbol: str, at: datetime, calendar: CalendarProvider) -> tuple[bool, str, str]:
    """G1 for strategy entries: instrument on, trading window, calendar present, no news blackout."""
    inst = rules.instrument(symbol)
    if not inst.enabled:
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
        cfg, direction.sign, price, fixed_stop, rules.instrument(symbol).tick, mnq, _ibars(mes_rows) or None
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
    s.commit()
    return out
