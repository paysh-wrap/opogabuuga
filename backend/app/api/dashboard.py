"""Dashboard + Today (§18): per-account safety numbers, today's bias, signals and trades. Read-only."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.automation import state as stt
from app.clock import session_date
from app.execution.adapters.base import BrokerError
from app.management.drawdown_guard import GuardCfgView, guard_active
from app.models import Account, Signal, Trade
from app.phases.phase_engine import stage_rules
from app.risk.checks import dll_remaining
from app.risk.eval_mode import eval_mode_effective
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
        cons = stt.consistency(db, a, r)
        eq = bal + opnl
        start = a.starting_balance or Decimal(0)
        row |= {
            "balance": str(bal),
            "open_pnl": str(opnl),
            "mll": _s(a.mll),
            "to_mll": _s(eq - a.mll) if a.mll is not None else None,
            "kill_at": str(r.internal.kill_switch_mll_distance),
            "max_loss": str(stage_rules(r, a.stage, a.drawdown_type, a.dll_enabled).max_loss),
            "dll_limit": _s(dll),
            "today_pnl": str(day.today_pnl),
            "trades_today": day.trades_today,
            "dll_left": _s(dll_remaining(dll, day.today_pnl, day.today_peak_pnl)) if dll is not None else None,
            "consistency_cap": _s(cons.cap) if cons else None,
            "consistency_stop": _s(cons.day_stop) if cons else None,
            "target_left": str(max(start + r.eval.profit_target - bal, Decimal(0))) if a.stage == "EVAL" else None,
            "mll_locked": a.mll_locked,
            "guard_on": guard_active(a.drawdown_type, bool(a.mll_locked), GuardCfgView(r.drawdown_guard.mode)),
            "eval_mode_on": eval_mode_effective(a.stage, a.eval_mode, st.rules.eval_mode_on),
            "day_net_r": str(stt.day_stats(db, a, now).day_net_r),
            "day_lockin_r": str(r.internal.day_lockin_r),
            "day_lockin": stt.day_stats(db, a, now).day_net_r >= r.internal.day_lockin_r,
            "fast_profit_pct": str(_fast_share(db, a, r)),
            "idle_days": (now - (a.last_trade_at or a.stage_started_at or now)).days,
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


GATES = [
    ("G1", "Window, news, feed, halt, cooldown"),
    ("G2", "TradingAgents bias allows this side"),
    ("G3", "LunqFX fractal model valid + C1 range ≥ ATR minimum"),
    ("G4", "BigBeluga MSO structure agrees"),
    ("G5", "MSO CHoCH/BoS after the sweep"),
    ("G6", "No opposing MSO divergence"),
    ("G7", "Valid trade plan (stop + target, R:R 2–3)"),
    ("G8", "Phase, drawdown guard, risk, consistency, hedge lock approve"),
]


def gate_texts(r: Any) -> list[tuple[str, str]]:
    """Gate descriptions from the LOADED plan (never hardcoded rule numbers)."""
    tp, f = r.trade_plan, r.filters
    out = dict(GATES)
    out["G4"] += "" if f.require_mso_agree else " (score only in this plan)"
    out["G5"] += "" if f.require_structure_break else " (score only; no break → closer target)"
    out["G7"] = f"Valid trade plan (stop + target, R:R {tp.rr_min:g}–{tp.rr_max:g})"
    return list(out.items())


@router.get("/strategy")
async def strategy(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    """How the three parts fit together, live: TradingAgents (which side) · LunqFX fractal (where/what) ·
    BigBeluga MSO (when/whether) → gates G1–G8 → risk → orders."""
    from app.models import ApiCredential, SignalGate
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
            active = [m for m in ss.models.values() if m.status not in ("C3_CLOSED", "MODEL_FAILED")]
            feeds.append(
                {
                    "profile": prof,
                    "feed": feed_status(ss.last_heartbeat_ms, tf, now, 2),
                    "mso_trend": (ss.mso or {}).get("trend"),
                    "mso_osc": (ss.mso or {}).get("osc"),
                    "active_models": [{"key": m.model_key, "dir": m.direction, "status": m.status} for m in active],
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
    last = db.execute(select(Signal).order_by(Signal.id.desc()).limit(1)).scalar_one_or_none()
    last_gates = (
        {g.gate: g.passed for g in db.execute(select(SignalGate).where(SignalGate.signal_id == last.id)).scalars()}
        if last
        else {}
    )
    return {
        "tradingagents": {
            "installed_version": ver.data.get("version") if ver and ver.ok else None,
            "pinned_version": st.ta.pinned_version,
            "configured": configured,
            "schedule": r.schedule.bias,
        },
        "indicators": [
            "ICT Fractal Model, HTF Candles, CISD & C2 Targets [LunqFX]",
            "Market Structure Oscillator [BigBeluga]",
        ],
        "instruments": instruments,
        "gates": [
            {"id": g, "text": t, "last": last_gates.get(g)} for g, t in gate_texts(request.app.state.rules.rules)
        ],
        "last_signal": {"id": last.id, "status": last.status, "skip_reason": last.skip_reason} if last else None,
        "one_to_one": r.one_to_one_mode.enabled,
    }


@router.get("/strategies")
def strategies(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    """D55: strategy buttons — on/off (My Settings keys strategy.*), tested results next to each, NOISE warm-up
    progress and the AI calibration ledger (advisory until proven)."""
    from app.bias.ledger import NOISE_MIN_ACC, status
    from app.engine.strategy_catalog import CATALOG
    from app.signals.strategy_service import load_days

    st = request.app.state
    r, now = st.rules.rules, st.clock.now()
    sess = session_date(now)
    on = {
        "noise": r.strategy.noise,
        "lunqfx": r.strategy.lunqfx,
        "open_drive": r.strategy.open_drive,
        "ai_bias": r.strategy.ai_bias,
    }
    nc = r.strategy.noise_cfg
    stored = [
        d for d in load_days(db, nc.symbol, now) if len(d.bars) >= nc.min_bars_per_day and d.day < sess.isoformat()
    ]
    ledgers = []
    for sym, i in r.instruments.items():
        if i.enabled:
            ledgers.append({**status(db, i.bias_proxy, sym, sess, NOISE_MIN_ACC), "rows": []})
    return {
        "strategies": [{**c, "enabled": on[str(c["key"])], "setting": f"strategy.{c['key']}"} for c in CATALOG],
        "noise_warmup": {
            "sessions": len(stored),
            "needed": nc.min_history_days,
            "ready": len(stored) >= nc.min_history_days,
        },
        "ai_ledger": ledgers,
        "markets": {sym: i.enabled for sym, i in r.instruments.items()},
    }
