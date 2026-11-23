"""Dashboard + Today (§18): per-account safety numbers, today's bias, signals and trades. Read-only."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.automation import state as stt
from app.clock import ET, session_date
from app.execution.adapters.base import BrokerError
from app.management.drawdown_guard import GuardCfgView, guard_active
from app.models import Account, BiasDecision, Signal, Trade
from app.payouts.service import consistency_view
from app.phases.phase_engine import stage_rules
from app.risk.checks import dll_remaining
from app.risk.cushion import cushion_level, cushion_share
from app.risk.eval_mode import eval_mode_effective
from app.risk.risk_base import money
from app.risk.split_risk import split_active
from app.signals.service import today_bias

router = APIRouter(prefix="/api")


def _s(x: Decimal | None) -> str | None:
    return None if x is None else str(x)


def _fast_share(db: Session, a: Account, r: Any) -> Decimal:
    """Lucid microscalping metric: % of profit from trades held ≤ firm_microscalp_hold_seconds (limit 50%)."""
    from app.management.exits import rapid_profit_share

    rows = db.execute(select(Trade).where(Trade.account_id == a.id, Trade.closed_at.is_not(None))).scalars()
    data = [
        (t.pnl_usd or Decimal(0), (t.closed_at - t.opened_at).total_seconds()) for t in rows if t.closed_at is not None
    ]
    return rapid_profit_share(data, r.behavior.firm_microscalp_hold_seconds)


def _cushion(r: Any, eq: Decimal, mll: Decimal | None, max_loss: Decimal) -> dict[str, Any] | None:
    """D122: current cushion level (equity incl. open P&L − MLL vs the MLL distance) + which strategies use it."""
    if mll is None:
        return None
    from app.automation.controller import cushion_levels
    from app.config import TRAIL_STRATEGIES

    cc, dt = r.strategy.cushion, r.strategy.dynamic_trail
    share = cushion_share(eq, mll, max_loss)
    return {
        "usd": str(eq - mll),
        "pct": str((share * 100).quantize(Decimal("0.1"))),
        "level": cushion_level(share, cushion_levels(cc)),
        "strategies": [k.upper() for k in TRAIL_STRATEGIES if getattr(cc, k)],
        "trail_strategies": [k.upper() for k in TRAIL_STRATEGIES if getattr(dt, k)],
        "unverified": True,
    }


@router.get("/dashboard")
async def dashboard(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    st = request.app.state
    c, r, now = st.controller, st.rules.rules, st.clock.now()
    accounts = []
    for a in db.execute(select(Account).order_by(Account.priority, Account.id)).scalars():
        row: dict[str, Any] = {"id": a.id, "label": a.label, "stage": a.stage, "paper": a.is_sim, "armed": a.armed}
        row["paused"] = a.paused_reason
        try:
            if a.broker_account_id not in c.adapter.accounts:
                raise BrokerError("broker not connected")
            bal = await c.adapter.get_balance(a.broker_account_id)
            opnl = c.adapter.open_pnl(a.broker_account_id)
        except BrokerError as e:
            accounts.append({**row, "error": str(e)})
            continue
        day = stt.day_state(db, a, opnl, now)
        dll = stt.dll_for(r, a)
        sr_ = stage_rules(r, a.stage, a.drawdown_type, a.dll_enabled)
        cons = stt.consistency(db, a, r)
        eq = bal + opnl
        start = a.starting_balance or Decimal(0)
        row |= {
            "balance": str(bal),
            "open_pnl": str(opnl),
            "mll": _s(a.mll),
            "to_mll": _s(eq - a.mll) if a.mll is not None else None,
            "kill_at": str(r.internal.kill_switch_mll_distance),
            "max_loss": str(max_loss := stage_rules(r, a.stage, a.drawdown_type, a.dll_enabled).max_loss),
            "cushion": _cushion(r, eq, a.mll, max_loss),  # D122
            "dll_limit": _s(dll),
            "dll_scale_pct": _s(sr_.dll_scale_pct),  # LucidScale (Pro): % of peak EOD profit once the MLL is locked
            "dll_scaled": dll != sr_.dll,
            "today_pnl": str(day.today_pnl),
            "trades_today": day.trades_today,
            "dll_left": _s(dll_remaining(dll, day.today_pnl, day.today_peak_pnl)) if dll is not None else None,
            "consistency_cap": _s(cons.cap) if cons else None,
            "consistency_stop": _s(cons.day_stop) if cons else None,
            "payout_consistency": consistency_view(db, r, a),  # D89 (FUNDED + Pro only)
            "target_left": str(max(start + r.eval.profit_target - bal, Decimal(0))) if a.stage == "EVAL" else None,
            "mll_locked": a.mll_locked,
            "guard_on": guard_active(a.drawdown_type, bool(a.mll_locked), GuardCfgView(r.drawdown_guard.mode)),
            "eval_mode_on": eval_mode_effective(a.stage, a.eval_mode, st.rules.eval_mode_on),
            "day_net_r": str(stt.day_stats(db, a, now).day_net_r),
            "day_lockin_r": str(r.internal.day_lockin_r),
            "day_lockin": stt.day_stats(db, a, now).day_net_r >= r.internal.day_lockin_r,
            "fast_profit_pct": str(_fast_share(db, a, r)),
            "idle_days": (now - (a.last_trade_at or a.stage_started_at or now)).days,
            "never_traded": a.last_trade_at is None,  # B8: "No trades yet" instead of "Last trade 0d ago"
            "idle_alert_days": r.behavior.inactivity_alert_days,
            "idle_delete_days": r.behavior.firm_inactivity_delete_days,
            "fast_warn_pct": str(r.behavior.rapid_trade_warn_pct),
            "fast_limit_pct": str(r.behavior.firm_microscalp_pct),
            "fast_hold_s": r.behavior.firm_microscalp_hold_seconds,
        }
        accounts.append(row)
    sess = session_date(now)
    bias = {sym: today_bias(db, sess, i.bias_proxy) for sym, i in r.instruments.items() if i.enabled}
    return {"session": sess.isoformat(), "mode": c.mode, "bias": bias, "accounts": accounts}


@router.get("/today")
def today(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    now = request.app.state.clock.now()
    since = now - timedelta(hours=24)
    sigs = db.execute(select(Signal).where(Signal.bar_time >= since).order_by(Signal.id.desc())).scalars()
    trades = db.execute(select(Trade).where(Trade.opened_at >= since).order_by(Trade.id.desc())).scalars()
    return {
        "signals": [
            {
                "id": x.id,
                "symbol": x.symbol,
                "profile": x.profile,
                "direction": x.direction,
                "status": x.status,
                "skip_reason": x.skip_reason,
                "score": _s(x.score),
                "at": x.bar_time.isoformat(),
            }
            for x in sigs
        ],
        "trades": [
            {
                "id": t.id,
                "account_id": t.account_id,
                "symbol": t.symbol,
                "direction": t.direction,
                "qty": t.qty,
                "entry": str(t.entry),
                "exit": _s(t.exit),
                "pnl": _s(t.pnl_usd),
                "net_r": _s(t.net_r),
                "exit_reason": t.exit_reason,
                "opened_at": t.opened_at.isoformat(),
            }
            for t in trades
        ],
    }


@router.get("/calendar")
def calendar(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    st = request.app.state
    sess = session_date(st.clock.now())
    ev = st.calendar(sess)
    store = st.calendar
    return {
        "session": sess.isoformat(),
        "loaded": ev is not None,
        "events": [{"at": e.at.isoformat(), "title": e.title} for e in (ev or [])],
        "fetched_at": store.fetched_at.isoformat() if getattr(store, "fetched_at", None) else None,
        "error": getattr(store, "error", None),
        "source": "ForexFactory weekly feed (USD high impact)",
    }


@router.get("/bias")
def bias_today(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    from app.models import BiasDecision

    sess = session_date(request.app.state.clock.now())
    rows = db.execute(
        select(BiasDecision).where(BiasDecision.session_date == sess).order_by(BiasDecision.id.desc())
    ).scalars()
    return {
        "session": sess.isoformat(),
        "decisions": [
            {
                "proxy": b.proxy,
                "raw": b.raw_rating,
                "mapped": b.mapped,
                "reasoning": b.reasoning.split("\n\n[Blend] ")[0][:4000],
                "blend": b.reasoning.split("\n\n[Blend] ", 1)[1][:600] if "\n\n[Blend] " in b.reasoning else None,
            }
            for b in rows
        ],
    }


@router.post("/bias/run")
async def bias_run(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    """Runs TradingAgents now for proxies without a valid bias today (retries failures; never re-runs successes)."""
    from app.bias.service import run_bias
    from app.crypto import Vault

    st = request.app.state
    sess = session_date(st.clock.now())
    vault = Vault(st.settings.master_key.get_secret_value())
    from app.bias.service import openbb_context

    ran = await run_bias(
        db,
        st.ta,
        vault,
        st.rules.rules,
        st.clock,
        sess,
        st.controller.notify,
        vt_root=st.settings.vt_root,
        context=openbb_context(st),
    )
    return {"ran": ran}


def _tier(t: Any) -> dict[str, Any]:
    return {
        "account_size": str(t.account_size),
        "contracts": t.contracts,
        "brake_below": None if t.brake_below is None else str(t.brake_below),
        "brake_contracts": t.brake_contracts,
        "taper_below_remaining": None if t.taper_below_remaining is None else str(t.taper_below_remaining),
        "taper_contracts": t.taper_contracts,
        "stop_usd": None if t.stop_usd is None else str(t.stop_usd),
    }


@router.get("/strategy")
async def strategy(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    """TradingAgents bias status + per-instrument feed state (D105: the LunqFX gates/model panel was removed)."""
    from app.models import ApiCredential
    from app.monitor.feed import feed_status

    st = request.app.state
    r, now = st.rules.rules, st.clock.now()
    sess = session_date(now)
    ver = await st.ta.version() if st.ta.installed() else None
    configured = (
        db.execute(select(ApiCredential).where(ApiCredential.provider == "tradingagents")).scalar_one_or_none()
        is not None
    )
    instruments = []
    for sym, i in r.instruments.items():
        feeds = []
        for (s_sym, prof), ss in st.market.states.items():
            if s_sym != sym:
                continue
            tf = 1 if prof == "TIGHT" else 5
            feeds.append(
                {
                    "profile": prof,
                    "feed": feed_status(ss.last_heartbeat_ms, tf, now, 2),
                    "data_feed": ss.data_feed,
                    "mso_trend": (ss.mso or {}).get("trend"),
                    "mso_osc": (ss.mso or {}).get("osc"),
                    "last_mso_event": ss.mso_events[-1][:2] if ss.mso_events else None,
                }
            )
        instruments.append(
            {
                "symbol": sym,
                "enabled": i.enabled,
                "proxy": i.bias_proxy,
                "bias": today_bias(db, sess, i.bias_proxy),
                "feeds": feeds,
            }
        )
    return {
        "tradingagents": {
            "installed_version": ver.data.get("version") if ver and ver.ok else None,
            "pinned_version": st.ta.pinned_version,
            "configured": configured,
            "schedule": r.schedule.bias,
        },
        "mso_enabled": False,  # D120: MSO removed
        "instruments": instruments,
        "one_to_one": r.one_to_one_mode.enabled,
    }


def _ta_mgc(db: Session, r: Any, sess: Any) -> dict[str, Any]:
    """D84: latest TradingAgents MGC research (part of AI Duo) + today's MGC Duo decision, for the Strategy page."""
    from app.bias import ta_mgc_research as tr

    cfg = r.strategy.ta_mgc_cfg
    on = bool(r.strategy.ai_duo and "MGC" in r.strategy.ai_duo_cfg.markets)
    key = tr.connected(db)
    row = tr.latest(db, cfg.proxy, sess)
    if row is None:  # show the newest earlier report when today's has not run yet
        row = db.execute(
            select(BiasDecision)
            .where(BiasDecision.proxy == tr.research_proxy(cfg.proxy))
            .order_by(BiasDecision.id.desc())
            .limit(1)
        ).scalar_one_or_none()
    data = tr.payload(row) or {}
    sig = db.execute(
        select(Signal).where(Signal.model_key.like("MGC-DUO-%")).order_by(Signal.id.desc()).limit(1)
    ).scalar_one_or_none()
    return {
        "enabled": on,
        "connected": key,
        "message": None if key else tr.NOT_CONNECTED,
        "research": None
        if row is None
        else {
            "day": row.session_date.isoformat(),
            "label": row.raw_rating,
            "setup": data.get("setup"),
            "vt": data.get("vt"),
            "vt_note": data.get("vt_note", ""),
            "error": data.get("error", ""),
            "report": str(data.get("report", ""))[:1200],
        },
        "decision": None
        if sig is None
        else {
            "day": sig.model_key.rsplit("-DUO-", 1)[-1],
            "status": sig.status,
            "code": sig.skip_reason or "TAKEN",
            "direction": sig.direction,
            "mode": (sig.features or {}).get("mode", "PULLBACK"),
            "below_preferred_2r": bool((sig.features or {}).get("below_preferred_2r")),
        },
    }


