"""Evaluation purchase gate status (§16.9): read-only, computed from the latest finished backtest run."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.models import BacktestRun

router = APIRouter(prefix="/api")


def _dec(v: Any) -> Decimal | None:
    try:
        return None if v is None else Decimal(str(v))
    except InvalidOperation:
        return None


def _check(key: str, label: str, need: str, value: Any, ok: bool | None) -> dict[str, Any]:
    # ok None = this app cannot measure it (never reported as passed)
    return {"key": key, "label": label, "need": need, "value": None if value is None else str(value), "ok": ok}


@router.get("/gate/purchase")
def purchase_gate(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    g = request.app.state.rules.rules.purchase_gate
    run = db.execute(select(BacktestRun).where(BacktestRun.status == "done").order_by(BacktestRun.id.desc())).scalar()
    m: dict[str, Any] = run.metrics if run else {}
    s: dict[str, Any] = m.get("stats") or {}
    mc: dict[str, Any] = m.get("monte_carlo_eval") or {}
    trades = s.get("trades")
    e = _dec(s.get("avg_r"))
    pf = _dec(s.get("profit_factor"))
    pass_rate = _dec(mc.get("pass_rate"))
    checks = [
        _check(
            "trades",
            "Backtest trades",
            f">= {g.min_trades}",
            trades,
            None if trades is None else trades >= g.min_trades,
        ),
        _check("e_net_r", "Net expectancy (R)", f">= {g.min_e_net_r}", e, None if e is None else e >= g.min_e_net_r),
        _check("profit_factor", "Profit factor", f">= {g.min_pf}", pf, None if pf is None else pf >= g.min_pf),
        _check("violations", "Rule violations", f"<= {g.max_violations}", None, None),
        _check("monte_carlo", "Monte Carlo pass rate reported", "reported", pass_rate, pass_rate is not None),
        _check("demo_days", "Clean demo days", f">= {g.demo_days}", None, None),
        _check("semi_auto_sessions", "Clean SEMI-AUTO sessions", f">= {g.semi_auto_sessions}", None, None),
    ]
    return {
        "run_id": run.id if run else None,
        "checks": checks,
        "passed": run is not None and all(c["ok"] is True for c in checks),
        "unmeasured": [c["key"] for c in checks if c["ok"] is None],
    }
