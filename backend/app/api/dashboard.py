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
from app.models import Account, Signal, Trade
from app.risk.checks import dll_remaining
from app.signals.service import today_bias

router = APIRouter(prefix="/api")


def _s(x: Decimal | None) -> str | None:
    return None if x is None else str(x)


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
            "today_pnl": str(day.today_pnl),
            "trades_today": day.trades_today,
            "dll_left": _s(dll_remaining(dll, day.today_pnl, day.today_peak_pnl)) if dll is not None else None,
            "consistency_cap": _s(cons.cap) if cons else None,
            "consistency_stop": _s(cons.day_stop) if cons else None,
            "target_left": str(max(start + r.eval.profit_target - bal, Decimal(0))) if a.stage == "EVAL" else None,
            "mll_locked": a.mll_locked,
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
