"""Live-Readiness API (§1.5). Shows the checklist; the toggle needs the typed phrase. Turning OFF is one click."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.api.automation import _preflight
from app.api.deps import Principal, current_user, get_db
from app.automation import state as stt
from app.execution.adapters.base import conservative_mode
from app.models import ApiCredential
from app.risk.live_gate import LIVE_PHRASE, LiveInputs, can_enable_toggle, checklist, live_allowed

router = APIRouter(prefix="/api")


async def live_inputs(request: Request, db: Session) -> LiveInputs:
    st = request.app.state
    c = st.controller
    ct = db.execute(select(ApiCredential).where(ApiCredential.provider == "crosstrade")).scalar_one_or_none()
    pf = await _preflight(request, db)
    return LiveInputs(
        env_allow_live=bool(st.settings.allow_live),
        toggle_on=bool(stt.get_setting(db, "live_toggle", False)),
        broker_name=c.adapter.name,
        broker_reads_back=not conservative_mode(c.adapter),
        broker_connected=ct is not None and ct.status == "connected",
        parity_sessions=int(stt.get_setting(db, "parity_sessions_passed", 0) or 0),  # type: ignore[call-overload]
        unconfirmed_verify=len(st.rules.verify_paths),
        preflight_ok=bool(pf["ok"]),
        rules_error=st.rules.error,
    )


async def _view(request: Request, db: Session) -> dict[str, Any]:
    i = await live_inputs(request, db)
    return {"live": live_allowed(i), "toggle_on": i.toggle_on, "phrase": LIVE_PHRASE, "checklist": checklist(i)}


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