def _presets(r: Any, plan: str = "") -> dict[str, Any]:
    """D82: NOISE strategy presets (config/strategy_presets.yaml) — static research labels + what each one sets.
    D137: each preset's pass / bust is read from config/eval_odds.yaml (preset odds_plan + odds_table, current toggle);
    raw shares of the study (pass + bust may be < 100: stuck / open evaluations are not counted as either)."""
    from app.config import SizeTierCfg, load_presets
    from app.eval_odds import odds_view

    rows = []
    for key, p in load_presets().items():
        ov = p["overlay"]
        nc = ov.get("noise_cfg", {})
        trig, lock = nc.get("profit_lock_trigger_pts"), nc.get("profit_lock_pts")
        ov_odds = odds_view(p["odds_plan"], p["odds_table"], r.strategy.eod_closed_balance)
        rows.append(
            {
                "key": key,
                "label": p["label"],
                "summary": p["summary"],
                "account": p["account"],
                "study": p["study"],
                "pass_pct": ov_odds["pass_pct"],
                "bust_pct": ov_odds["bust_pct"],
                "odds_text": ov_odds["text"],
                "held_out": p["held_out"],
                "recommended": p["recommended"],
                "superseded": bool(p.get("superseded", False)),  # D134: kept selectable, labelled
                "warning": p["warning"],
                "fade": bool(ov.get("pm_fade")),
                "stop_usd": None if nc.get("emergency_stop_usd") is None else str(nc["emergency_stop_usd"]),
                "profit_lock": None if trig is None else {"trigger_pts": str(trig), "lock_pts": str(lock)},
                "size": [_tier(SizeTierCfg.model_validate(x)) for x in ov["size_table"]],
                "matches_plan": any(Decimal(str(x["account_size"])) == r.account_size for x in ov["size_table"]),
            }
        )
    return {
        "active": r.strategy.preset,
        "setting": "strategy.preset",
        "plan_account_size": str(r.account_size),
        "rows": rows,
    }


