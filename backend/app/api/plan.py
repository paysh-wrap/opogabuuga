"""Payouts & Plan (§14/§18/§19): payout settings, plan tracker + 12-month projection, eval pace per account.

Everything here is computed from real rows (processed payouts, trades, daily stats) and the loaded rules — no
assumptions are presented as results; the projection is the trailing 90-day payout rate carried forward.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.api.insights import eval_pace
from app.automation import state as stt
from app.clock import ET, to_et
from app.execution.adapters.base import BrokerError
from app.models import Account, DailyAccountStats, Payout
from app.payouts.service import plan_for

router = APIRouter(prefix="/api")
CENT = Decimal("0.01")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------- eval pace ----------
@router.get("/accounts/{acct_id}/eval-pace")
def account_eval_pace(
    acct_id: int, request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    r = request.app.state.rules.rules
    a = db.get(Account, acct_id)
    if a is None:
        raise HTTPException(404, "no such account")
    if a.stage != "EVAL":
        raise HTTPException(409, f"eval pace applies to EVAL accounts only (this one is {a.stage})")
    out = eval_pace(db, a, r)
    q = select(DailyAccountStats.day_profit).where(DailyAccountStats.account_id == a.id)
    if a.stage_started_at is not None:
        from app.clock import session_date

        q = q.where(DailyAccountStats.session_date >= session_date(a.stage_started_at))
    largest = max((d for d in db.execute(q).scalars()), default=Decimal(0))
    cons = stt.consistency(db, a, r)
    profit = Decimal(out["profit"])
    out |= {
        "target_left": str(max(r.eval.profit_target - profit, Decimal(0))),
        "largest_day": str(largest),
        "consistency_cap": str(cons.cap) if cons else None,
        "consistency_day_stop": str(cons.day_stop) if cons else None,
        "consistency_headroom": str(max(cons.cap - max(largest, Decimal(0)), Decimal(0))) if cons else None,
        "consistency_pct": str(r.eval.consistency_max_day_pct) if r.eval.consistency_max_day_pct else None,
    }
    return out


# ---------- payout settings ----------
class PayoutSettingsIn(BaseModel):
    skim_mode: Literal["half", "off"]  # off = sweep only
    frequency: Literal["weekly", "on_demand", "every_n_sessions"]
    mode: Literal["sweep_skim", "max_eligible"] | None = None  # D65; None = keep the plan's
    min_sessions_between: int | None = Field(None, ge=1, le=20)
    min_pct_of_cap: Decimal | None = Field(None, gt=0, le=1)  # D65: None = request as soon as eligible


def _settings(request: Request) -> dict[str, Any]:
    pc = request.app.state.rules.rules.payouts
    return {
        "skim_mode": pc.skim_mode,
        "frequency": pc.frequency,
        "check_time": pc.check_time,
        "sweep_above": str(pc.sweep_above),
        "buffer": str(request.app.state.rules.rules.funded.payout.buffer),
        "mode": pc.mode,
        "min_sessions_between": pc.min_sessions_between,
        "session_check_time": pc.session_check_time,
        "min_pct_of_cap": None if pc.min_pct_of_cap is None else str(pc.min_pct_of_cap),
    }


@router.get("/payouts/settings")
def get_payout_settings(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    return _settings(request)


@router.put("/payouts/settings")
async def put_payout_settings(
    body: PayoutSettingsIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    st = request.app.state
    before = {"skim_mode": st.rules.rules.payouts.skim_mode, "frequency": st.rules.rules.payouts.frequency}
    after = body.model_dump(mode="json", exclude_none=True)
    if body.min_pct_of_cap is None:
        after["min_pct_of_cap"] = None  # explicit "as soon as eligible"
    stt.set_setting(db, "payouts.settings", after, st.clock.now())
    audit.record(db, st.clock, p.user.username, "payouts.settings", "", {"before": before, "after": after})
    db.commit()
    st.rules.refresh(db)
    st.bus.publish("risk.settings_changed", {"payouts": after})
    return _settings(request)


# ---------- plan ----------
def next_check(now: datetime, check_time: str) -> datetime:
    day, hm = check_time.split()
    h, m = (int(x) for x in hm.split(":"))
    local = to_et(now)
    ahead = (DAYS.index(day) - local.weekday()) % 7
    at = datetime.combine(local.date() + timedelta(days=ahead), time(h, m), ET)
    return at if at > local else at + timedelta(days=7)


def _month_add(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def projection(paid: list[tuple[datetime, Decimal]], now: datetime, split: Decimal) -> dict[str, Any]:
    """Trailing-90-day net payout rate carried forward 12 months (cumulative)."""
    since = now - timedelta(days=90)
    recent = sum((amt for at, amt in paid if at >= since), Decimal(0))
    monthly = (recent * split * Decimal(30) / Decimal(90)).quantize(CENT, rounding=ROUND_DOWN)
    start = to_et(now).date().replace(day=1)
    months = [
        {"month": _month_add(start, i + 1).strftime("%Y-%m"), "net": str(monthly), "cumulative": str(monthly * (i + 1))}
        for i in range(12)
    ]
    return {"basis": "trailing 90-day processed payouts × split", "monthly_net": str(monthly), "months": months}


@router.get("/plan")
async def plan(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    st = request.app.state
    r, c, now = st.rules.rules, st.controller, st.clock.now()
    split = r.funded.payout.split
    rows = list(db.execute(select(Payout).where(Payout.status == "processed")).scalars())
    paid = [(x.processed_at, x.amount) for x in rows if x.processed_at is not None]
    year = to_et(now).year
    ytd = sum((amt for at, amt in paid if to_et(at).year == year), Decimal(0))
    total = sum((amt for _, amt in paid), Decimal(0))
    ytd_net = (ytd * split).quantize(CENT, rounding=ROUND_DOWN)
    tracker = {
        "year": year,
        "ytd_gross": str(ytd),
        "ytd_net": str(ytd_net),
        "all_time_gross": str(total),
        "target_net": str(r.plan.annual_target_net),
        "floor_net": str(r.plan.annual_floor_net),
        "target_pct": str((ytd_net / r.plan.annual_target_net * 100).quantize(Decimal("0.1"))),
        "floor_pct": str((ytd_net / r.plan.annual_floor_net * 100).quantize(Decimal("0.1"))),
        "payouts_processed": len(paid),
    }
    nxt = []
    for a in db.execute(select(Account).where(Account.stage == "FUNDED").order_by(Account.id)).scalars():
        row: dict[str, Any] = {"account_id": a.id, "label": a.label}
        try:
            if a.broker_account_id not in c.adapter.accounts:
                raise BrokerError("broker not connected")
            bal = await c.adapter.get_balance(a.broker_account_id)
        except BrokerError as e:
            nxt.append({**row, "error": str(e)})
            continue
        pp = plan_for(db, r, a, bal, now)
        nxt.append(
            {
                **row,
                "balance": str(bal),
                "kind": pp.kind,
                "amount": str(pp.amount),
                "net": str(pp.net),
                "reason": pp.reason,
            }
        )
    pc = r.payouts
    return {
        "tracker": tracker,
        "projection": projection(paid, now, split),
        "next_payout": {
            "check_at": next_check(now, pc.check_time).isoformat() if pc.frequency == "weekly" else None,
            "frequency": pc.frequency,
            "skim_mode": pc.skim_mode,
            "accounts": nxt,
            "total": str(sum((Decimal(x["amount"]) for x in nxt if "amount" in x), Decimal(0))),
        },
    }
