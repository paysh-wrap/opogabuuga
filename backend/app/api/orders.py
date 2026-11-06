"""Manual order ticket (§19 POST /api/orders/manual).

No bypass: the ticket becomes a MANUAL signal with a §7 TradePlan (same R:R window, tick rounding, min stop) and is
executed through Controller.execute — the exact path automated orders take (account ready/armed/attested, payout
pending, one position, HEDGE_LOCK, pause floor, kill distance, DLL, day stops, consistency cap, sizing, Drawdown
Guard, RR-after-fill, PAPER/LIVE routing + Live-Readiness gate). On top: flatten time, news blackout, enabled market.
Orders are stored with source MANUAL (never disguised as automation and vice versa).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.api.insights import news_blackouts
from app.clock import session_date
from app.engine.trade_plan import Direction, Skip, build_trade_plan
from app.models import Account, Signal, TradePlanRow

router = APIRouter(prefix="/api")


class ManualIn(BaseModel):
    account_id: int
    symbol: str = Field(min_length=1, max_length=16)
    direction: Literal["LONG", "SHORT"]
    stop: Decimal = Field(gt=0)
    take_profit: Decimal = Field(gt=0)


def _refuse(code: int, reason: str) -> HTTPException:
    return HTTPException(code, reason)


@router.post("/orders/manual")
async def manual_order(
    body: ManualIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    st = request.app.state
    c, r, now = st.controller, st.rules.rules, st.clock.now()
    if st.rules.error:
        raise _refuse(409, f"RULES_INVALID: {st.rules.error}")
    inst = r.instruments.get(body.symbol)
    if inst is None or not inst.enabled:
        raise _refuse(422, f"MARKET_DISABLED: {body.symbol}")
    if db.get(Account, body.account_id) is None:
        raise _refuse(404, "no such account")
    if c.entries_blocked_by_time():
        raise _refuse(409, "FLATTEN_TIME: entries are blocked after the flatten time")
    events = st.calendar(session_date(now))
    if events is None:
        raise _refuse(409, "NO_CALENDAR: economic calendar not loaded (no data = no trading)")
    for b in news_blackouts(r, events):
        if datetime.fromisoformat(b["no_entry_from"]) <= now <= datetime.fromisoformat(b["no_entry_until"]):
            raise _refuse(409, f"NEWS_BLACKOUT: {b['title']}")
    entry = c.adapter.sim.last.get(body.symbol)
    if entry is None:
        raise _refuse(409, "NO_PRICE: no live price for this market yet")
    tp = r.trade_plan
    buffer = inst.stop_buffer_ticks or tp.stop_buffer_ticks
    plan = build_trade_plan(
        Direction(body.direction),
        entry,
        body.stop,
        body.take_profit,
        inst.tick,
        0,  # the user's stop is the stop (tick-rounded away from entry); no extra buffer
        inst.min_stop_ticks or tp.min_stop_ticks,
        tp.rr_min,
        tp.rr_max,
    )
    if isinstance(plan, Skip):
        audit.record(
            db, st.clock, p.user.username, "order.manual.rejected", str(body.account_id), {"reason": plan.reason}
        )
        db.commit()
        raise _refuse(422, f"{plan.reason}{': ' + plan.detail if plan.detail else ''}")
    sig = Signal(
        status="PASS",
        passed=True,
        symbol=body.symbol,
        profile="MANUAL",
        direction=body.direction,
        model_key=f"MANUAL-{body.symbol}-{body.account_id}-{int(now.timestamp() * 1000)}-{uuid4().hex[:8]}",
        bar_time=now,
        entry_bar_time=now,
        updated_at=now,
        score=r.score.min_score,  # sizing only: the lowest tier (floor), never a higher one
        # post-fill rebuild re-derives stop = invalid - sign*buffer -> store the level that maps back to this stop
        features={
            "manual": True,
            "invalid": str(plan.stop + plan.direction.sign * buffer * inst.tick),
            "t2": str(plan.take_profit),
            "rr_max": str(tp.rr_max),
        },
    )
    db.add(sig)
    db.flush()
    db.add(
        TradePlanRow(
            signal_id=sig.id,
            mode="STANDARD",
            direction=plan.direction.value,
            entry=plan.entry,
            stop=plan.stop,
            take_profit=plan.take_profit,
            risk_pts=plan.risk_pts,
            rr=plan.rr,
        )
    )
    audit.record(
        db,
        st.clock,
        p.user.username,
        "order.manual",
        str(body.account_id),
        {
            "signal": sig.id,
            "symbol": body.symbol,
            "direction": body.direction,
            "stop": str(plan.stop),
            "tp": str(plan.take_profit),
            "entry": str(entry),
        },
    )
    db.commit()
    res = await c.execute(sig.id, p.user.username, [body.account_id])
    out = res[0] if res else None
    if out is None:  # account not selected/armed (selector skipped it) → explicit refusal
        out_d: dict[str, Any] = {"account_id": body.account_id, "ok": False, "reason": "ACCOUNT_NOT_READY"}
    else:
        out_d = out.__dict__
    c.publish("order.updated", {"signal": sig.id, "manual": True})
    if out_d["ok"]:
        c.publish("position.updated", {"account": body.account_id})
    return {
        "signal_id": sig.id,
        "plan": {
            "entry": str(plan.entry),
            "stop": str(plan.stop),
            "take_profit": str(plan.take_profit),
            "rr": str(plan.rr),
        },
        "result": out_d,
    }