def _jj_fit(r: Any) -> str:
    """D143: the Lucid fit on the ACTIVE plan for a fresh EVAL account (same math as the controller)."""
    from decimal import Decimal

    from app.engine.jj_fpt import contracts_for, trade_risk_usd
    from app.phases.phase_engine import firm_max_micros, stage_rules
    from app.risk.consistency import eval_limits

    c, i = r.strategy.jj_fpt_cfg, r.internal
    sr = stage_rules(r, "EVAL")
    pct = r.eval.consistency_max_day_pct
    cons = eval_limits(r.eval.profit_target, pct, i.consistency_day_stop_buffer_pct) if pct is not None else None
    risk = trade_risk_usd(
        sr.max_loss,
        c.risk_pct_of_drawdown,
        c.stop_after_losses,
        sr.dll,
        c.dll_use_pct,
        sr.max_loss - i.kill_switch_mll_distance,
        r.strategy.max_trade_risk_usd,
        cons.day_stop if cons is not None else None,
    )
    m = r.instrument(c.symbol)
    slip = m.slippage_ticks or r.trade_plan.slippage_ticks
    cap = min(firm_max_micros(r, "EVAL", Decimal(0)), i.internal_max_micros)
    n = [min(contracts_for(risk, Decimal(x), m.tick, m.tick_value, m.fee_rt, slip), cap) for x in ("25", "12.5")]
    return (
        f"; Lucid fit on this plan (EVAL, {sr.drawdown_type.upper()} drawdown): ${risk} per trade, "
        f"{n[0]} micros at 25 pt / {n[1]} at 12.5 pt, max {c.stop_after_losses} losses per session "
        f"(≤ {c.dll_use_pct * 100:.0f}% of the DLL, consistency day stop and MLL room)"
    )


def jj_rules(r: Any) -> list[dict[str, object]]:
    """JJ F.P.T STRAT card: his rules (docs/JJ_FPT_RULES.md) with the plan's live numbers and switches."""
    c = r.strategy.jj_fpt_cfg
    on = [f"{x.name} {x.open}" for x in c.sessions if x.enabled]
    off = [f"{x.name} {x.open}" for x in c.sessions if not x.enabled]
    p = c.risk_pct_of_drawdown * 100
    return [
        {
            "key": "SESSIONS",
            "on": bool(on),
            "rule": f"first {c.window_minutes} min of each open, ET: "
            f"{', '.join(on) or 'none'}{' (off: ' + ', '.join(off) + ')' if off else ''}; {c.symbol}, 1-minute closes",
        },
        {"key": "FAIR PRICE", "on": True, "rule": "the session's opening price"},
        {
            "key": "NEWS",
            "on": c.news_session,
            "rule": f"{c.news_time} red-folder news is priced in: revert to the "
            "pre-news price until 09:30; at 09:30 the open is fair only if it continues away from it",
        },
        {
            "key": "CONTINUATION",
            "on": True,
            "rule": f"first {c.continuation_minutes} min: opening-candle colour, must "
            "break the previous candle; more entries on a break of structure that way; "
            f"{c.base_stop_pts}/{c.base_target_pts} pt, or {c.big_stop_pts}/{c.big_target_pts} when the opening body > "
            f"{c.big_open_body_pts} pt",
        },
        {
            "key": "HTF BIAS",
            "on": c.htf_filter,
            "rule": f"continuation must match the reverse of the last {c.htf_hours} h",
        },
        {"key": "WICK", "on": c.wick_rejection_filter, "rule": "no continuation into a wick rejecting that side"},
        {
            "key": "REVERSION",
            "on": True,
            "rule": f"minute {c.continuation_minutes}–{c.window_minutes}: toward fair "
            "only, on a break of structure (close beyond the last 3-bar swing) or a displacement (body > previous "
            "opposite-colour body, close beyond its wick)",
        },
        {
            "key": "ROOM",
            "on": True,
            "rule": f"≥ {c.room_full_min_pts} pt to fair → {c.base_stop_pts}/"
            f"{c.base_target_pts}; {c.room_small_min_pts}–{c.room_full_min_pts} → {c.small_stop_pts}/"
            f"{c.small_target_pts}{'' if c.small_room_tier else ' (OFF)'}; less → no trade",
        },
        {
            "key": "FAIR MOVES",
            "on": c.adapt_fair_price,
            "rule": f"a break of structure away from fair ≥ "
            f"{c.adjust_min_pts} pt beyond it → fair = middle of the last {c.consolidation_bars} bars",
        },
        {
            "key": "LOSSES",
            "on": True,
            "rule": f"after {c.bos_only_after_losses} losses in a row only breaks of "
            f"structure; {c.stop_after_losses} in a row → done for the session",
        },
        {
            "key": "SIZE",
            "on": True,
            "rule": f"{p:.0f}% of the account's drawdown per trade, same dollars for every "
            "stop size (50 pt ≈ half, 12.5 pt ≈ double the contracts)" + _jj_fit(r),
        },
        {"key": "ACCOUNTS", "on": c.one_account_per_trade, "rule": "one free account per trade, never copy trading"},
        {"key": "FUNDED", "on": c.funded_bos_only, "rule": "funded / live accounts take breaks of structure only"},
        {"key": "EXIT", "on": True, "rule": "hold to target or stop (broker bracket); the app's flat times apply"},
    ]


def fit_size_row(r: Any, c: Any, losses: int, stops: tuple[str, str]) -> str:
    """D144+: the Lucid fit on the ACTIVE plan for a fresh EVAL account (same math as the controller)."""
    from decimal import Decimal

    from app.engine.lucid_fit import contracts_for, trade_risk_usd
    from app.phases.phase_engine import firm_max_micros, stage_rules
    from app.risk.consistency import eval_limits

    i = r.internal
    sr = stage_rules(r, "EVAL")
    pct = r.eval.consistency_max_day_pct
    cons = eval_limits(r.eval.profit_target, pct, i.consistency_day_stop_buffer_pct) if pct is not None else None
    risk = trade_risk_usd(
        sr.max_loss, c.risk_pct_of_drawdown, losses, sr.dll, c.dll_use_pct,
        sr.max_loss - i.kill_switch_mll_distance, r.strategy.max_trade_risk_usd,
        cons.day_stop if cons is not None else None,
    )  # fmt: skip
    m = r.instrument(c.symbol)
    slip = m.slippage_ticks or r.trade_plan.slippage_ticks
    cap = min(firm_max_micros(r, "EVAL", Decimal(0)), i.internal_max_micros)
    n = [min(contracts_for(risk, Decimal(x), m.tick, m.tick_value, m.fee_rt, slip), cap) for x in stops]
    return (
        f"Lucid fit on this plan (EVAL, {sr.drawdown_type.upper()} drawdown): ${risk} per trade, {n[0]} micros at "
        f"{stops[0]} pt / {n[1]} at {stops[1]} pt stop, sized for {losses} losses a day"
    )


