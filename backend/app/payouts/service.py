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
from app.risk.consistency import (
    PayoutConsistency,
    payout_consistency,
    payout_consistency_text,
    payout_limit,
    payout_rule_applies,
)


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


def _largest_day(s: Session, a: Account, since: datetime | None) -> Decimal:
    from app.clock import session_date

    q = select(Trade).where(Trade.account_id == a.id, Trade.closed_at.is_not(None))
    if since is not None:
        q = q.where(Trade.closed_at >= since)
    days: dict[str, Decimal] = {}
    for t in s.execute(q).scalars():
        assert t.closed_at is not None
        k = session_date(t.closed_at).isoformat()
        days[k] = days.get(k, Decimal(0)) + (t.pnl_usd or Decimal(0))
    return max(days.values(), default=Decimal(0))


def cycle_start(s: Session, a: Account) -> datetime | None:
    """D89: the payout cycle starts at the last processed payout, else at the FUNDED start (stage_started_at)."""
    return _last_processed(s, a) or a.stage_started_at


def cycle_day_profits(s: Session, a: Account) -> list[Decimal]:
    from app.clock import session_date

    q = select(Trade).where(Trade.account_id == a.id, Trade.closed_at.is_not(None))
    since = cycle_start(s, a)
    if since is not None:
        q = q.where(Trade.closed_at >= since)
    days: dict[str, Decimal] = {}
    for t in s.execute(q).scalars():
        assert t.closed_at is not None
        k = session_date(t.closed_at).isoformat()
        days[k] = days.get(k, Decimal(0)) + (t.pnl_usd or Decimal(0))
    return list(days.values())


def payout_consistency_for(s: Session, rules: Any, a: Account) -> tuple[PayoutConsistency, bool] | None:
    """D89: (status, purchase date known) when Lucid's payout consistency rule applies to this account (FUNDED, plan has
    it), else None. Unknown purchase/reset date → the stricter legacy limit."""
    cfg = rules.funded.payout_consistency
    if cfg is None or not payout_rule_applies(a.stage, True):
        return None
    limit, known = payout_limit(a.purchased_at, cfg.pct, cfg.legacy_pct, cfg.legacy_cutoff)
    return payout_consistency(cycle_day_profits(s, a), limit), known


def consistency_view(s: Session, rules: Any, a: Account) -> dict[str, Any] | None:
    """JSON for the Payouts page and the Dashboard."""
    got = payout_consistency_for(s, rules, a)
    if got is None:
        return None
    c, known = got
    return {
        "pct": None if c.pct is None else str(c.pct.quantize(Decimal("0.1"))),
        "limit": str(c.limit),
        "largest_day": str(c.largest_day),
        "cycle_profit": str(c.cycle_profit),
        "eligible": c.eligible,
        "needed_cycle_profit": str(c.needed_cycle_profit),
        "still_needed": str(c.still_needed),
        "text": payout_consistency_text(c),
        "date_known": known,
        "verify": None
        if known
        else "Purchase / last reset date unknown: the stricter legacy limit is used. Enter it on the Accounts page.",
    }


def plan_for(s: Session, rules: Any, a: Account, balance: Decimal, now: datetime) -> PayoutPlan:
    pr, pc = rules.funded.payout, rules.payouts
    last = _last_processed(s, a)
    done = len(s.execute(select(Payout.id).where(Payout.account_id == a.id, Payout.status == "processed")).all())
    if pr.max_payouts is not None and done >= pr.max_payouts:
        return PayoutPlan(None, Decimal(0), Decimal(0), "MAX_PAYOUTS_REACHED")
    pcons = payout_consistency_for(s, rules, a)
    if pcons is not None and not pcons[0].eligible:  # D89: a payout may only be proposed while the rule is met
        return PayoutPlan(None, Decimal(0), Decimal(0), "CONSISTENCY")
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
        mode=pc.mode,
        largest_day=_largest_day(s, a, last),
        consistency_pct=pcons[0].limit if pcons is not None else rules.funded.consistency_max_day_pct,
        min_pct_of_cap=pc.min_pct_of_cap,
    )


def _sessions_since(last: datetime | None, now: datetime) -> int:
    """Weekdays from the last processed payout's session to now's session (no payout yet → large)."""
    from app.clock import session_date

    if last is None:
        return 10**6
    d, end, n = session_date(last), session_date(now), 0
    while d < end:
        d += timedelta(days=1)
        n += d.weekday() < 5
    return n


async def session_check(s: Session, ctl: Any, rules: Any, now: datetime) -> list[Payout]:
    """D65: once per session — plan a payout for every FUNDED account that has no open payout and is at least
    payouts.min_sessions_between sessions past its last processed payout (Lucid Pro: request any day once eligible)."""
    from app.clock import session_date

    gap = rules.payouts.min_sessions_between
    eligible = []
    for a in s.execute(select(Account).where(Account.stage == "FUNDED")).scalars():
        open_ = s.execute(
            select(Payout.id).where(Payout.account_id == a.id, Payout.status.in_(("ready", "submitted")))
        ).first()
        if open_ is None and _sessions_since(_last_processed(s, a), now) >= gap:
            eligible.append(a.id)
    return await weekly_check(s, ctl, rules, now, key=session_date(now).isoformat(), only=eligible)


async def weekly_check(
    s: Session, ctl: Any, rules: Any, now: datetime, key: str | None = None, only: list[int] | None = None
) -> list[Payout]:
    """Creates at most one 'ready' payout per FUNDED account per ISO week (or per `key`, e.g. a session date)."""
    out = []
    wk = key or week_key(now)
    for a in s.execute(select(Account).where(Account.stage == "FUNDED")).scalars():
        if only is not None and a.id not in only:
            continue
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


def session_due(now: datetime, hm: str, last_day: str | None) -> bool:
    """D65: True once per weekday session, at/after hm (ET)."""
    from app.clock import session_date

    h, m = (int(x) for x in hm.split(":"))
    local = to_et(now)
    return local.weekday() < 5 and local.time() >= time(h, m) and last_day != session_date(now).isoformat()


def due(now: datetime, check_time: str, last_week: str | None) -> bool:
    """True once per ISO week, at/after the configured weekday + time (ET)."""
    day, hm = check_time.split()
    h, m = (int(x) for x in hm.split(":"))
    local = to_et(now)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    after = (local.weekday(), local.time()) >= (days.index(day), time(h, m))
    return after and last_week != week_key(now)
