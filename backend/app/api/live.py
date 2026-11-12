"""Live-Readiness API (§1.5). Shows the checklist; the toggle needs the typed phrase. Turning OFF is one click."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.api.automation import _preflight
from app.api.deps import Principal, current_user, get_db
from app.automation import state as stt
from app.clock import session_date
from app.config import RulesConfig
from app.execution.adapters.base import conservative_mode
from app.models import ApiCredential, Notification, Signal, Trade
from app.risk.live_gate import (
    LIVE_PHRASE,
    MIN_PAPER_SESSIONS,
    READINESS_MODES,
    LiveInputs,
    PaperDay,
    can_enable_toggle,
    checklist,
    clean_paper_sessions,
    live_allowed,
)

router = APIRouter(prefix="/api")
READINESS_KEY = "live.readiness_check"
LOOKBACK_DAYS = 400  # paper sessions older than this are not counted


def active_strategies(r: RulesConfig) -> set[str]:
    st = r.strategy
    on = {"NOISE": st.noise, "PM_FADE": st.pm_fade, "AI_BIAS": st.ai_bias, "AI_DUO": st.ai_duo}
    on["ORDER_FLOW"] = st.order_flow
    return {k for k, v in on.items() if v}


def paper_days(db: Session, r: RulesConfig, now: datetime) -> list[PaperDay]:
    """B1: per CME session, closed PAPER trades of the strategies that are ON now, and error banners raised."""
    since = now - timedelta(days=LOOKBACK_DAYS)
    active = active_strategies(r)
    trades: Counter[date] = Counter()
    rows = db.execute(
        select(Trade.opened_at, Signal.features)
        .join(Signal, Signal.id == Trade.signal_id)
        .where(Trade.mode == "PAPER", Trade.closed_at.is_not(None), Trade.opened_at >= since)
    ).all()
    for opened, feats in rows:
        if (feats or {}).get("strategy") in active:
            trades[session_date(opened)] += 1
    errors = Counter(
        session_date(at)
        for (at,) in db.execute(
            select(Notification.created_at).where(Notification.level == "error", Notification.created_at >= since)
        ).all()
    )
    return [PaperDay(d, trades[d], errors[d]) for d in sorted(set(trades) | set(errors))]


def readiness_mode(db: Session) -> str:
    m = stt.get_setting(db, READINESS_KEY, "paper_sessions")
    return m if m in READINESS_MODES else "paper_sessions"


async def live_inputs(request: Request, db: Session) -> LiveInputs:
    st = request.app.state
    c = st.controller
    ct = db.execute(select(ApiCredential).where(ApiCredential.provider == "crosstrade")).scalar_one_or_none()
    pf = await _preflight(request, db)
    now = st.clock.now()
    return LiveInputs(
        env_allow_live=bool(st.settings.allow_live),
        toggle_on=bool(stt.get_setting(db, "live_toggle", False)),
        broker_name=c.adapter.name,
        broker_reads_back=not conservative_mode(c.adapter),
        broker_connected=ct is not None and ct.status == "connected",
        paper_sessions=clean_paper_sessions(paper_days(db, st.rules.rules, now), session_date(now)),
        readiness_mode=readiness_mode(db),
        unconfirmed_verify=len(st.rules.verify_paths),
        preflight_ok=bool(pf["ok"]),
        rules_error=st.rules.error,
    )


async def _view(request: Request, db: Session) -> dict[str, Any]:
    i = await live_inputs(request, db)
    return {
        "live": live_allowed(i),
        "toggle_on": i.toggle_on,
        "phrase": LIVE_PHRASE,
        "checklist": checklist(i),
        "readiness": {"mode": i.readiness_mode, "sessions": i.paper_sessions, "needed": MIN_PAPER_SESSIONS},
    }


@router.get("/live")
async def get_live(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    return await _view(request, db)


class LiveIn(BaseModel):
    enabled: bool
    confirm: str = ""


@router.put("/live")
async def put_live(
    body: LiveIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> Any:
    if body.enabled and not can_enable_toggle(body.confirm):
        raise HTTPException(422, f"type {LIVE_PHRASE!r} to enable live trading")
    now = request.app.state.clock.now()
    stt.set_setting(db, "live_toggle", body.enabled, now)
    audit.record(db, request.app.state.clock, p.user.username, "live.toggle", "household", {"enabled": body.enabled})
    db.commit()
    await request.app.state.hub.broadcast("live.changed", {"toggle_on": body.enabled})
    return await _view(request, db)


class ReadinessIn(BaseModel):
    mode: Literal["paper_sessions", "off"]


@router.put("/live/readiness")
async def put_readiness(
    body: ReadinessIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> Any:
    """B1 toggle: "off" skips ONLY the paper-sessions item; every other live gate (server flag, typed phrase,
    broker, VERIFY, pre-flight, rules) still applies. Each change is audit-logged."""
    before = readiness_mode(db)
    stt.set_setting(db, READINESS_KEY, body.mode, request.app.state.clock.now())
    audit.record(
        db,
        request.app.state.clock,
        p.user.username,
        "live.readiness_check",
        "household",
        {"from": before, "to": body.mode},
    )
    db.commit()
    await request.app.state.hub.broadcast("live.changed", {"readiness": body.mode})
    return await _view(request, db)