def _gala_fit(r: Any) -> str:
    c = r.strategy.gala_pa_cfg
    return fit_size_row(r, c, c.max_trades_per_day, ("10", "20"))


def conti_orb_rules(r: Any) -> list[dict[str, object]]:
    """CONTI ORB card (docs/CONTI_RULES.md part B; * = not from the video)."""
    c = r.strategy.conti_orb_cfg
    return [
        {"key": "RANGE", "on": True, "rule": f"high / low of 09:30–{c.range_end} ET (B1)"},
        {
            "key": "ENTRY",
            "on": True,
            "rule": f"LONG only on a 1-minute* close above the range high (B2/B3); "
            f"{c.max_trades_per_day}* trade a day, last entry {c.last_entry}*",
        },
        {"key": "STOP / TARGET", "on": True, "rule": f"stop = range low (B4); target {c.rr}R (B5)"},
        {"key": "TIME EXIT", "on": True, "rule": f"flat at {c.time_exit} ET if neither hit (B6)"},
        {
            "key": "SIZE",
            "on": True,
            "rule": "same dollars at risk, fewer micros on a wide range (B7); "
            + fit_size_row(r, c, c.max_trades_per_day, ("30", "60")),
        },
        {"key": "ACCOUNTS", "on": c.one_account_per_trade, "rule": "one free account per trade, never copy trading"},
    ]


def gala_rules(r: Any) -> list[dict[str, object]]:
    """GALA PRICE ACTION card: the rule sheet (docs/GALA_RULES.md) (* = not from the video)."""
    c = r.strategy.gala_pa_cfg
    return [
        {
            "key": "TREND",
            "on": True,
            "rule": f"hourly highs and lows (A2): HH+HL long, LH+LL short, else no trade (A3); "
            f"{c.history_sessions} sessions*, swing {c.trend_swing_lookback}*",
        },
        {
            "key": "LEVELS",
            "on": True,
            "rule": f"open of the colour-change hourly candle at a body pivot ({c.pivot_lookback}"
            "* each side, A4); a body through a level deletes it (A6); overnight = one candle (A7)",
        },
        {"key": "OPEN LEVEL", "on": c.use_open_level, "rule": "the day's opening price as a level (A5)*"},
        {
            "key": "SETUP",
            "on": True,
            "rule": "closer to the level in the trend's way → break-and-retest, else bounce "
            "(long) / rejection (short) (A8)",
        },
        {
            "key": "NEWS",
            "on": c.skip_news_first_hour,
            "rule": "no trade when high-impact news is in the first hour (A9)",
        },
        {
            "key": "WINDOW",
            "on": True,
            "rule": f"skip the first {c.skip_first_minutes} min (B1); entries "
            f"{c.window_start}–{c.window_end} ET* (B2); time exit after {c.max_hold_minutes} min",
        },
        {
            "key": "ENTRY CANDLE",
            "on": True,
            "rule": f"5-min wick ≤ {c.max_wick_through_pts}* pt through the level, body "
            f"on the right side (C2); skip hammers, wick ≥ {c.hammer_wick_body_mult}*× body (C4)",
        },
        {
            "key": "BREAK & RETEST",
            "on": True,
            "rule": f"5-min close beyond the level, retest within {c.max_retest_bars}* "
            "candles, a close back through cancels (C5/C6)",
        },
        {
            "key": "BOUNCE / REJECTION",
            "on": True,
            "rule": f"{c.bounce_candles} candles, bodies holding, wicks through (C7/C8)",
        },
        {
            "key": "STOP / TARGET",
            "on": True,
            "rule": f"{c.stop_buffer_ticks}* tick past the lowest / highest wick (D1); target {c.target_r}R (D3)",
        },
        {
            "key": "TRIM + TRAIL",
            "on": c.trim_at_target,
            "rule": f"2+ micros: about half off at {c.target_r}R (D4), then the stop moves to each closed 5-min "
            "candle's open "
            + ("every candle*" if c.runner_trail_after_entry else "until it is above entry")
            + f" (D5); runner target {c.runner_target_r}R*, same time exit; 1 micro: all off at {c.target_r}R",
        },
        {
            "key": "LIMITS",
            "on": True,
            "rule": f"{c.max_attempts_per_setup} attempts per setup (E1), {c.max_trades_per_day} "
            f"trades a day (E2){', a winner ends the day (E3)' if c.stop_after_win else ''}",
        },
        {"key": "SIZE", "on": True, "rule": _gala_fit(r)},
        {"key": "ACCOUNTS", "on": c.one_account_per_trade, "rule": "one free account per trade, never copy trading"},
    ]


def conti_vwap_rules(r: Any) -> list[dict[str, object]]:
    """CONTI VWAP card (docs/CONTI_RULES.md part C; * = not from the video)."""
    c = r.strategy.conti_vwap_cfg
    return [
        {
            "key": "VWAP",
            "on": True,
            "rule": "anchored at 09:30 ET, volume-weighted (high + low + close) / 3 (C1), 1-minute bars (C2)",
        },
        {
            "key": "ENTRY",
            "on": True,
            "rule": "1-minute close above VWAP → LONG, below → SHORT (C3/C4); "
            "after an exit the next close on the other side (a reversal waits until flat)*",
        },
        {"key": "EXIT", "on": True, "rule": f"a 1-minute close back through VWAP (C5); flat at {c.window_end}*"},
        {"key": "EMERGENCY STOP", "on": True, "rule": f"{c.emergency_stop_pts} pt broker stop* (the video has none)"},
        {"key": "SIZE", "on": True, "rule": fit_size_row(r, c, c.max_losses_per_day, ("25", "25"))},
        {"key": "ACCOUNTS", "on": c.one_account_per_trade, "rule": "one free account per trade, never copy trading"},
    ]


