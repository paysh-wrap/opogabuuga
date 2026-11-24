"""D55 strategy runtime: NOISE (verified) and the other strategy signals from TradingView 1-minute heartbeat bars.

Called after every accepted 1-minute HEARTBEAT (non-negotiable #1: TradingView webhooks are the only signal source —
the bars stored by webhook/service.py). Decisions use app/engine/noise.py etc. (pure, the same
code the parity test checks against the research script). Each entry decision becomes a Signal (PASS, or SKIP when a
G1-style gate blocks it) with exactly one TradePlanRow in its strategy's mode; exits are returned for the controller.
Strategy position state lives on the signal: features.state = OPEN | CLOSED | SKIPPED."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias import advisor as ADV
from app.bias import ledger
from app.bias import of_advisor as OFA
from app.bias import ta_mgc_research as TR
from app.bias.policy import LedgerStats, Policy, combine
from app.clock import ET, Clock, session_date
from app.config import ADVISED_MODES, CandaceIctCfg, NoiseCfg, RulesConfig
from app.engine import ai_duo as DU
from app.engine import auction_imre as AU
from app.engine import bruni_structure as BR
from app.engine import candace_ict as CI
from app.engine import conti_orb as CO
from app.engine import conti_vwap as CV
from app.engine import gala_pa as GP
from app.engine import jj_fpt as JJ
from app.engine import late_day as LD
from app.engine import noise as N
from app.engine import okala_8020 as OK
from app.engine import order_flow as OF
from app.engine import pm_fade as PF
from app.engine import structure_filter as SF
from app.engine import ta_mgc as TM
from app.engine import zone_atr as ZA
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
    stop_moves: list[tuple[int, Decimal, str]] = field(default_factory=list)  # (signal_id, runner stop, reason)


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
    # D143: tighten-only — the wider of the EVAL and FUNDED news windows (funded news = hard breach), one gate for both
    firm_after = max(rules.eval.news_breach_min_after, rules.funded.news_breach_min_after)
    after = inst.news_after_min if inst.news_after_min is not None else firm_after
    before = max(
        rules.internal.no_entry_before_news_min, rules.eval.news_breach_min_before, rules.funded.news_breach_min_before
    )
    ev = news_block(at, cal, before, after)
    if ev is not None:
        return False, "NEWS_BLACKOUT", ev.title
    return True, "OK", ""


def advise(
    s: Session,
    rules: RulesConfig,
    clock: Clock,
    *,
    mode: str,
    symbol: str,
    key: str,
    direction: Direction,
    at: datetime,
    gate: tuple[bool, str, str],
) -> tuple[tuple[bool, str, str], dict[str, object] | None]:
    """D151 hook: the TradingAgents advisor in front of the D142-D150 strategies. Reads today's STORED BiasDecision
    and the ledger (DB only, never a network call). Tighten-only: may turn a PASS into SKIP ADVISOR_DISAGREE (GATE
    mode + proven ledger + DISAGREE), never the reverse. OFF / opted-out strategy → no field, nothing changes."""
    cfg = rules.strategy.advisor
    if cfg.mode == "OFF" or mode not in ADVISED_MODES or mode in cfg.skip_strategies:
        return gate, None
    proxy = rules.instrument(symbol).bias_proxy
    today = at.astimezone(ET).date()
    pol = Policy(bias_matters=True)
    rows = ledger._calls(s, proxy, today, today)
    call, label, st = None, None, None
    if rows:
        label = rows[-1].raw_rating
        call = combine(*ledger.parse_label(label), pol)
        st = LedgerStats(**ledger.ledger(s, proxy, symbol, today, pol)["stats"])
    params = ADV.AdvisorParams(cfg.mode, float(rules.strategy.ai_gate_min_accuracy), pol.min_calls)
    v = ADV.advisor_verdict(call, direction.sign, st, params)
    blocked = v.blocks and gate[0]
    if blocked:
        gate = (False, "ADVISOR_DISAGREE", f"proven TradingAgents call ({label}) is against this side")
    feat = {**v.as_features(label, cfg.mode), "blocks": blocked}
    audit.record(s, clock, "engine", "signal.advisor", key, {"strategy": mode, **feat})
    return gate, feat


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
    rules: RulesConfig | None = None,
) -> Signal:
    if rules is not None:  # D151: TradingAgents advisor (only the ADVISED_MODES strategies pass `rules`)
        gate, adv = advise(s, rules, clock, mode=plan[0], symbol=symbol, key=key, direction=direction, at=at, gate=gate)
        if adv is not None:
            features = {**features, "advisor": adv}
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


def noise_entries_today(sigs: list[Signal]) -> int:
    """Entries counted toward the daily max: every signal plus the same-direction re-entries merged into a HOLD."""
    return len(sigs) + sum(int(x.features.get("merged_entries", 0)) for x in sigs)


def run_noise(
    s: Session,
    rules: RulesConfig,
    clock: Clock,
    calendar: CalendarProvider,
    at: datetime,
    exits_only: bool = False,
    cfg: NoiseCfg | None = None,
    mode: str = "NOISE",
) -> StrategyOutput:
    """NOISE on MNQ. D165: the same code runs on MGC with `cfg` = the MGC NOISE settings and `mode` = "MGC_NOISE" (the
    MGC button is that market's own switch; no AI-bias block, structure filter or Duo lock on it)."""
    mgc = cfg is not None
    cfg = cfg or rules.strategy.noise_cfg
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
    entries = noise_entries_today(sigs)
    lock_exit = any(x.features.get("lock_exit") for x in sigs)  # D82: a locked-stop exit ends NOISE for the day
    inst = rules.instrument(cfg.symbol)
    actions = N.decide(
        k=k,
        close=close,
        b=b,
        vw=vw,
        position=position,
        entries_today=entries,
        max_entries=cfg.max_entries_per_day,
        allow_entry=check and not exits_only and not lock_exit and at.astimezone(ET).weekday() not in cfg.skip_weekdays,
    )
    # A same-direction EXIT + ENTER on one check leaves the account in the same position: with the exit fill still
    # pending the re-entry would hit POSITION_OPEN and strand the account flat. Treat it as HOLD, count the entry.
    merge = (
        open_sig is not None
        and any(x.kind == "EXIT" for x in actions)
        and any(x.kind == "ENTER" and x.direction is position for x in actions)
    )
    for a in actions:
        if a.kind == "EXIT" and open_sig is not None and merge:
            continue  # same-direction EXIT + ENTER on one check = HOLD (see below)
        if a.kind == "EXIT" and open_sig is not None:
            _close(s, open_sig, a.reason, at, clock)
            out.exits.append((open_sig.id, a.reason))
            open_sig = None
        elif a.kind == "ENTER" and a.direction is not None and merge:
            if "merged_at" not in open_sig.features or open_sig.features["merged_at"] != at.isoformat():
                open_sig.features = {
                    **open_sig.features,
                    "merged_entries": int(open_sig.features.get("merged_entries", 0)) + 1,
                    "merged_at": at.isoformat(),
                }
                open_sig.updated_at = clock.now()
            entries += 1
        elif a.kind == "ENTER" and a.direction is not None:
            if any(x.bar_time == at for x in sigs):
                continue  # this bar was already decided (replay after a crash): never a second entry for one bar
            p = N.plan(
                a.direction, close, inst.tick, cfg.emergency_stop_pct, cfg.take_profit_pct, noise_stop_pts(rules, cfg)
            )
            entries += 1
            gate = _gate(rules, cfg.symbol, at, calendar, True if mgc else None)
            sf: dict[str, object] = {}
            if not mgc:
                if gate[0] and hedge_lock_vs(s, cfg.symbol, "DUO", day, a.direction) is not None:
                    gate = (False, "HEDGE_LOCK", "AI Duo holds the opposite side today (first position keeps the lock)")
                gate, sf = structure_check(s, rules, cfg.symbol, at, today.bars, k, a.direction, close, p.stop, gate)
            if gate[0] and not mgc:  # the AI may block only once its record is proven (≥ 70% for NOISE) — else advisory
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
                plan=(mode, p.entry, p.stop, p.take_profit, p.risk_pts, p.rr),
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
    am = cfg.amt  # D110 AMT+ (button): CONTEXT → LOCATION before any order-flow layer ("order flow LAST")
    amt_f = OF.AmtFields(context=of.context, key_level_type=of.key_level_type, target_level=of.target_level)
    res: OF.OrderFlowPlan | OF.OrderFlowSkip | None = (
        OF.check_amt(
            direction,
            amt_f,
            OF.AmtRules(
                balance_mode=am.balance_mode,
                level_filter=am.level_filter,
                levels=frozenset(am.levels),
                target_to_level=am.target_to_level,
                target_max_rr=am.target_max_rr,
            ),
        )
        if am.enabled
        else None
    )
    z = cfg.zone_atr  # D111 ATR-zone type (iceberg PROXY): a ZONE alert never runs the AR / Casper layers
    is_zone = of.kind == "ZONE" or of.zone_signal is not None
    if is_zone and not z.enabled:
        return out  # the type is off: zone alerts are ignored
    zf = ZA.ZoneFields(
        signal=of.zone_signal,
        zone_hi=of.event_zone_hi,
        zone_lo=of.event_zone_lo,
        event_size=of.event_size,
        atr5=of.atr5,
        rev_level=of.rev_level,
        prior_hi=of.prior_event_hi,
        prior_lo=of.prior_event_lo,
        rvol=of.rvol,
        range5_atr=of.range5_atr,
        tick=of.tick,
    )
    if is_zone and of.zone_signal == "EVENT":
        out.exits += _zone_event(s, clock, symbol, day, direction, zf, z.stop_atr_pct, inst.tick, at)
        s.commit()
        return out
    if is_zone:
        zr = ZA.ZoneRules(
            modes=frozenset(z.modes),
            entry_atr_pct=z.entry_atr_pct,
            stop_atr_pct=z.stop_atr_pct,
            reversion_levels=frozenset(z.reversion_levels),
            a_plus_only=z.a_plus_only,
            min_event_size=z.min_event_size.get(symbol, 150),
            dead_zone_filter=z.dead_zone_filter,
            dead_zone=(_mod(z.dead_zone[0]), _mod(z.dead_zone[1])),
            dead_zone_min_rvol=z.dead_zone_min_rvol,
            last_minutes_filter=z.last_minutes_filter,
            rth_close=_mod(z.rth_close),
            last_minutes=z.last_minutes,
            price_change_confirm=z.price_change_confirm,
            price_change_pct=z.price_change_pct,
            tick_filter=z.tick_filter,
            tick_extreme=z.tick_extreme,
        )
        res = res or ZA.check_zone(direction, of.entry, at.hour * 60 + at.minute, zf, zr)
        res = res or ZA.plan_zone(
            direction,
            of.entry,
            zf,
            zr,
            tick=inst.tick,
            rr=cfg.rr,
            rr_min=cfg.rr_min,
            min_risk_ticks=max(cfg.min_risk_ticks, inst.min_stop_ticks or 0),
            max_risk_ticks=z.max_risk_ticks,
        )
    elif z.enabled and z.exclusive:
        res = res or OF.OrderFlowSkip("OF_ZONE_EXCLUSIVE", "ATR-zone type is exclusive: AR alerts do not trade", "ZONE")
    # D101 AR Model: ENVIRONMENT → LOCATION → PATH → CONFIRMATION first ("the signal comes last"), then the plan
    res = res or OF.check_ar(
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
    c = cfg.casper  # D108 Casper refinements after the AR layers (each a switch)
    res = res or OF.check_casper(
        direction,
        of.kind,
        OF.CasperFields(
            close_pos=of.close_pos,
            stacked=of.stacked,
            cvd_slope=of.cvd_slope,
            open_vs_value=of.open_vs_value,
            prior_va_width_atr=of.prior_va_width_atr,
        ),
        OF.CasperRules(
            price_confirms=c.price_confirms,
            close_pos_min=c.close_pos_min,
            stacked_definition=c.stacked_definition,
            min_stacked=c.min_stacked,
            cvd_confirm=c.cvd_confirm,
            condition=c.condition,
            inside_value_ok=c.inside_value_ok,
            bunched=c.bunched,
            min_va_width_atr=c.min_va_width_atr,
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
    if c.round_stop and not is_zone and isinstance(res, OF.OrderFlowPlan) and symbol in c.round_step:
        res = OF.casper_round_stop(
            res,
            tick=inst.tick,
            step=c.round_step[symbol],
            buffer_ticks=c.round_buffer_ticks,
            rr=cfg.rr,
            rr_min=cfg.rr_min,
            max_risk_ticks=cfg.max_risk_ticks,
        )
    pos_ok = not is_zone or of.zone_signal == "POSITION"  # a reversion targets its own zone
    if am.enabled and am.target_to_level and pos_ok and isinstance(res, OF.OrderFlowPlan):  # D110: next level
        res = OF.amt_target(res, of.target_level, tick=inst.tick, rr_min=cfg.rr_min, max_rr=am.target_max_rr)
    layers = {
        "context": of.context,
        "ctx_session": of.ctx_session,
        "key_level_type": of.key_level_type,
        "target_level": None if of.target_level is None else str(of.target_level),
        "eth_vwap": None if of.eth_vwap is None else str(of.eth_vwap),
        "prev_rth_vah": None if of.prev_rth_vah is None else str(of.prev_rth_vah),
        "prev_rth_val": None if of.prev_rth_val is None else str(of.prev_rth_val),
        "prev_rth_poc": None if of.prev_rth_poc is None else str(of.prev_rth_poc),
        "env": of.env,
        "location_zone": of.location_zone,
        "fib": None if of.fib is None else str(of.fib),
        "value_side": of.value_side,
        "path_zone": of.path_zone,
        "path_side": of.path_side,
        "delta_source": of.delta_source,
        "confirm_time": of.confirm_time,
        "close_pos": None if of.close_pos is None else str(of.close_pos),
        "cvd_slope": None if of.cvd_slope is None else str(of.cvd_slope),
        "open_vs_value": of.open_vs_value,
        "prior_va_width_atr": None if of.prior_va_width_atr is None else str(of.prior_va_width_atr),
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
        for tag in ("NOISE", "DUO", "OD", "FADE", "AI"):  # "OD": legacy Opening-drive positions still lock (D107)
            lock = hedge_lock_vs(s, symbol, tag, day, direction)
            if lock is not None:
                gate = (False, "HEDGE_LOCK", lock.model_key)
                break
    key = f"{symbol}-OF-{day}-{payload.bar_time_ms}-{direction.value}"
    if s.execute(select(Signal.id).where(Signal.model_key == key)).first() is not None:
        return out  # same alert twice (one entry per model)
    # D109 TradingAgents advisor: annotate; skip OF_TA_DISAGREES only with ta_advisor_blocks + a proven ledger
    ta_note, ta_skip = OFA.verdict(s, rules, symbol, session_date(at), direction.value)
    if ta_note is not None and ta_note.get("agrees") is False:
        audit.record(
            s,
            clock,
            "engine",
            "order_flow.ta_disagrees",
            f"{symbol}-OF-{day}",
            {"key": key, "direction": direction.value, "advice": ta_note.get("side"), "blocks": ta_skip is not None},
        )
        if ta_skip and gate[0]:
            gate = (False, ta_skip, f"TradingAgents advisor says {ta_note.get('side')} (proven ledger, blocks on)")
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
            **(
                {
                    "zone": {
                        "signal": of.zone_signal,
                        "hi": str(of.event_zone_hi),
                        "lo": str(of.event_zone_lo),
                        "atr5": str(of.atr5),
                        "proxy": "iceberg PROXY (no MBO data)",
                    }
                }
                if is_zone
                else {}
            ),
            **({"ta_advice": ta_note} if ta_note is not None else {}),  # D109 advisory annotation
        },
        plan=("ORDER_FLOW", res.entry, res.stop, res.take_profit, res.risk_pts, res.rr),
    )
    s.commit()
    out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def _zone_event(
    s: Session,
    clock: Clock,
    symbol: str,
    day: str,
    direction: Direction,
    zf: ZA.ZoneFields,
    pct: Decimal,
    tick: Decimal,
    at: datetime,
) -> list[tuple[int, str]]:
    """D111: a new event (iceberg PROXY) for open ZONE positions — same direction: trail to its 115%-ATR line (ratchet,
    never breakeven; enforced at bar close by order_flow_exits); opposite direction: exit (OF_ZONE_OPPOSING_EVENT)."""
    exits: list[tuple[int, str]] = []
    if zf.zone_hi is None or zf.zone_lo is None or zf.atr5 is None:
        return exits
    for x in _today_signals(s, symbol, "OF", day):
        zone = x.features.get("zone")
        if not zone or not _holds_position(s, x):
            continue
        d = Direction(x.direction)
        if d is not direction:
            _close(s, x, "OF_ZONE_OPPOSING_EVENT", at, clock)
            exits.append((x.id, "OF_ZONE_OPPOSING_EVENT"))
            continue
        plan = s.execute(select(TradePlanRow).where(TradePlanRow.signal_id == x.id)).scalar_one_or_none()
        cur = Decimal(str(x.features.get("zone_trail_stop") or (plan.stop if plan is not None else 0)))
        new = ZA.zone_trail(d, cur, zf.zone_hi, zf.zone_lo, zf.atr5, pct, tick) if cur > 0 else None
        if new is not None:
            x.features = {**x.features, "zone_trail_stop": str(new)}
            audit.record(s, clock, "engine", "order_flow.zone_trail", x.model_key, {"from": str(cur), "to": str(new)})
    return exits


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


def zone_trail_exits(s: Session, symbol: str, close: Decimal, at: datetime, clock: Clock) -> StrategyOutput:
    """D111: a closed bar beyond a ZONE position's trail line (set only by a new same-direction event) exits it."""
    out = StrategyOutput()
    for x in _today_signals(s, symbol, "OF", at.astimezone(ET).date().isoformat()):
        t = x.features.get("zone_trail_stop")
        live = t and x.features.get("state") == "OPEN" and "exit_requested" not in x.features
        if live and ZA.trail_hit(Direction(x.direction), Decimal(str(t)), close):
            _close(s, x, "OF_ZONE_TRAIL", at, clock)
            out.exits.append((x.id, "OF_ZONE_TRAIL"))
    return out


def noise_stop_pts(rules: RulesConfig, cfg: NoiseCfg | None = None) -> Decimal | None:
    """D58: NOISE fixed-dollar emergency stop in points (None = the % stop)."""
    cfg = cfg or rules.strategy.noise_cfg
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
    if at.astimezone(ET).weekday() in rules.strategy.noise_cfg.skip_weekdays:
        return out  # D132 (B2): the NOISE weekday skip (Mondays) applies to the fade too — shipped_config.md
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


JJ_TAG = "JJ"


def _et_at(day: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(day, time(h, m), tzinfo=ET)


def _jbars(s: Session, symbol: str, since: datetime, until: datetime) -> list[JJ.JBar]:
    rows = s.execute(
        select(Bar)
        .where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time > since, Bar.close_time <= until)
        .order_by(Bar.close_time)
    ).scalars()
    return [JJ.JBar(b.close_time, b.o, b.h, b.l, b.c) for b in rows]


def _bar_open(bars: list[JJ.JBar], open_at: datetime) -> JJ.JBar | None:
    return next((b for b in bars if b.close_time == open_at + timedelta(minutes=1)), None)


def _last_close_at(s: Session, symbol: str, at: datetime) -> Decimal | None:
    row = s.execute(
        select(Bar.c).where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time <= at).order_by(Bar.close_time.desc())
    ).first()
    return None if row is None else row[0]


def jj_sessions(rules: RulesConfig, at: datetime, calendar: CalendarProvider) -> list[tuple[str, datetime, int]]:
    """Every JJ session whose replay window contains `at`: (name, open time, window minutes)."""
    cfg = rules.strategy.jj_fpt_cfg
    day = at.astimezone(ET).date()
    out: list[tuple[str, datetime, int]] = []
    span = cfg.window_minutes + cfg.extend_minutes
    for x in cfg.sessions:
        if x.enabled:
            o = _et_at(day, x.open)
            if o < at <= o + timedelta(minutes=span):
                out.append((x.name, o, cfg.window_minutes))
    if cfg.news_session:
        o = _et_at(day, cfg.news_time)
        ny = _et_at(day, "09:30")
        if o < at <= ny and _news_at(calendar, day, o):
            out.append(("NEWS", o, int((ny - o).total_seconds() // 60)))
    return out


def _news_at(calendar: CalendarProvider, day: date, when: datetime) -> bool:
    """#8: an EXPECTED red-folder (high-impact USD) event scheduled at `when`."""
    cal = calendar(day) or []
    return any(e.currency == "USD" and e.impact == "high" and e.at == when for e in cal)


def _jj_input(
    s: Session, rules: RulesConfig, calendar: CalendarProvider, name: str, open_at: datetime, window: int,
    bars: list[JJ.JBar],
) -> JJ.SessionInput:  # fmt: skip
    cfg = rules.strategy.jj_fpt_cfg
    day = open_at.date()
    first = _bar_open(bars, open_at)
    ref = _last_close_at(s, cfg.symbol, open_at - timedelta(hours=cfg.htf_hours))
    htf = JJ.htf_bias(first.o, ref) if first is not None else None
    if name == "NEWS":  # #8 pre-news price = the open of the news candle; #20 no continuation
        return JJ.SessionInput(name, open_at, continuation=False, htf_bias=htf, window=window)
    if name == "NY":
        news = _et_at(day, cfg.news_time)
        nb = _bar_open(bars, news) if cfg.news_session and _news_at(calendar, day, news) else None
        return JJ.SessionInput(name, open_at, news_fair=None if nb is None else nb.o, htf_bias=htf)
    if name == "NY_PM":  # #13: revert toward the 09:30 price
        ny = _bar_open(_jbars(s, cfg.symbol, _et_at(day, "09:29"), _et_at(day, "09:31")), _et_at(day, "09:30"))
        return JJ.SessionInput(name, open_at, fair=None if ny is None else ny.o, htf_bias=htf)
    if name == "6PM":  # #19: gap vs the last close before the daily break
        return JJ.SessionInput(
            name, open_at, htf_bias=htf, gap_prior_close=_last_close_at(s, cfg.symbol, _et_at(day, "17:00"))
        )
    six = _bar_open(_jbars(s, cfg.symbol, _et_at(day, "17:59"), _et_at(day, "18:01")), _et_at(day, "18:00"))
    return JJ.SessionInput(name, open_at, alt_fair=None if six is None else six.o, htf_bias=htf)  # ASIA #12


def _jj_gate(rules: RulesConfig, at: datetime, calendar: CalendarProvider) -> tuple[bool, str, str]:
    """G1 for JJ entries: MNQ on, a calendar present, no Lucid news blackout. The session window is JJ's own (#3)."""
    cfg = rules.strategy.jj_fpt_cfg
    inst = rules.instrument(cfg.symbol)
    if not inst.enabled:
        return False, "INSTRUMENT_DISABLED", ""
    cal = calendar(at.astimezone(ET).date())
    if cal is None:
        return False, "CALENDAR_MISSING", "no calendar data = no trading"
    # D143: tighten-only — the wider of the EVAL and FUNDED news windows (funded news = hard breach), one gate for both
    firm_after = max(rules.eval.news_breach_min_after, rules.funded.news_breach_min_after)
    after = inst.news_after_min if inst.news_after_min is not None else firm_after
    before = max(
        rules.internal.no_entry_before_news_min, rules.eval.news_breach_min_before, rules.funded.news_breach_min_before
    )
    ev = news_block(at, cal, before, after)
    if ev is not None:
        return False, "NEWS_BLACKOUT", ev.title
    return True, "OK", ""


def run_jj_fpt(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """JJ F.P.T STRAT: replay each running session (engine/jj_fpt.py) and store a signal for a setup on THIS bar.
    Exits are the broker brackets (#33: hold to target or stop); the app's flat rules still apply."""
    cfg = rules.strategy.jj_fpt_cfg
    out = StrategyOutput()
    if exits_only:
        return out
    for name, open_at, window in jj_sessions(rules, at, calendar):
        bars = _jbars(s, cfg.symbol, open_at - timedelta(minutes=30), at)
        if not bars or bars[-1].close_time != at:
            continue
        start = next((i for i, b in enumerate(bars) if b.close_time == open_at + timedelta(minutes=1)), None)
        if start is None:
            continue  # no opening candle in the feed → no fair price → no trade
        sin = _jj_input(s, rules, calendar, name, open_at, window, bars)
        rep = JJ.replay(bars, start, sin, cfg)
        last = len(bars) - 1
        for x in (y for y in rep.signals if y.index == last):
            day = open_at.date().isoformat()
            key = f"{cfg.symbol}-{JJ_TAG}-{day}-{name}-{at.astimezone(ET).strftime('%H%M')}"
            if s.execute(select(Signal.id).where(Signal.model_key == key)).first() is not None:
                continue
            new = _new_signal(
                s,
                clock,
                symbol=cfg.symbol,
                key=key,
                direction=x.direction,
                at=at,
                gate=_jj_gate(rules, at, calendar),
                features={
                    "session": name,
                    "entry_kind": x.kind,
                    "tier": x.tier,
                    "fair": str(x.fair),
                    "room": None if x.room is None else str(x.room),
                    "stop_pts": str(x.stop_pts),
                    "target_pts": str(x.target_pts),
                    "epoch": x.epoch,
                    "fair_changes": len(rep.fair_changes),
                    "paper_only": cfg.paper_only,
                },
                plan=("JJ_FPT", x.entry, x.stop, x.take_profit, x.stop_pts, x.rr),
                rules=rules,
            )
            out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


GALA_TAG = "GALA"


def gala_input(s: Session, symbol: str, at: datetime, sessions: int) -> tuple[list[GP.GBar], list[GP.GBar]]:
    """D144: (earlier sessions, this session up to `at`) as 1-minute bars for engine/gala_pa.replay_day."""
    day0 = datetime.combine(at.astimezone(ET).date(), time(0), tzinfo=ET)
    rows = s.execute(
        select(Bar)
        .where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time > day0 - timedelta(days=sessions * 2 + 7))
        .where(Bar.close_time <= at)
        .order_by(Bar.close_time)
    ).scalars()
    hist: list[GP.GBar] = []
    today: list[GP.GBar] = []
    for b in rows:
        (today if b.close_time > day0 else hist).append(GP.GBar(b.close_time, b.o, b.h, b.l, b.c))
    return hist, today


def _gala_news_first_hour(calendar: CalendarProvider, day: date) -> bool:
    """A9: a high-impact USD event scheduled in the first hour (09:30–10:30 ET)."""
    lo, hi = _et_at(day, "09:30"), _et_at(day, "10:30")
    return any(e.currency == "USD" and e.impact == "high" and lo <= e.at <= hi for e in calendar(day) or [])


def run_gala_pa(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """D144 GALA PRICE ACTION: replay today's session (engine/gala_pa.py) on every 1-minute close; store a signal for
    an entry on THIS bar, and close a running trade at the rule sheet's time limit (B2). Brackets do stop / 2R.
    D152 (D4/D5): after the trim, every minute the runner's stop the replay chose so far is sent on (the order
    manager moves leg B only after the 2R leg really filled, ratchet only), so a missed move is retried."""
    cfg = rules.strategy.gala_pa_cfg
    out = StrategyOutput()
    t = at.astimezone(ET)
    if not (_et_at(t.date(), "09:30") < at <= _et_at(t.date(), "16:00")):
        return out
    hist, today = gala_input(s, cfg.symbol, at, cfg.history_sessions)
    if not today or today[-1].close_time != at:
        return out
    inst = rules.instrument(cfg.symbol)
    rep = GP.replay_day(hist, today, cfg, inst.tick, _gala_news_first_hour(calendar, t.date()))
    day = t.date().isoformat()
    for x in rep.signals:
        key = f"{cfg.symbol}-{GALA_TAG}-{day}-{x.time.astimezone(ET).strftime('%H%M')}"
        rn = x.runner
        timed = (x.outcome == "TIME" and x.exit_time == at) or (
            rn is not None and rn.outcome == "TIME" and rn.exit_time == at
        )
        runner_stop = rn.stop_at(at) if rn is not None and (rn.exit_time is None or rn.exit_time > at) else None
        if timed or runner_stop is not None:
            row = s.execute(select(Signal.id).where(Signal.model_key == key)).first()
            if row is not None and timed:
                out.exits.append((row[0], "GALA_TIME_EXIT"))
            if row is not None and runner_stop is not None:
                out.stop_moves.append((row[0], runner_stop, "GALA_CANDLE_TRAIL"))
        if x.time != at or exits_only:
            continue
        if s.execute(select(Signal.id).where(Signal.model_key == key)).first() is not None:
            continue
        new = _new_signal(
            s,
            clock,
            symbol=cfg.symbol,
            key=key,
            direction=x.direction,
            at=at,
            gate=_gate(rules, cfg.symbol, at, calendar),
            features={
                "setup": x.setup,
                "level": str(x.level),
                "attempt": x.attempt,
                "trend": rep.trend,
                "stop_pts": str(x.stop_pts),
                "paper_only": cfg.paper_only,
                **({} if x.runner_target is None else {"runner_target": str(x.runner_target)}),  # D152 D4/D5
            },
            plan=("GALA_PA", x.entry, x.stop, x.take_profit, x.stop_pts, x.rr),
            rules=rules,
        )
        out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def session_mbars(s: Session, symbol: str, at: datetime) -> list[CO.MBar]:
    """This ET session's RTH 1-minute bars (09:30, `at`] with volume — input of the CONTI / OKALA engines."""
    o = _et_at(at.astimezone(ET).date(), "09:30")
    rows = s.execute(
        select(Bar)
        .where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time > o, Bar.close_time <= at)
        .order_by(Bar.close_time)
    ).scalars()
    return [CO.MBar(b.close_time, b.o, b.h, b.l, b.c, b.v or Decimal(0)) for b in rows]


def _key_id(s: Session, key: str) -> int | None:
    row = s.execute(select(Signal.id).where(Signal.model_key == key)).first()
    return None if row is None else int(row[0])


def run_conti_orb(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """D146 CONTI ORB: replay today's range breakout; a signal on THIS bar, the 15:30 time exit (B6)."""
    cfg = rules.strategy.conti_orb_cfg
    out = StrategyOutput()
    today = session_mbars(s, cfg.symbol, at)
    if not today or today[-1].close_time != at:
        return out
    rep = CO.replay_day(today, cfg, rules.instrument(cfg.symbol).tick)
    day = at.astimezone(ET).date().isoformat()
    for x in rep.signals:
        key = f"{cfg.symbol}-CORB-{day}-{x.time.astimezone(ET).strftime('%H%M')}"
        sid = _key_id(s, key)
        if x.outcome == "TIME" and x.exit_time == at and sid is not None:
            out.exits.append((sid, "CORB_TIME_EXIT"))
        if x.time != at or exits_only or sid is not None:
            continue
        new = _new_signal(
            s, clock, symbol=cfg.symbol, key=key, direction=Direction.LONG, at=at,
            gate=_gate(rules, cfg.symbol, at, calendar),
            features={"range_high": str(x.range_high), "range_low": str(x.range_low), "paper_only": cfg.paper_only},
            plan=("CONTI_ORB", x.entry, x.stop, x.take_profit, x.risk_pts, x.rr), rules=rules,
        )  # fmt: skip
        out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_conti_vwap(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """D147 CONTI VWAP: replay the session; a signal on a close across VWAP, an exit on a close back through (C5)
    or at 15:30. A reversal on the same bar is stored too; the controller waits for flat (D139)."""
    cfg = rules.strategy.conti_vwap_cfg
    out = StrategyOutput()
    today = session_mbars(s, cfg.symbol, at)
    if not today or today[-1].close_time != at:
        return out
    day = at.astimezone(ET).date().isoformat()
    for x in CV.replay_day(today, cfg, rules.instrument(cfg.symbol).tick):
        key = f"{cfg.symbol}-CVWAP-{day}-{x.time.astimezone(ET).strftime('%H%M')}"
        sid = _key_id(s, key)
        if x.outcome in ("CROSS", "TIME") and x.exit_time == at and sid is not None:
            out.exits.append((sid, f"CVWAP_{x.outcome}"))
        if x.time != at or exits_only or sid is not None:
            continue
        risk = (x.entry - x.stop) * x.direction.sign
        rr = (x.take_profit - x.entry) * x.direction.sign / risk
        new = _new_signal(
            s, clock, symbol=cfg.symbol, key=key, direction=x.direction, at=at,
            gate=_gate(rules, cfg.symbol, at, calendar),
            features={"vwap": str(x.vwap), "paper_only": cfg.paper_only},
            plan=("CONTI_VWAP", x.entry, x.stop, x.take_profit, risk, rr), rules=rules,
        )  # fmt: skip
        out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_okala_8020(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """D145 OKALA 8020: replay the session; a signal (or a same-direction ADD after TP1) on THIS 3-minute close,
    the time exit when the replay says so. TP1 / break even / runner are the broker legs (controller)."""
    cfg = rules.strategy.okala_8020_cfg
    out = StrategyOutput()
    today = session_mbars(s, cfg.symbol, at)
    if not today or today[-1].close_time != at:
        return out
    day = at.astimezone(ET).date().isoformat()
    for x in OK.replay_day(today, cfg, rules.instrument(cfg.symbol).tick).signals:
        key = f"{cfg.symbol}-OKALA-{day}-{x.time.astimezone(ET).strftime('%H%M')}"
        sid = _key_id(s, key)
        if x.outcome == "TIME" and x.exit_time == at and sid is not None:
            out.exits.append((sid, "OKALA_TIME_EXIT"))
        if x.time != at or exits_only or sid is not None:
            continue
        risk = (x.entry - x.stop) * x.direction.sign
        rr = (x.runner_target - x.entry) * x.direction.sign / risk
        new = _new_signal(
            s, clock, symbol=cfg.symbol, key=key, direction=x.direction, at=at,
            gate=_gate(rules, cfg.symbol, at, calendar),
            features={"setup": x.setup, "confluences": x.confluences, "tp1": str(x.tp1), "add_no": x.add_no,
                      "be_cover_pts": str(cfg.be_cover_pts), "paper_only": cfg.paper_only,
                      "entry_bars": f"{cfg.entry_minutes}m (200 s not possible from 1-minute bars)"},
            plan=("OKALA_8020", x.entry, x.stop, x.runner_target, risk, rr), rules=rules,
        )  # fmt: skip
        out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_bruni_structure(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """D148 BRUNI STRUCTURE: replay the New York session on the 15-minute structure; a signal on THIS 1-minute bar
    (price back in the triple-print zone), the time exit when the replay says so."""
    cfg = rules.strategy.bruni_structure_cfg
    out = StrategyOutput()
    today = session_mbars(s, cfg.symbol, at)
    if not today or today[-1].close_time != at:
        return out
    day0 = _et_at(at.astimezone(ET).date(), "00:00")
    rows = s.execute(
        select(Bar)
        .where(
            Bar.symbol == cfg.symbol,
            Bar.tf == "1",
            Bar.close_time > day0 - timedelta(days=cfg.history_sessions * 2 + 7),
        )
        .where(Bar.close_time <= day0)
        .order_by(Bar.close_time)
    ).scalars()
    hist = [CO.MBar(b.close_time, b.o, b.h, b.l, b.c, b.v or Decimal(0)) for b in rows]
    rep = BR.replay_day(hist, today, cfg, rules.instrument(cfg.symbol).tick)
    day = at.astimezone(ET).date().isoformat()
    for x in rep.signals:
        key = f"{cfg.symbol}-BRUNI-{day}-{x.time.astimezone(ET).strftime('%H%M')}"
        sid = _key_id(s, key)
        if x.outcome == "TIME" and x.exit_time == at and sid is not None:
            out.exits.append((sid, "BRUNI_TIME_EXIT"))
        if x.time != at or exits_only or sid is not None:
            continue
        risk = (x.entry - x.stop) * x.direction.sign
        rr = (x.take_profit - x.entry) * x.direction.sign / risk
        new = _new_signal(
            s, clock, symbol=cfg.symbol, key=key, direction=x.direction, at=at,
            gate=_gate(rules, cfg.symbol, at, calendar),
            features={"context": x.context, "zone": [str(x.zone[0]), str(x.zone[1])], "regime": x.regime,
                      "flipped": x.flipped, "paper_only": cfg.paper_only},
            plan=("BRUNI_STRUCTURE", x.entry, x.stop, x.take_profit, risk, rr), rules=rules,
        )  # fmt: skip
        out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_candace_ict(
    s: Session,
    rules: RulesConfig,
    clock: Clock,
    calendar: CalendarProvider,
    at: datetime,
    exits_only: bool = False,
    cfg: CandaceIctCfg | None = None,
    mode: str = "CANDACE_ICT",
) -> StrategyOutput:
    """D149 CANDACE ICT SCALP: replay today's regular-hours bars; a signal on THIS bar, the max-hold exit.
    D165: the same code runs on MGC with `cfg` = the MGC CANDACE settings and `mode` = "MGC_CANDACE"."""
    mgc = cfg is not None
    cfg = cfg or rules.strategy.candace_ict_cfg
    out = StrategyOutput()
    day0 = _et_at(at.astimezone(ET).date(), "00:00")
    rows = list(
        s.execute(
            select(Bar)
            .where(Bar.symbol == cfg.symbol, Bar.tf == "1", Bar.close_time > day0 - timedelta(days=7))
            .where(Bar.close_time <= at)
            .order_by(Bar.close_time)
        ).scalars()
    )
    if not rows or rows[-1].close_time != at:
        return out
    # research parity (model_qa 2 / H1): regular-hours bars only; 7 calendar days keep ~4 RTH sessions over a weekend
    mb = CI.rth_only([CO.MBar(b.close_time, b.o, b.h, b.l, b.c, b.v or Decimal(0)) for b in rows])
    hist, today = [b for b in mb if b.close_time <= day0], [b for b in mb if b.close_time > day0]
    day = at.astimezone(ET).date().isoformat()
    for x in CI.replay_day(hist, today, cfg, rules.instrument(cfg.symbol).tick).signals:
        key = f"{cfg.symbol}-CAND-{day}-{x.time.astimezone(ET).strftime('%H%M')}"
        sid = _key_id(s, key)
        if x.outcome == "TIME" and x.exit_time == at and sid is not None:
            out.exits.append((sid, "CAND_TIME_EXIT"))
        if x.time != at or exits_only or sid is not None:
            continue
        risk = (x.entry - x.stop) * x.direction.sign
        rr = (x.take_profit - x.entry) * x.direction.sign / risk
        new = _new_signal(
            s, clock, symbol=cfg.symbol, key=key, direction=x.direction, at=at,
            gate=_gate(rules, cfg.symbol, at, calendar, True if mgc else None),
            features={"session": x.session, "swept": x.swept.kind, "confluences": x.confluences, "grade": x.grade,
                      "size_mult": str(x.size_mult), "paper_only": cfg.paper_only},
            plan=(mode, x.entry, x.stop, x.take_profit, risk, rr), rules=rules,  # MGC_CANDACE is no ADVISED_MODE: no-op
        )  # fmt: skip
        out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_late_day(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """D166 LATE-DAY MOMENTUM (3rd edge of the fast pass): trend of the session so far, followed at 15:00 with a 60 pt
    stop, flat at 15:59. One entry a day; the controller decides per account whether the plan's fast pass applies."""
    cfg = rules.strategy.late_day_cfg
    out = StrategyOutput()
    day = at.astimezone(ET).date().isoformat()
    if LD.is_flat_time(at, cfg):
        for sig in _today_signals(s, cfg.symbol, "LATE", day):
            if sig.features.get("state") == "OPEN":
                _close(s, sig, "LATE_FLAT_1559", at, clock)
                out.exits.append((sig.id, "LATE_FLAT_1559"))
        return out
    if exits_only:
        return out
    day0 = _et_at(at.astimezone(ET).date(), "00:00")
    rows = s.execute(
        select(Bar)
        .where(Bar.symbol == cfg.symbol, Bar.tf == "1", Bar.close_time > day0 - timedelta(days=HISTORY_CALENDAR_DAYS))
        .where(Bar.close_time <= at)
        .order_by(Bar.close_time)
    ).scalars()
    mb = [CO.MBar(b.close_time, b.o, b.h, b.l, b.c, b.v or Decimal(0)) for b in rows]
    hist, today = [b for b in mb if b.close_time <= day0], [b for b in mb if b.close_time > day0]
    x = LD.decide(hist, today, cfg, rules.instrument(cfg.symbol).tick, at)
    key = f"{cfg.symbol}-LATE-{day}-{at.astimezone(ET).strftime('%H%M')}"
    if x is None or _key_id(s, key) is not None:
        return out
    new = _new_signal(
        s, clock, symbol=cfg.symbol, key=key, direction=x.direction, at=at,
        gate=_gate(rules, cfg.symbol, at, calendar),
        features={"trend_pts": str(x.trend_pts), "atr": str(x.atr), "paper_only": cfg.paper_only},
        plan=("LATE_DAY", x.entry, x.stop, x.take_profit, x.risk_pts, x.rr), rules=rules,
    )  # fmt: skip
    out.updates.append(SignalUpdate(new.id, new.model_key, new.status, new.skip_reason, None))
    return out


def run_order_flow_auction(
    s: Session, rules: RulesConfig, clock: Clock, calendar: CalendarProvider, at: datetime, exits_only: bool = False
) -> StrategyOutput:
    """D150 ORDER FLOW · AUCTION (IMRE): replay the cash session from stored 1-minute bars (estimated delta); a
    signal on THIS bar. Exits are the broker legs (first target + stop to entry, then the second target)."""
    cfg = rules.strategy.order_flow_cfg.auction
    out = StrategyOutput()
    if exits_only:
        return out
    today = session_mbars(s, cfg.symbol, at)
    if not today or today[-1].close_time != at:
        return out
    day0 = _et_at(at.astimezone(ET).date(), "00:00")
    rows = s.execute(
        select(Bar)
        .where(Bar.symbol == cfg.symbol, Bar.tf == "1")
        .where(Bar.close_time > day0 - timedelta(days=cfg.history_sessions * 2 + 7), Bar.close_time <= day0)
        .order_by(Bar.close_time)
    ).scalars()
    hist = [CO.MBar(b.close_time, b.o, b.h, b.l, b.c, b.v or Decimal(0)) for b in rows]
    rep = AU.replay_day(hist, today, cfg, rules.instrument(cfg.symbol).tick)
    day = at.astimezone(ET).date().isoformat()
    for x in rep.signals:
        if x.time != at:
            continue
        key = f"{cfg.symbol}-OFA-{day}-{x.time.astimezone(ET).strftime('%H%M')}"
        if _key_id(s, key) is not None:
            continue
        risk = (x.entry - x.stop) * x.direction.sign
        rr = (x.tp2 - x.entry) * x.direction.sign / risk
        new = _new_signal(
            s, clock, symbol=cfg.symbol, key=key, direction=x.direction, at=at,
            gate=_gate(rules, cfg.symbol, at, calendar),
            features={"setup": x.setup, "regime": rep.regime, "weekly": rep.weekly, "open_vs_value": rep.open_vs_value,
                      "tp1": str(x.tp1), "be_cover_pts": "0", "risk_share": str(x.risk_share),
                      "delta": "ESTIMATED", "paper_only": cfg.paper_only},
            plan=("ORDER_FLOW_AUCTION", x.entry, x.stop, x.tp2, risk, rr), rules=rules,
        )  # fmt: skip
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
    if st.pm_fade and symbol == st.pm_fade_cfg.symbol:
        r = run_pm_fade(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.ai_bias and symbol == st.ai_bias_cfg.symbol:
        r = run_ai_bias(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.jj_fpt and symbol == st.jj_fpt_cfg.symbol:
        r = run_jj_fpt(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.order_flow and st.order_flow_cfg.auction.enabled and symbol == st.order_flow_cfg.auction.symbol:
        r = run_order_flow_auction(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
    if st.candace_ict and symbol == st.candace_ict_cfg.symbol:
        r = run_candace_ict(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.fast_pass_late_day and symbol == st.late_day_cfg.symbol:  # D166: the controller gates it per account
        r = run_late_day(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.mgc_noise_candace:  # D165: the MGC pair — own market switch, fixed 1 micro, no AI advisor
        mc = st.mgc_noise_candace_cfg
        if symbol == mc.noise.symbol:
            r = run_noise(s, rules, clock, calendar, at, exits_only, mc.noise, "MGC_NOISE")
            out.updates += r.updates
            out.exits += r.exits
        if symbol == mc.candace.symbol:
            r = run_candace_ict(s, rules, clock, calendar, at, exits_only, mc.candace, "MGC_CANDACE")
            out.updates += r.updates
            out.exits += r.exits
    if st.bruni_structure and symbol == st.bruni_structure_cfg.symbol:
        r = run_bruni_structure(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.okala_8020 and symbol == st.okala_8020_cfg.symbol:
        r = run_okala_8020(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.conti_vwap and symbol == st.conti_vwap_cfg.symbol:
        r = run_conti_vwap(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.conti_orb and symbol == st.conti_orb_cfg.symbol:
        r = run_conti_orb(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    if st.gala_pa and symbol == st.gala_pa_cfg.symbol:
        r = run_gala_pa(s, rules, clock, calendar, at, exits_only)
        out.updates += r.updates
        out.exits += r.exits
        out.stop_moves += r.stop_moves
    if st.ai_duo and symbol in st.ai_duo_cfg.markets:  # after NOISE: on a same-bar tie NOISE wins (D83)
        r = run_ai_duo(s, rules, clock, calendar, at, symbol, exits_only)
        out.updates += r.updates
        out.exits += r.exits
    out.exits += order_flow_exits(s, rules, clock, symbol, at).exits
    bar = s.execute(
        select(Bar).where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time <= at).order_by(Bar.close_time.desc())
    ).first()
    if bar is not None:  # D111: ZONE trail line (new same-direction event), checked on the closed bar
        out.exits += zone_trail_exits(s, symbol, bar[0].c, at, clock).exits
    s.commit()
    return out
