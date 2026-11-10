"""D78: AI bias ledger page data + fast-track backfill control. Live record and backfill estimate are kept apart."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.bias import backfill as bf
from app.bias import ledger as L
from app.clock import ET, session_date
from app.crypto import Vault

router = APIRouter(prefix="/api/ai-ledger")


class BackfillIn(BaseModel):
    days: int = Field(default=60, ge=1, le=bf.MAX_DAYS)


def _job(request: Request) -> bf.Job:
    st = request.app.state
    if not isinstance(getattr(st, "bf_job", None), bf.Job):
        st.bf_job = bf.Job()
    return st.bf_job  # type: ignore[no-any-return]


def _after_close(now: Any) -> bool:
    t = now.astimezone(ET)
    return t.weekday() < 5 and (t.hour, t.minute) >= (16, 1)


@router.get("")
def ai_ledger(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    st = request.app.state
    r, now = st.rules.rules, st.clock.now()
    sess = session_date(now)
    proxy = r.instruments["MNQ"].bias_proxy
    min_acc = float(r.strategy.ai_gate_min_accuracy)
    # D78: after 16:01 ET today's call is scored from the stored 09:30–16:00 bars right away
    through = sess if _after_close(now) and sess == now.astimezone(ET).date() else None
    live = L.status(db, proxy, "MNQ", sess, min_acc, through=through)
    est = L.status(db, bf.bf_proxy(proxy), "MNQ", sess, min_acc, through=sess - timedelta(days=1))
    for k in ("badge", "state", "calls_needed", "required_accuracy", "min_calls"):
        est.pop(k, None)  # a backfill estimate never carries a "proven / may block" verdict
    vault = Vault(st.settings.master_key.get_secret_value())
    return {
        "session": sess.isoformat(),
        "symbol": "MNQ",
        "live": {**live, "rows": live["rows"][-10:]},
        "backfill_estimate": {
            **est,
            "label": "estimate (possible hindsight) — does NOT count toward the proof",
            "rows": est["rows"][-10:],
        },
        "coverage": L.coverage(db, proxy, "MNQ", sess),
        "schedule": r.schedule.bias,
        "job": _job(request).view(),
        "preview": bf.preview(db, vault, r, sess, 60, st.settings.vt_root),
    }


@router.get("/backfill/preview")
def preview(
    request: Request, days: int = 60, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> Any:
    st = request.app.state
    vault = Vault(st.settings.master_key.get_secret_value())
    n = max(1, min(days, bf.MAX_DAYS))
    return bf.preview(db, vault, st.rules.rules, session_date(st.clock.now()), n, st.settings.vt_root)


@router.post("/backfill")
async def start(
    body: BackfillIn, request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> Any:
    st = request.app.state
    job = _job(request)
    if job.status == "running":
        raise HTTPException(409, "a backfill is already running")
    vault = Vault(st.settings.master_key.get_secret_value())
    pv = bf.preview(db, vault, st.rules.rules, session_date(st.clock.now()), body.days, st.settings.vt_root)
    if not pv["configured"]:
        raise HTTPException(400, "TradingAgents LLM key not set (Connections page)")
    new = bf.Job(status="running", days_requested=body.days, started=st.clock.now().isoformat(timespec="seconds"))
    st.bf_job = new
    new.task = asyncio.create_task(
        bf.run_job(
            new,
            st.sessionmaker,
            st.ta,
            vault,
            st.rules.rules,
            st.clock,
            st.controller.notify,
            session_date(st.clock.now()),
            body.days,
            st.settings.vt_root,
        )
    )
    return {"started": True, "preview": pv}


@router.post("/backfill/cancel")
def cancel(request: Request, _: Principal = Depends(current_user)) -> Any:
    job = _job(request)
    job.cancel = True
    return {"cancelling": job.status == "running"}
