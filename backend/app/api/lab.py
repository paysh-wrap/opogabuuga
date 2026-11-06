"""Self-Learning Lab (§17, step 1): progress per session, backtest history, suggestions → proposals you approve.
Nothing here changes trading rules by itself; approved proposals are recorded for the guarded apply step (§17)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.clock import session_date
from app.models import BacktestRun, Proposal, Trade

router = APIRouter(prefix="/api")


def session_progress(rows: list[tuple[str, Decimal, Decimal | None]]) -> list[dict[str, Any]]:
    """rows = (session iso, pnl, net_r) → per-session stats + running (cumulative) win rate and net."""
    by: dict[str, list[tuple[Decimal, Decimal | None]]] = {}
    for d, p, r in rows:
        by.setdefault(d, []).append((p, r))
    out, wins_all, n_all, net_all = [], 0, 0, Decimal(0)
    for d in sorted(by):
        ts = by[d]
        w = sum(1 for p, _ in ts if p > 0)
        rs = [r for _, r in ts if r is not None]
        net = sum((p for p, _ in ts), Decimal(0))
        wins_all, n_all, net_all = wins_all + w, n_all + len(ts), net_all + net
        out.append(
            {
                "session": d,
                "trades": len(ts),
                "win_rate": round(w / len(ts), 4),
                "net": str(net),
                "avg_r": str(round(sum(rs, Decimal(0)) / len(rs), 3)) if rs else None,
                "cum_win_rate": round(wins_all / n_all, 4),
                "cum_net": str(net_all),
            }
        )
    return out


@router.get("/lab")
def lab(_: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    trades = db.execute(select(Trade).where(Trade.closed_at.is_not(None)).order_by(Trade.closed_at)).scalars()
    rows = [
        (session_date(t.closed_at).isoformat(), t.pnl_usd or Decimal(0), t.net_r)
        for t in trades
        if t.closed_at is not None
    ]
    runs = db.execute(select(BacktestRun).where(BacktestRun.status == "done").order_by(BacktestRun.id)).scalars()
    bts = []
    latest_suggestions: list[str] = []
    for r in runs:
        s = r.metrics.get("stats", {})
        mc = r.metrics.get("monte_carlo_eval", {})
        bts.append(
            {
                "id": r.id,
                "params": r.params,
                "trades": s.get("trades"),
                "win_rate": s.get("win_rate"),
                "profit_factor": s.get("profit_factor"),
                "net": s.get("net"),
                "mc_pass": mc.get("pass_rate"),
                "sessions": r.metrics.get("sessions"),
            }
        )
        latest_suggestions = r.metrics.get("suggestions", []) or latest_suggestions
    props = db.execute(select(Proposal).order_by(Proposal.id.desc()).limit(50)).scalars()
    from app.automation import state as stt
    from app.lab.tunables import TUNABLE_PARAMS
    from app.risk.settings_store import latest

    lab_row = latest(db, "lab")
    return {
        "lab_layer": {"version": lab_row.version, "settings": lab_row.settings} if lab_row else None,
        "last_cycle": stt.get_setting(db, "lab.last_cycle"),
        "tunables": {k: {"lo": str(t.lo), "hi": str(t.hi), "step": str(t.step)} for k, t in TUNABLE_PARAMS.items()},
        "sessions": session_progress(rows),
        "backtests": bts,
        "suggestions": latest_suggestions,
        "proposals": [
            {
                "id": p.id,
                "text": p.explanation,
                "status": p.status,
                "metrics": p.metrics,
                "diff": p.diff,
                "at": p.created_at.isoformat(),
            }
            for p in props
        ],
    }


class ProposalIn(BaseModel):
    text: str = Field(min_length=3, max_length=500)


@router.post("/lab/proposals")
def add_proposal(
    body: ProposalIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    row = Proposal(challenger_version=0, diff={}, metrics={}, explanation=body.text, status="pending")
    db.add(row)
    audit.record(db, request.app.state.clock, p.user.username, "lab.proposal", body.text[:64], {})
    db.commit()
    return {"id": row.id, "status": row.status}


class DecisionIn(BaseModel):
    status: Literal["approved", "rejected"]


@router.put("/lab/proposals/{pid}")
def decide(
    pid: int, body: DecisionIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    row = db.get(Proposal, pid)
    if row is None:
        raise HTTPException(404, "no such proposal")
    if row.status != "pending":
        raise HTTPException(409, f"already {row.status}")
    row.status = body.status
    audit.record(db, request.app.state.clock, p.user.username, f"lab.{body.status}", str(pid), {})
    db.commit()
    return {"id": pid, "status": row.status}


@router.post("/lab/cycle")
async def run_now(
    request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Run the §17.3 challenger search now (same guards as the weekly run). Creates a proposal only if one wins."""
    from app.automation import state as stt
    from app.lab.cycle import run_cycle

    st = request.app.state
    now = st.clock.now()
    report = await run_cycle(request.app, db, now)
    stt.set_setting(db, "lab.last_cycle", {"at": now.isoformat(), "report": report}, now)
    audit.record(db, st.clock, p.user.username, "lab.cycle_run", "manual", {})
    db.commit()
    return {"report": report}


@router.post("/lab/rollback")
def lab_rollback(
    request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """One-click rollback of the newest applied Lab change (takes effect for the next NEW trade)."""
    from app.lab.cycle import rollback_lab

    st = request.app.state
    v = rollback_lab(db, st.clock, p.user.username)
    st.rules.refresh(db)
    return {"active_lab_version": v}
