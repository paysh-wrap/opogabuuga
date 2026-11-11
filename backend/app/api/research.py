"""D94: Trading-R1 research card. INFORMATION ONLY — nothing here reaches a gate, score, bias, size or order."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.connections.service import credentials
from app.crypto import Vault
from app.research import trading_r1 as tr1

router = APIRouter(prefix="/api/research")
PID = "tradingr1"


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=tr1.MAX_QUESTION)


def _state(request: Request) -> dict[str, Any]:
    st = request.app.state
    if not isinstance(getattr(st, "tr1", None), dict):
        st.tr1 = {"running": False, "last": None, "task": None}
    return st.tr1  # type: ignore[no-any-return]


def _key(request: Request, db: Session) -> str | None:
    vault = Vault(request.app.state.settings.master_key.get_secret_value())
    c = credentials(db, vault, PID)
    return (c or {}).get("api_key") or None


def _factory(request: Request) -> Callable[[Path, str], tr1.Runner]:
    f = getattr(request.app.state, "tr1_runner_factory", None)
    return f if callable(f) else tr1.ServeRunner


def _view(request: Request, db: Session) -> dict[str, Any]:
    root = Path(request.app.state.settings.tr1_root)
    configured, message = tr1.status(root, _key(request, db))
    s = _state(request)
    return {
        "label": tr1.LABEL,
        "configured": configured,
        "message": message,
        "running": s["running"],
        "last": s["last"],
    }


@router.get("/trading-r1")
def get_tr1(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    return _view(request, db)


@router.post("/trading-r1", status_code=202)
async def ask_tr1(
    body: AskIn, request: Request, user: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> Any:
    root = Path(request.app.state.settings.tr1_root)
    key = _key(request, db)
    configured, message = tr1.status(root, key)
    if not configured or key is None:
        raise HTTPException(409, message)
    try:
        payload = tr1.body(body.question)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    s = _state(request)
    if s["running"]:
        raise HTTPException(409, "a Trading-R1 question is already running")
    clock = request.app.state.clock
    audit.record(db, clock, user.user.username, "research.trading_r1.asked", PID, {"chars": len(payload["question"])})
    db.commit()
    runner = _factory(request)(root, key)
    s["running"] = True

    async def go() -> None:
        try:
            r = await runner.research(payload["question"])
        except Exception as e:
            r = tr1.Result(False, "", "", f"runner error: {type(e).__name__}", 0)
        s["last"] = {
            "question": payload["question"],
            "ok": r.ok,
            "text": r.text,
            "termination": r.termination,
            "error": r.error,
            "rounds": r.rounds,
            "at": clock.now().isoformat(),
        }
        s["running"] = False

    s["task"] = asyncio.create_task(go())
    return _view(request, db)