def okala_rules(r: Any) -> list[dict[str, object]]:
    """OKALA 8020 card (docs/OKALA_8020_RULES.md; * = not from the video)."""
    c = r.strategy.okala_8020_cfg
    return [
        {"key": "LEVELS", "on": True, "rule": "NASDAQ prices ending in 20 / 80; either way, on the reaction (A1–A4)"},
        {
            "key": "CHARTS",
            "on": True,
            "rule": f"{c.structure_minutes}-min structure; entries on {c.entry_minutes}-min "
            "bars* (the video's 200-second chart cannot be built from 1-minute data)",
        },
        {
            "key": "SETUPS",
            "on": True,
            "rule": f"{', '.join(c.setups)}: fork / reverse fork (D1/D2), cross-section with "
            "H-pattern confluence (D3/D4), level reaction (A3); repair candles = magnets / runner target (D5)",
        },
        {"key": "WINDOW", "on": True, "rule": f"{', '.join(c.windows)} ET*, lunch excluded (B3)"},
        {
            "key": "STOP / TP",
            "on": True,
            "rule": f"stop {c.stop_pts} pt always (C1); TP1 {c.tp1_pts} pt (C2), then "
            f"stop to break even +{c.be_cover_pts} pt (C3); runner to the magnet or {c.runner_target_pts} pt* (C4); "
            "1 micro → TP1 only, 2+ → about half at TP1 (C5 approximated)",
        },
        {
            "key": "ADDS",
            "on": c.add_after_tp1 and c.max_adds > 0,
            "rule": f"D145: up to {c.max_adds}* same-direction "
            "adds once the stop is at break even; the whole position stays inside one trade's risk cap",
        },
        {"key": "LOSSES", "on": True, "rule": f"no trade cap; {c.max_losses_per_day} losses a day* (Lucid sizing)"},
        {"key": "SIZE", "on": True, "rule": fit_size_row(r, c, c.max_losses_per_day, ("10", "10"))},
        {"key": "ACCOUNTS", "on": c.one_account_per_trade, "rule": "one free account per new trade; adds stay on it"},
    ]


def bruni_rules(r: Any) -> list[dict[str, object]]:
    """BRUNI STRUCTURE card (docs/BRUNI_RULES.md; * = not from the video)."""
    c = r.strategy.bruni_structure_cfg
    gap = "OFF until measured in-sample" if c.wick_gap_min_pts is None else f"skip below {c.wick_gap_min_pts} pt"
    return [
        {
            "key": "STRUCTURE",
            "on": True,
            "rule": f"{c.tf_minutes}-min only (A1); breakout = body close beyond the last "
            f"swing by ≥ {c.breakout_min_ticks}* ticks (A2); last two breakouts = actual + peripheral (A3–A5)",
        },
        {"key": "POTENTIAL", "on": True, "rule": f"{c.potential}: 75% of the leg (A6) or the value-area limit (A7)"},
        {
            "key": "ZONE",
            "on": True,
            "rule": "triple print: the latest 3 valid opposite candles before the impulse (B1–B5)",
        },
        {
            "key": "ENTRY",
            "on": True,
            "rule": f"[GAP]* price back in the zone → entry, stop {c.stop_buffer_ticks}* ticks "
            "past it (the video never shows the trigger); New York session only (no Asian range, no overnight)",
        },
        {"key": "WICK GAP", "on": c.wick_gap_min_pts is not None, "rule": f"two wicks nearest the stop (C1–C5): {gap}"},
        {"key": "TARGET", "on": True, "rule": f"fixed {c.target_r}R (E1/E2, never above 3R)"},
        {
            "key": "AUTOCORRELATION",
            "on": c.autocorr_sizing,
            "rule": "F2/F3: smaller after a loss (positive) or a win "
            "(negative), from stored in-sample win rates; never larger",
        },
        {
            "key": "REGIME FLIP",
            "on": c.regime_flip,
            "rule": "F6: flip the side only in a bucket the in-sample table marks FLIP",
        },
        {"key": "DRAWDOWN SHIELD", "on": c.drawdown_shield, "rule": "F5: one active account per week"},
        {
            "key": "SIZE",
            "on": True,
            "rule": "fixed risk, no Kelly on prop accounts (F4), no VAM (F7); "
            + fit_size_row(r, c, c.max_losses_per_day, ("20", "40")),
        },
    ]


def candace_rules(r: Any) -> list[dict[str, object]]:
    """CANDACE ICT SCALP card (docs/CANDACE_ICT_RULES.md; * = not from the video)."""
    c = r.strategy.candace_ict_cfg
    return [
        {
            "key": "SESSIONS",
            "on": True,
            "rule": f"New York {c.ny_window}* ET (B2); London {c.london_window} "
            f"{'on' if c.london else 'OFF — cannot be tested here (RTH-only history)'} (B1)",
        },
        {
            "key": "POOLS",
            "on": True,
            "rule": "equal highs / lows, swings, previous day and session high / low, "
            "1-hour FVG (A1/A3); a sweep = beyond a pool and a close back inside (A4)",
        },
        {
            "key": "IFVG",
            "on": True,
            "rule": f"a body closes through the run's FVG with displacement ≥ "
            f"{c.displacement_mult}* × the {c.displacement_bars}-bar avg body (C1/C2/C5); entry on the retrace (C3)",
        },
        {
            "key": "PREMIUM / DISCOUNT",
            "on": True,
            "rule": f"shorts above, longs below {c.premium_pct * 100:.0f}%* (A2)",
        },
        {
            "key": "STOP",
            "on": True,
            "rule": f"beyond the swept extreme; max NY {c.ny_max_stop_pts} / London "
            f"{c.london_max_stop_pts} pt, else skip (D1/D2)",
        },
        {
            "key": "TARGET",
            "on": True,
            "rule": f"≥ 1:{c.min_rr}, moved to the nearest pool beyond (D3); max hold "
            f"{c.ny_max_hold_minutes} min NY. Partial + break even (D4/D5) NOT built — single bracket",
        },
        {
            "key": "GRADE",
            "on": True,
            "rule": f"A+ ≥ {c.grade_a_min}* confluences, B {c.grade_b_min}*, else C → "
            "full / half / quarter of the Lucid-fit size (E3, tighten-only)",
        },
        {"key": "NOT TESTABLE", "on": False, "rule": "15 / 30-second charts, Asia range, midnight price, SMT with ES"},
        {"key": "SIZE", "on": True, "rule": fit_size_row(r, c, c.max_losses_per_day, ("20", "40"))},
    ]


def auction_rules(r: Any) -> list[dict[str, object]]:
    """ORDER FLOW · AUCTION (IMRE) card (docs/IMRE_AMT_RULES.md; * = not from the video)."""
    c = r.strategy.order_flow_cfg.auction
    return [
        {
            "key": "REGIME",
            "on": True,
            "rule": "daily one-time-framing (strict HH + HL + HC up, LH + LL + LC down) = "
            "IMBALANCE, else BALANCE (A2/A3); weekly shown as context",
        },
        {
            "key": "VALUE",
            "on": True,
            "rule": f"prior cash-session profile: POC, {c.value_area_pct * 100:.0f}% value "
            "area, low-volume nodes (B1/B5); where today opened vs that value (B7)",
        },
        {
            "key": "DELTA",
            "on": True,
            "rule": f"ESTIMATED from 1-minute bars (no footprint delta stored); big bubble = "
            f"|delta| ≥ {c.bubble_mult}* × the {c.bubble_bars}*-bar average (C5). DOM / heatmap NOT available (C4)",
        },
        {
            "key": "FAILED AUCTION",
            "on": True,
            "rule": "BALANCE only: V-shape reclaim of VAL / VAH + big bubble, or "
            "the slower micro-range flavour plan A / B (D1–D8); target POC, then the opposite value extreme",
        },
        {
            "key": "BREAKOUT",
            "on": True,
            "rule": f"IMBALANCE only, with the trend: never the first break; micro range "
            f"({c.micro_bars}* bars ≤ {c.micro_max_pts}* pt) beyond value, plan A reclaim / plan B break of its VAH "
            f"(E1–E5), risk split {c.risk_share_a}/{1 - c.risk_share_a}, target {c.breakout_target_r}R*",
        },
        {
            "key": "STOP / TARGET",
            "on": True,
            "rule": f"{c.stop_buffer_ticks}* ticks beyond the absorbing side; ≥ 1:"
            f"{c.min_rr}* to the first target; 2+ micros: about half off there and the stop to entry (F1)",
        },
        {
            "key": "WINDOW",
            "on": True,
            "rule": f"{c.window}* ET, never before 09:30 (F4); max {c.max_trades_per_day}* "
            "trades a day; news = the Lucid blackout (F5)",
        },
        {"key": "SIZE", "on": True, "rule": fit_size_row(r, c, c.max_trades_per_day, ("8", "16"))},
    ]


