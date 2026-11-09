"""D59: projected income from funded Lucid accounts on the Dashboard (research replay of the MAIN strategy)."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import Principal, current_user
from app.backtest.income_projection import project, rules_view
from app.config import load_rules

router = APIRouter(prefix="/api")


@lru_cache(maxsize=64)
def _cached(path: str, mtime: float, accounts: int, micros: int, cadence: int) -> dict[str, Any]:
    r = load_rules(Path(path)).rules
    p = project(rules_view(r), accounts=accounts, micros=micros, cadence=cadence)
    return {k: (str(v) if v is not None and not isinstance(v, int) else v) for k, v in asdict(p).items()}


@router.get("/income/projection")
def income_projection(
    request: Request,
    _: Principal = Depends(current_user),
    plan: str | None = None,
    accounts: int = Query(5, ge=1, le=5),
    micros: int = Query(1, ge=1, le=5),
    cadence: int = Query(10, ge=5, le=20),
) -> dict[str, Any]:
    st = request.app.state
    folder: Path = st.settings.rules_path.parent
    plans = sorted(p.stem for p in folder.glob("lucid_*.yaml"))
    name = plan or st.rules.plan
    if name not in plans:  # whitelist: only plan files in the rules folder (no paths from the client)
        raise HTTPException(422, f"unknown plan {name!r}")
    path = folder / f"{name}.yaml"
    out = _cached(str(path), path.stat().st_mtime, accounts, micros, cadence)
    return {
        **out,
        "plan": name,
        "plans": plans,
        "current_plan": st.rules.plan,
        "basis": "MAIN strategy (NOISE $250 + afternoon fade $250), Databento MNQ 2021-11 → 2026-10, replayed through "
        "the plan's funded payout rules; rolling starts, first 12 months per account. Research projection, not a "
        "promise: same trades on every account, open-trade drawdown and news not modeled, eval fees not subtracted.",
    }
