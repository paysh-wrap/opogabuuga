"""Dashboard profit calculator. Every figure comes from config/income_calc.json (written by
docs/results/agent_review_2026-11-24/calculator_r8/make_calc.py: MAIN strategy = Fast Evaluation NOISE + CANDACE replayed through the
funded rules). UNVERIFIED research projection, not a promise; nothing is hard-coded here (CLAUDE.md: no figures in the UI)."""

from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import Principal, current_user

router = APIRouter(prefix="/api")
CALC_PATH = Path(__file__).resolve().parents[3] / "config" / "income_calc.json"


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def calc_data() -> dict[str, Any]:
    return _load(str(CALC_PATH), CALC_PATH.stat().st_mtime)


def _scale(v: float | None, n: int) -> str | None:
    return None if v is None else str(Decimal(str(v)) * n)


def _basis(meta: dict[str, Any], plan: dict[str, Any], micros: int, profile: str, grow: int, a: dict[str, Any] | None) -> str:
    if micros:
        size = f"NOISE {micros} + CANDACE {micros} micros each, stop ${meta['fixed_stop_usd']}, profit lock 100 pt to entry +10"
        if grow:
            size += f", +1 micro per ${grow:,} cushion (max {meta['max_micros']})"
    else:
        assert a is not None
        brakes = "; ".join(
            f"{name} drops to {q} below ${c:,} cushion" for name, br in (("NOISE", a["noise_brake"]), ("CANDACE", a["candace_brake"])) for c, q in br
        )
        size = f"{a['setup']}: NOISE {a['noise']} (stop ${a['stop_usd']}) + CANDACE {a['candace']} micros" + (f"; {brakes}" if brakes else "")
        if a.get("grow"):
            size += f"; +1 micro per ${int(a['grow'][0]):,} cushion (max {a['grow'][1]})"
    return (
        f"MAIN strategy = {meta['title'].split('= ')[-1]} ({meta['setups']}). Setup: {size}. {meta['data']}, first "
        f"{meta['horizon_sessions']} trading days per account, rolling starts on every day, funded rules: EOD drawdown + lock, DLL, payout "
        f"consistency {meta['payout_consistency_pct']}%, kill switch $50, news {meta['news']}, ${meta['cost_per_micro_rt_usd']} per micro round trip, "
        f"payouts net of {int((1 - Decimal(str(meta['net_split']))) * 100)}% split. {meta['status'].upper()}. {meta['caveat']}"
    )


@router.get("/income/projection")
def income_projection(
    request: Request,
    _: Principal = Depends(current_user),
    plan: str | None = None,
    accounts: int = Query(5, ge=1, le=5),
    micros: int = Query(0, ge=0, le=9),  # 0 = the plan's own fast-pass size + brakes
    cadence: int = Query(10, ge=0, le=20),  # sessions between payouts; 0 = on-demand (UNVERIFIED model)
    grow: int = Query(0, ge=0, le=10000),
    profile: str | None = Query(None, pattern="^(regular|high)$"),
) -> dict[str, Any]:
    d = calc_data()
    meta, plans = d["meta"], d["plans"]
    st = request.app.state
    name = plan or (st.rules.plan if st.rules.plan in plans else sorted(plans)[0])
    if name not in plans:  # whitelist: only plans present in the data file
        raise HTTPException(422, f"unknown plan {name!r}")
    if cadence not in meta["cadences"] or (grow and grow not in meta["grows"]):
        raise HTTPException(422, "cadence / growth value not in the simulated grid")
    p = plans[name]
    prof = profile or ("high" if st.rules.rules.strategy.high_risk else "regular")
    a = None
    if micros:
        key = f"m{micros}|g{grow}|c{cadence}"
        if micros > meta["max_micros"]:
            raise HTTPException(422, "micros above the simulated grid")
    else:
        a = p["auto"][prof]
        key = f"auto-{prof}|c{cadence}"
    c = p["cells"][key]
    n = accounts
    return {
        "plan": name, "plans": sorted(plans), "current_plan": st.rules.plan, "grow": grow, "profile": prof,
        "accounts": n, "micros": micros or a["noise"], "cadence_sessions": cadence, "starts": c["starts"],
        "horizon_sessions": meta["horizon_sessions"], "status": meta["status"], "caveat": meta["caveat"],
        "on_demand_note": meta["on_demand"], "max_micros": meta["max_micros"], "cadences": meta["cadences"],
        "year_mean": _scale(c["year_mean"], n), "year_median": _scale(c["year_median"], n), "year_p25": _scale(c["year_p25"], n),
        "year_p75": _scale(c["year_p75"], n), "week_mean": _scale(c["week_mean"], n), "per_paycheck_mean": _scale(c["per_paycheck_mean"], n),
        "max_possible_year": _scale(p["max_possible_year"], n), "any_payout_pct": str(c["any_payout_pct"]), "bust_pct": str(c["bust_pct"]),
        "max_payouts_pct": str(c["max_payouts_pct"]), "median_sessions_to_first": c["median_sessions_to_first"],
        "auto": a and {"contracts": a["noise"], "candace": a["candace"], "stop_usd": a["stop_usd"], "noise_brake": a["noise_brake"],
                       "candace_brake": a["candace_brake"], "grow": a["grow"], "setup": a["setup"]},
        "basis": _basis(meta, p, micros, prof, grow, a),
    }