def mgc_nc_rules(r: Any) -> list[dict[str, object]]:
    """D165 NOISE + CANDACE · MGC card: the same engines as the MNQ cards on MGC, with the 30-day picks."""
    m = r.strategy.mgc_noise_candace_cfg
    n, c = m.noise, m.candace
    return [
        {
            "key": "NOISE",
            "on": True,
            "rule": f"noise-area momentum on MGC RTH (same engine as MNQ): hourly checks, "
            f"${n.emergency_stop_usd} emergency stop, no profit lock, no weekday skip, flat {n.flat_at} ET; "
            f"needs {n.min_history_days} stored MGC sessions",
        },
        {
            "key": "CANDACE",
            "on": True,
            "rule": f"ICT sweep + IFVG retrace (same engine as MNQ): window {c.ny_window} ET, "
            f"stop cap {c.ny_max_stop_pts} pt, hold {c.ny_max_hold_minutes} min, min {c.min_rr}R",
        },
        {
            "key": "SIZE",
            "on": True,
            "rule": f"fixed {m.contracts} micro; METALS group (no equity hedge lock); "
            "one position per account; DLL / MLL / consistency / news checks only shrink or skip",
        },
        {
            "key": "DATA",
            "on": True,
            "rule": "MGC 1-minute bars from the existing live feed (TradingView heartbeats); "
            "the 30-day test used Yahoo continuous contracts, not MGC.v.0",
        },
    ]


RULE_CARDS: dict[str, Any] = {
    "mgc_noise_candace": mgc_nc_rules,
    "order_flow_auction": auction_rules,
    "candace_ict": candace_rules,
    "bruni_structure": bruni_rules,
    "conti_orb": conti_orb_rules,
    "conti_vwap": conti_vwap_rules,
    "okala_8020": okala_rules,
}


def _order_flow_markets(c: dict[str, object], r: Any) -> dict[str, object]:
    """D96: the Order Flow card lists the markets it trades (plan file strategy.order_flow_cfg.instruments)."""
    if c["key"] not in ("order_flow", "order_flow_amt", "order_flow_zone"):
        return {}
    from app.api.orderflow import amt_rules, ar_rules, zone_rules

    cfg = r.strategy.order_flow_cfg
    return {
        "instruments": list(cfg.instruments),
        "paper_only": cfg.paper_only,
        "flat_at": cfg.flat_at,
        "ar_layers": ar_rules(r)["layers"],  # D101: ENVIRONMENT → LOCATION → PATH → CONFIRMATION
        "amt_layers": amt_rules(r.strategy.order_flow_cfg.amt),  # D110: AMT+ context / location / target
        "zone_layers": zone_rules(r.strategy.order_flow_cfg.zone_atr),  # D111: ATR-zone type
    }


def _ar_side_by_side(db: Session, r: Any, sess: Any) -> dict[str, Any]:
    """D160: the Order Flow card's AR-beside-NOISE option: toggle, the pre-session TradingAgents runs and their latest
    bias / probabilities (or NO_CALL), the data-source label and the evidence line. No pass / win figures."""
    from app.bias import ar_pre_session as arp

    return {
        "setting": "strategy.order_flow_cfg.ar_side_by_side",
        "enabled": r.strategy.order_flow_cfg.ar_side_by_side,
        "data_source": arp.SOURCE,
        "evidence": arp.EVIDENCE,
        "verified": False,
        "advisor_mode": r.strategy.advisor.mode,
        "session": sess.isoformat(),
        "runs": arp.view(db, r, sess),
    }


def _fast_pass_weekly(plan_stem: str) -> dict[str, Any] | None:
    """D164: weekly profit targets for a fast-pass card. Figures come from config/eval_odds.yaml (fast_pass_weekly), the
    eval target from the plan yaml. weekly_needed = target / (median_days / 5); sim_weekly = 5-year profit / 260."""
    from app.config import load_yaml_decimal
    from app.eval_odds import weekly_row

    got = weekly_row(plan_stem)
    path = Path(__file__).resolve().parents[3] / "config" / "rules" / f"{plan_stem}.yaml"
    try:
        target = Decimal(str(load_yaml_decimal(path.read_text(encoding="utf-8"))["eval"]["profit_target"]))
    except (OSError, KeyError, TypeError, ArithmeticError):
        return None
    if got is None:
        return None
    row, source = got
    needed = money(target / (row.median_days / Decimal(5)))
    sim = money(row.sim_profit_5y / Decimal(260))
    return {
        "target": str(target),
        "median_days": str(row.median_days),
        "needed_week": str(needed),
        "sim_week": str(sim),
        "measured": row.measured,
        "source": source,
    }


