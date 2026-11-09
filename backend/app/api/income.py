"""D59: projected income from funded Lucid accounts on the Dashboard (research replay of the MAIN strategy)."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import Principal, current_user
from app.backtest.income_projection import project, rules_view
from app.config import load_rules
from app.risk.strategy_sizing import SizeTier, tier_for

router = APIRouter(prefix="/api")


@lru_cache(maxsize=64)
def _cached(
    path: str, mtime: float, accounts: int, micros: int, cadence: int, grow: int, high: bool = False
) -> dict[str, Any]:
    """micros = 0 → D63 automatic size from the plan's size_table (tier for the plan's account size + brake)."""
    r = load_rules(Path(path)).rules
    g = Decimal(grow) if grow else None
    brake: tuple[Decimal, int] | None = None
    auto = None
    if micros == 0:
        table = (r.strategy.size_table_high or r.strategy.size_table) if high else r.strategy.size_table
        if table:
            t = tier_for(
                r.account_size,
                [SizeTier(x.account_size, x.mll, x.contracts, x.brake_below, x.brake_contracts) for x in table],
            )
            micros = t.contracts
            if t.brake_below is not None and t.brake_contracts is not None:
                brake = (t.brake_below, t.brake_contracts)
            auto = {
                "contracts": t.contracts,
                "brake_below": None if t.brake_below is None else str(t.brake_below),
                "brake_contracts": t.brake_contracts,
            }
        else:
            micros = r.strategy.noise_cfg.contracts
    p = project(rules_view(r), accounts=accounts, micros=micros, cadence=cadence, grow_per=g, brake=brake)
    out = {k: (str(v) if v is not None and not isinstance(v, int) else v) for k, v in asdict(p).items()}
    return {**out, "auto": auto}


@router.get("/income/projection")
def income_projection(
    request: Request,
    _: Principal = Depends(current_user),
    plan: str | None = None,
    accounts: int = Query(5, ge=1, le=5),
    micros: int = Query(0, ge=0, le=6),  # 0 = automatic (D63 size_table)
    cadence: int = Query(10, ge=5, le=20),
    grow: int = Query(0, ge=0, le=10000),  # D60: +1 micro per `grow` $ of cushion above the trailing MLL (0 = fixed)
    profile: str | None = Query(None, pattern="^(regular|high)$"),  # D64: size profile for "Auto" (default: active)
) -> dict[str, Any]:
    st = request.app.state
    folder: Path = st.settings.rules_path.parent
    plans = sorted(p.stem for p in folder.glob("lucid_*.yaml"))
    name = plan or st.rules.plan
    if name not in plans:  # whitelist: only plan files in the rules folder (no paths from the client)
        raise HTTPException(422, f"unknown plan {name!r}")
    path = folder / f"{name}.yaml"
    high = st.rules.rules.strategy.high_risk if profile is None else profile == "high"
    out = _cached(str(path), path.stat().st_mtime, accounts, micros, cadence, grow, high)
    return {
        **out,
        "plan": name,
        "grow": grow,
        "profile": "high" if high else "regular",
        "plans": plans,
        "current_plan": st.rules.plan,
        "basis": "MAIN strategy (NOISE $250 + afternoon fade $250), Databento MNQ 2021-11 → 2026-10, replayed through "
        "the plan's funded payout rules; rolling starts, first 12 months per account. Research projection, not a "
        "promise: same trades on every account, open-trade drawdown and news not modeled, eval fees not subtracted.",
    }
