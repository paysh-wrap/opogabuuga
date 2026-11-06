"""Read-only UI insights (§24): Today plan (blackouts, windows, pace) and the daily P&L calendar."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.automation import state as stt
from app.clock import session_date
from app.config import RulesConfig
from app.engine.filters import CooldownState
from app.models import Account, Cooldown, DailyAccountStats, Trade

router = APIRouter(prefix="/api")


def news_blackouts(rules: RulesConfig, events: list[Any]) -> list[dict[str, Any]]:
    """No-entry window and flatten time per high-impact event. All minutes come from the loaded rules.

    The 'after' side is the longest across enabled markets (instrument news_after_min, else the eval breach minutes)."""
    before = rules.internal.no_entry_before_news_min
    flat = rules.internal.news_flatten_before_min
    afters = [
        i.news_after_min if i.news_after_min is not None else rules.eval.news_breach_min_after
        for i in rules.instruments.values()
        if i.enabled
    ] or [rules.eval.news_breach_min_after]
    after = max(afters)
    return [
        {
            "at": e.at.isoformat(),
            "title": e.title,
            "no_entry_from": (e.at - timedelta(minutes=before)).isoformat(),
            "no_entry_until": (e.at + timedelta(minutes=after)).isoformat(),
            "flatten_at": (e.at - timedelta(minutes=flat)).isoformat(),
        }
        for e in events
    ]


def entry_windows(rules: RulesConfig) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    intraday = getattr(rules.internal, "intraday_windows", None)
    for sym, i in rules.instruments.items():
        if not i.enabled:
            continue
        out.append({"symbol": sym, "label": "Trading hours", "windows": i.windows or rules.internal.windows})
        if intraday:
            out.append({"symbol": sym, "label": "Intraday mode (best hours)", "windows": intraday})
    return out


def eval_pace(db: Session, a: Account, rules: RulesConfig) -> dict[str, Any]:
    q = select(Trade.pnl_usd).where(Trade.account_id == a.id, Trade.closed_at.is_not(None))
    if a.stage_started_at is not None:
        q = q.where(Trade.closed_at >= a.stage_started_at)
    profit = sum((p or Decimal(0) for p in db.execute(q).scalars()), Decimal(0))
    dq = select(DailyAccountStats.day_profit).where(DailyAccountStats.account_id == a.id)
    if a.stage_started_at is not None:
        dq = dq.where(DailyAccountStats.session_date >= session_date(a.stage_started_at))
    days = [d for d in db.execute(dq).scalars() if d > 0]
    ts = rules.eval_mode.target_sessions
    return {
        "id": a.id,
        "label": a.label,
        "profit": str(profit),
        "target": str(rules.eval.profit_target),
        "profitable_days": len(days),
        "min_profitable_days": rules.eval.min_profitable_days,
        "sessions_used": stt.stage_sessions(db, a),
        "target_sessions": ts.target,
        "max_sessions": ts.max,
    }


@router.get("/today/plan")
def today_plan(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    st = request.app.state
    r, now = st.rules.rules, st.clock.now()
    sess = session_date(now)
    events = st.calendar(sess)
    accounts = list(db.execute(select(Account).order_by(Account.priority, Account.id)).scalars())
    cds = [
        {
            "symbol": c.symbol,
            "profile": c.profile,
            "until_session": c.until_session.isoformat() if c.until_session else None,
        }
        for c in db.execute(select(Cooldown)).scalars()
        if CooldownState(c.streak, c.until_session).active(sess)
    ]
    return {
        "session": sess.isoformat(),
        "calendar_loaded": events is not None,
        "news": news_blackouts(r, events or []),
        "news_rules": {
            "no_entry_before_min": r.internal.no_entry_before_news_min,
            "flatten_before_min": r.internal.news_flatten_before_min,
        },
        "windows": entry_windows(r),
        "accounts": [
            {"id": a.id, "label": a.label, "stage": a.stage, "armed": a.armed, "selected": a.selected}
            for a in accounts
            if a.armed or a.selected
        ],
        "attested_today": stt.attested_today(db, now),
        "preflight": getattr(st, "last_preflight", None),
        "cooldowns": cds,
        "eval_pace": [eval_pace(db, a, r) for a in accounts if a.stage == "EVAL"],
    }


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _pack(m: dict[date, Decimal]) -> dict[str, Any]:
    weeks: dict[date, Decimal] = defaultdict(lambda: Decimal(0))
    for d, v in m.items():
        weeks[_week_start(d)] += v
    return {
        "days": [{"date": d.isoformat(), "pnl": str(v)} for d, v in sorted(m.items())],
        "weeks": [{"week_start": w.isoformat(), "pnl": str(v)} for w, v in sorted(weeks.items())],
        "total": str(sum(m.values(), Decimal(0))),
    }


@router.get("/pnl/daily")
def pnl_daily(
    request: Request,
    account_id: int | None = Query(None),
    days: int = Query(90, ge=1, le=730),
    _: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Daily net P&L from closed trades (CME session date). Household + per account; EVAL gets the consistency view."""
    r, now = request.app.state.rules.rules, request.app.state.clock.now()
    since = session_date(now) - timedelta(days=days)
    accts = {a.id: a for a in db.execute(select(Account)).scalars()}
    q = select(Trade.account_id, Trade.pnl_usd, Trade.closed_at).where(Trade.closed_at.is_not(None))
    if account_id is not None:
        q = q.where(Trade.account_id == account_id)
    per: dict[int, dict[date, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal(0)))
    for aid, pnl, closed in db.execute(q).all():
        if closed is not None and pnl is not None and session_date(closed) >= since:
            per[aid][session_date(closed)] += pnl
    house: dict[date, Decimal] = defaultdict(lambda: Decimal(0))
    for dd in per.values():
        for d, v in dd.items():
            house[d] += v
    pct = r.eval.consistency_max_day_pct
    out_accounts = []
    for aid, m in sorted(per.items()):
        a = accts.get(aid)
        row: dict[str, Any] = {
            "id": aid,
            "label": a.label if a else str(aid),
            "stage": a.stage if a else None,
            **_pack(m),
        }
        if a is not None and a.stage == "EVAL" and pct is not None:
            best_d, best = max(m.items(), key=lambda kv: kv[1])
            total = sum(m.values(), Decimal(0))
            row["eval"] = {
                "largest_day": best_d.isoformat(),
                "largest_pnl": str(best),
                "limit_pct": str(pct),
                "cap": str(r.eval.profit_target * pct / 100),
                "largest_pct": str(best / total * 100) if total > 0 and best > 0 else None,
            }
        out_accounts.append(row)
    return {"since": since.isoformat(), "household": _pack(house), "accounts": out_accounts}
