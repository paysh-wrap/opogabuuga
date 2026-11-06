"""Weekly payout check (§14). Lucid has no API → the app PLANS and reminds; the user requests it in Lucid's dashboard,
then marks it submitted (trading blocks until processed) and processed. Paper accounts are debited on "processed"."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.clock import ET, to_et
from app.execution.adapters.base import BrokerError
from app.models import Account, Payout, Trade
from app.phases.payout_plan import PayoutPlan, plan_payout


def week_key(now: datetime) -> str:
    y, w, _ = to_et(now).isocalendar()
    return f"{y}-W{w:02d}"


def _week_start(now: datetime) -> datetime:
    d = to_et(now).date()
    return datetime.combine(d - timedelta(days=d.weekday()), time(0), ET)


def _sum(s: Session, a: Account, since: datetime | None) -> Decimal:
    q = select(Trade.pnl_usd).where(Trade.account_id == a.id, Trade.closed_at.is_not(None))
    if since is not None:
        q = q.where(Trade.closed_at >= since)
    return sum((x or Decimal(0) for x in s.execute(q).scalars()), Decimal(0))


def _last_processed(s: Session, a: Account) -> datetime | None:
    return s.execute(
        select(Payout.processed_at)
        .where(Payout.account_id == a.id, Payout.status == "processed")
        .order_by(Payout.processed_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _profitable_days(s: Session, a: Account, since: datetime | None, min_day: Decimal) -> int:
    from app.clock import session_date

    q = select(Trade).where(Trade.account_id == a.id, Trade.closed_at.is_not(None))
    if since is not None:
        q = q.where(Trade.closed_at >= since)
    days: dict[str, Decimal] = {}
    for t in s.execute(q).scalars():
        assert t.closed_at is not None
        k = session_date(t.closed_at).isoformat()
        days[k] = days.get(k, Decimal(0)) + (t.pnl_usd or Decimal(0))
    return sum(1 for v in days.values() if v >= min_day and v > 0)


def plan_for(s: Session, rules: Any, a: Account, balance: Decimal, now: datetime) -> PayoutPlan:
    pr, pc = rules.funded.payout, rules.payouts
    last = _last_processed(s, a)
    done = len(s.execute(select(Payout.id).where(Payout.account_id == a.id, Payout.status == "processed")).all())
    if pr.max_payouts is not None and done >= pr.max_payouts:
        return PayoutPlan(None, Decimal(0), Decimal(0), "MAX_PAYOUTS_REACHED")
    return plan_payout(
        balance=balance,
        week_profit=_sum(s, a, _week_start(now)),
        cycle_profit=_sum(s, a, last),
        locked=bool(a.mll_locked),
        sweep_above=pc.sweep_above,
        skim_mode=pc.skim_mode,
        buffer=pr.buffer,
        min_request=pr.min_request,
        min_cycle_profit=pr.min_cycle_profit,
        split=pr.split,
        payout_no=done + 1,
        max_first=pr.max_first,
        max_next=pr.max_next,
        max_pct_of_profit=pr.max_pct_of_profit,
        profitable_days=_profitable_days(s, a, last, pr.min_day_profit),
        min_profitable_days=pr.min_profitable_days,
    )


async def weekly_check(s: Session, ctl: Any, rules: Any, now: datetime) -> list[Payout]:
    """Creates at most one 'ready' payout per FUNDED account per ISO week."""
    out = []
    wk = week_key(now)
    for a in s.execute(select(Account).where(Account.stage == "FUNDED")).scalars():
        if a.broker_account_id not in ctl.adapter.accounts:
            continue
        if s.execute(select(Payout.id).where(Payout.account_id == a.id, Payout.week == wk)).first():
            continue
        try:
            bal = await ctl.adapter.get_balance(a.broker_account_id)
        except BrokerError as e:
            ctl.notify("error", "Payout check failed", f"{a.label}: {e}")
            continue
        p = plan_for(s, rules, a, bal, now)
        if p.kind is None:
            continue
        row = Payout(account_id=a.id, week=wk, kind=p.kind, amount=p.amount, balance_before=bal, status="ready")
        s.add(row)
        audit.record(
            s, ctl.clock, "payouts", "payout.planned", a.broker_account_id, {"kind": p.kind, "amount": str(p.amount)}
        )
        ctl.notify(
            "info", "Payout ready", f"{a.label}: request ${p.amount} ({p.kind}) in your Lucid dashboard", "payout"
        )
        ctl.publish("payout.ready", {"account": a.id, "kind": p.kind, "amount": str(p.amount), "week": wk})
        out.append(row)
    return out


def due(now: datetime, check_time: str, last_week: str | None) -> bool:
    """True once per ISO week, at/after the configured weekday + time (ET)."""
    day, hm = check_time.split()
    h, m = (int(x) for x in hm.split(":"))
    local = to_et(now)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    after = (local.weekday(), local.time()) >= (days.index(day), time(h, m))
    return after and last_week != week_key(now)