@router.get("/strategies")
def strategies(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    """D55: strategy buttons — on/off (My Settings keys strategy.*), tested results next to each, NOISE warm-up
    progress and the AI calibration ledger (advisory until proven)."""
    from app.bias.ledger import duo_decisions, status
    from app.engine.strategy_catalog import CATALOG
    from app.eval_odds import odds_view, table_for
    from app.signals.strategy_service import load_days

    st = request.app.state
    r, now = st.rules.rules, st.clock.now()
    plan, eod = st.rules.plan, r.strategy.eod_closed_balance
    sess = session_date(now)
    # D137: eval pass / bust of the NOISE card (active size table) and the MAIN card (NOISE + fade, regular table)
    card_odds = {
        "noise": odds_view(plan, table_for(r.strategy.high_risk, _suggested_on(r)), eod),
        "pm_fade": odds_view(plan, "regular_fade_on", eod),
    }
    on = {
        "noise": r.strategy.noise,
        "ai_bias": r.strategy.ai_bias,
        "ai_duo": r.strategy.ai_duo,
        "order_flow": r.strategy.order_flow,
        "order_flow_amt": r.strategy.order_flow and r.strategy.order_flow_cfg.amt.enabled,  # D110
        "order_flow_zone": r.strategy.order_flow and r.strategy.order_flow_cfg.zone_atr.enabled,  # D111
        "pm_fade": r.strategy.noise and r.strategy.pm_fade,  # D58 MAIN card = NOISE + fade both on
        "jj_fpt": r.strategy.jj_fpt,
        "gala_pa": r.strategy.gala_pa,
        "conti_orb": r.strategy.conti_orb,
        "conti_vwap": r.strategy.conti_vwap,
        "okala_8020": r.strategy.okala_8020,
        "bruni_structure": r.strategy.bruni_structure,
        "candace_ict": r.strategy.candace_ict,
        "mgc_noise_candace": r.strategy.mgc_noise_candace,  # D165
        "order_flow_auction": r.strategy.order_flow and r.strategy.order_flow_cfg.auction.enabled,  # D150
        "noise_ai_split": split_active(r.strategy.noise_ai_split, r.strategy.noise, r.strategy.ai_duo),  # D92
    }
    nc = r.strategy.noise_cfg
    stored = [
        d for d in load_days(db, nc.symbol, now) if len(d.bars) >= nc.min_bars_per_day and d.day < sess.isoformat()
    ]
    ledgers = []
    for sym, i in r.instruments.items():
        if i.enabled:
            ledgers.append({**status(db, i.bias_proxy, sym, sess, float(r.strategy.ai_gate_min_accuracy)), "rows": []})
    return {
        "strategies": [
            {
                **c,
                **_card_odds(str(c["key"]), card_odds),
                "enabled": on[str(c["key"])],
                "setting": str(c.get("setting_key") or f"strategy.{c['key']}"),
                **_order_flow_markets(c, r),
                **({"ar_side_by_side": _ar_side_by_side(db, r, sess)} if c["key"] == "order_flow" else {}),
                **({"jj_rules": jj_rules(r)} if c["key"] == "jj_fpt" else {}),
                **({"gala_rules": gala_rules(r)} if c["key"] == "gala_pa" else {}),
                **({"strategy_rules": RULE_CARDS[str(c["key"])](r)} if c["key"] in RULE_CARDS else {}),
            }
            for c in CATALOG
        ],
        "noise_warmup": {
            "sessions": len(stored),
            "needed": nc.min_history_days,
            "ready": len(stored) >= nc.min_history_days,
        },
        "ai_ledger": ledgers,
        "presets": _presets(r, plan),
        "ta_mgc": _ta_mgc(db, r, sess),
        "ai_duo_log": duo_decisions(db, r.strategy.ai_duo_cfg.markets),
        "markets": {sym: i.enabled for sym, i in r.instruments.items()},
        "size_profiles": {  # D64: Regular / High risk buttons (each account sized by its own size + drawdown brake)
            "active": "high" if r.strategy.high_risk else "regular",
            "setting": "strategy.high_risk",
            "regular": [_tier(t) for t in r.strategy.size_table],
            "high": [_tier(t) for t in r.strategy.size_table_high],
            "suggested": [_tier(t) for t in r.strategy.size_table_suggested],  # D127
            "suggested_on": bool(r.strategy.suggested_size and r.strategy.size_table_suggested),
            "suggested_setting": "strategy.suggested_size",
            # D137: pass / bust text per table for the active plan + current EOD toggle (config/eval_odds.yaml)
            "odds": {t: odds_view(plan, t, eod) for t in ("regular", "high", "suggested", "regular_fade_on")},
            # D66 / D69 — EVAL accounts, Evaluation Mode on; D133: shown as traded (capped while eval_size_s19 is on)
            "eval_regular": [_tier(t) for t in _eval_rows(r, r.strategy.size_table_eval)],
            "eval_high": [_tier(t) for t in _eval_rows(r, r.strategy.size_table_eval_high)],
        },
        "toggles": _session20_toggles(r, plan),
        "advisor": advisor_view(db, r, sess),
    }


ADVISOR_CARDS = {
    "jj_fpt": "JJ_FPT",
    "gala_pa": "GALA_PA",
    "conti_orb": "CONTI_ORB",
    "conti_vwap": "CONTI_VWAP",
    "okala_8020": "OKALA_8020",
    "bruni_structure": "BRUNI_STRUCTURE",
    "candace_ict": "CANDACE_ICT",
    "order_flow_auction": "ORDER_FLOW_AUCTION",
}


def advisor_view(db: Session, r: Any, sess: Any) -> dict[str, Any]:
    """D151: advisor mode + today's stored TradingAgents call per strategy market + each card's latest verdict today.
    DB reads only (no network). `connected` = a TradingAgents key is stored (same check as /api/strategy)."""
    from app.bias import ledger as L
    from app.bias.policy import Policy, combine
    from app.models import ApiCredential, TradePlanRow

    cfg = r.strategy.advisor
    connected = (
        db.execute(select(ApiCredential).where(ApiCredential.provider == "tradingagents")).scalar_one_or_none()
        is not None
    )
    cards: dict[str, Any] = {}
    day0 = datetime.combine(sess, datetime.min.time(), tzinfo=ET)
    for key, mode in ADVISOR_CARDS.items():
        sym = _advised_symbol(r, key)
        proxy = r.instrument(sym).bias_proxy
        rows = list(
            db.execute(
                select(BiasDecision).where(BiasDecision.proxy == proxy, BiasDecision.session_date == sess)
            ).scalars()
        )
        label = rows[-1].raw_rating if rows else None
        call = combine(*L.parse_label(label), Policy(bias_matters=True)) if label else None
        last = db.execute(
            select(Signal.features)
            .join(TradePlanRow, TradePlanRow.signal_id == Signal.id)
            .where(TradePlanRow.mode == mode, Signal.bar_time >= day0)
            .order_by(Signal.id.desc())
            .limit(1)
        ).first()
        adv = (last[0] or {}).get("advisor") if last else None
        cards[key] = {
            "mode": mode,
            "symbol": sym,
            "skipped": mode in cfg.skip_strategies,
            "call_label": label,
            "call_direction": None if call is None else call.direction,
            "prob_up": None if call is None else call.prob_up,
            "last_verdict": None if adv is None else adv.get("verdict"),
        }
    st = L.status(db, r.instrument(r.strategy.gala_pa_cfg.symbol).bias_proxy, r.strategy.gala_pa_cfg.symbol, sess,
                  float(r.strategy.ai_gate_min_accuracy))  # fmt: skip
    return {
        "mode": cfg.mode,
        "setting": "strategy.advisor.mode",
        "skip_strategies": list(cfg.skip_strategies),
        "connected": connected,
        "ledger_proven": st["state"] == "PROVEN",
        "required_accuracy": float(r.strategy.ai_gate_min_accuracy),
        "cards": cards,
    }


def _advised_symbol(r: Any, key: str) -> str:
    if key == "order_flow_auction":
        return str(r.strategy.order_flow_cfg.auction.symbol)
    return str(getattr(r.strategy, f"{key}_cfg").symbol)


def _suggested_on(r: Any) -> bool:
    return bool(r.strategy.suggested_size and r.strategy.size_table_suggested)


def _card_odds(key: str, card_odds: dict[str, Any]) -> dict[str, Any]:
    """D137: the strategy card's eval odds (None fields for cards without a measured study)."""
    o = card_odds.get(key)
    if o is None:
        return {}
    return {"pro25k_pass_pct": o["pass_pct"], "pro25k_bust_pct": o["bust_pct"], "eval_odds": o}


def _eval_rows(r: Any, table: list[Any]) -> list[Any]:
    from app.config import capped_eval_table

    return capped_eval_table(table, r.strategy.eval_size_caps) if r.strategy.eval_size_s19 else table


def _session20_toggles(r: Any, plan: str = "") -> list[dict[str, Any]]:
    """D132 / D133: two-way Strategy-page toggles (My Settings keys; each save is validated, versioned, audited)."""
    from app.eval_odds import drawdown_compare, odds_view

    st, nc = r.strategy, r.strategy.noise_cfg
    eod = st.eod_closed_balance
    ov = {t: odds_view(plan, t, eod)["text"] for t in ("regular", "high", "regular_fade_on")}
    caps = ", ".join(f"{int(c.account_size) // 1000}K ≤ {c.max_contracts}" for c in st.eval_size_caps)
    out: list[dict[str, Any]] = [
        {
            "key": "fade_eval_off",
            "setting": "strategy.pm_fade_cfg.eval_off",
            "title": "Afternoon fade during evaluations",
            "value": st.pm_fade_cfg.eval_off,
            "on_label": "Off on EVAL accounts (default — better pass/bust)",
            "off_label": "On everywhere",
            "note": f"EVAL stage only; funded accounts keep the fade. This plan, fade off: {ov['regular']}. "
            f"Fade on: {ov['regular_fade_on']}.",
        }
    ]
    out.append(
        {
            "key": "eod_closed_balance",
            "setting": "strategy.eod_closed_balance",
            "title": "EOD drawdown: open losses don't stop the account",
            "value": st.eod_closed_balance,
            "on_label": "EOD accounts: kill switch watches the closed balance only",
            "off_label": "Kill switch watches balance + open P&L (default, safest)",
            "note": "Only for accounts whose drawdown is EOD; intraday accounts are unchanged. The $250 broker stop, "
            "daily loss limit and the pre-trade room check still apply. Lucid rules (user, 2026-11-13): on EOD "
            "accounts (Pro and Flex eval + funded) an open loss touching the floor does not breach by itself; "
            "the balance measured at the session end does. LucidDaily funded is intraday, so this toggle never "
            "applies to it. Measured: this setting changes 0 points on every plan (session 21 + 22).",
            "compare": drawdown_compare(plan),  # session 22: EOD vs intraday trailing drawdown (config/eval_odds.yaml)
        }
    )
    if nc.profit_lock_trigger_alt_pts is not None and nc.profit_lock_trigger_pts is not None:
        out.append(
            {
                "key": "noise_lock_alt",
                "setting": "strategy.noise_lock_alt",
                "title": "NOISE profit-lock trigger",
                "value": st.noise_lock_alt,
                "on_label": f"{nc.profit_lock_trigger_alt_pts.normalize():f} pt — experimental, likely chance",
                "off_label": f"{nc.profit_lock_trigger_pts.normalize():f} pt (default, session-19 preset C)",
                "note": f"Stop moves to entry +{(nc.profit_lock_pts or 0):f} pt once the trade is that far in profit "
                "(same lock distance either way). 80 pt: last 12 months PF 1.89, but no gain "
                "in-sample — treat as chance until paper proves it.",
            }
        )
    for fk, fp, fon in (
        ("fast_pass_25k", st.fast_pass_25k_cfg, st.fast_pass_25k),
        ("fast_pass_50k", st.fast_pass_50k_cfg, st.fast_pass_50k),
        ("fast_pass_100k", st.fast_pass_100k_cfg, st.fast_pass_100k),
        ("fast_pass_150k", st.fast_pass_150k_cfg, st.fast_pass_150k),
    ):
        if fp is None:  # D156/D157: only plan files that carry the cfg show the card
            continue
        op = "≤" if fp.brake_inclusive else "<"

        def steps_text(steps: Any, op: str = op) -> str:
            return ", ".join(f"{op} ${x.cushion_usd:,.0f}: {x.contracts}" for x in steps) or "no brake"

        late = None
        if fp.late_contracts is not None:  # D166: the 3rd-edge option lives INSIDE the card (one global switch)
            late = {
                "setting": "strategy.fast_pass_late_day",
                "value": st.fast_pass_late_day,
                "label": "3rd edge: late-day momentum (UNVERIFIED, held-out PF 1.10)",
                "detail": f"MNQ, follows the 09:30-13:30 trend at 15:00, {st.late_day_cfg.stop_pts:g} pt stop, flat "
                f"{st.late_day_cfg.flat_at}: {fp.late_contracts} micro(s) (cushion {steps_text(fp.late_steps)}). "
                "Only while this plan's fast pass is ON; EVAL, own size; one position per account; hedge lock and "
                "every Lucid check still shrink or skip. Study: docs/results/new_edge/late_leg_sizes/RESULTS.md.",
            }
        out.append(
            {
                "late": late,
                "weekly": _fast_pass_weekly(f"lucid_pro_{int(fp.account_size) // 1000}k"),
                "key": fk,
                "setting": f"strategy.{fk}",
                "title": f"{int(fp.account_size) // 1000}K fast pass (evaluations)",
                "value": fon,
                "on_label": f"NOISE {fp.noise_contracts} @ ${fp.noise_stop_usd:,.0f} stop "
                f"(cushion {steps_text(fp.noise_steps)}"
                + (
                    f"; +1 per ${fp.noise_grow_per:,.0f} of cushion, max {fp.noise_max_contracts}"
                    if fp.noise_grow_per
                    else ""
                )
                + f") · CANDACE {fp.candace_contracts or 'off'} (cushion {steps_text(fp.candace_steps)}"
                + (
                    f"; +1 per ${fp.candace_grow_per:,.0f} of cushion, max {fp.candace_max_contracts}"
                    if fp.candace_grow_per
                    else ""
                )
                + ")"
                + (f" · day lock {fp.day_lock_pct:g} of the remaining target" if fp.day_lock_pct else "")
                + (f" · NOISE lock {fp.noise_lock_trigger_pts:g} pt" if fp.noise_lock_trigger_pts else ""),
                "off_label": "Normal evaluation sizes (default)",
                "note": f"EVAL stage, {int(fp.account_size) // 1000}K accounts only. Every Lucid check (DLL, MLL room, "
                "consistency, hedge lock, news/flat) still shrinks or skips. "
                "Numbers and pass figures: docs/results/pass_fastest/ (smaller_plans/, beat109/RESULTS.md, passfloor/ "
                "RESULTS.md, pass70/RESULTS.md; not repeated here).",
            }
        )
    if st.eval_size_caps:
        out.append(
            {
                "key": "eval_size_s19",
                "setting": "strategy.eval_size_s19",
                "title": "Evaluation-Mode size (100K / 150K)",
                "value": st.eval_size_s19,
                "on_label": f"Session 19 lowest bust ({caps}) — default",
                "off_label": "Previous (150K 4 micros, 100K grows to 4)",
                "note": "EVAL accounts with Evaluation Mode on. This plan, Regular table (the capped sizes): "
                f"{ov['regular']}. High-risk table (grows larger): {ov['high']}.",
            }
        )
    return out
