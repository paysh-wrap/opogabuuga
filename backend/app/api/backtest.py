"""Backtest API (§16): upload a 1-minute CSV → replay through the live pipeline in the background → stats + MC."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.backtest.data import DataError, load_csv
from app.backtest.runner import BacktestConfig, run_backtest
from app.backtest.stats import monte_carlo, stats
from app.clock import session_date
from app.models import BacktestRun, BacktestTrade, BiasDecision

router = APIRouter(prefix="/api")
MAX_BYTES = 80 * 1024 * 1024


def _j(x: Any) -> Any:
    if isinstance(x, Decimal):
        return str(x)
    if isinstance(x, dict):
        return {k: _j(v) for k, v in x.items()}
    return x


def metrics(trades: list[dict[str, Any]], rules: Any, stage: str) -> dict[str, Any]:
    from datetime import datetime

    rows = [
        (session_date(datetime.fromisoformat(t["opened_at"])).isoformat(), Decimal(t["pnl"]), _d(t["net_r"]))
        for t in trades
        if t["pnl"] is not None
    ]
    s = stats(rows)
    by_day: dict[str, Decimal] = {}
    for d, p, _ in rows:
        by_day[d] = by_day.get(d, Decimal(0)) + p
    target = rules.eval.profit_target
    mc = monte_carlo(list(by_day.values()), target, rules.eval.max_loss_limit)
    pct = rules.eval.consistency_max_day_pct
    cons_ok = s.best_day_share is None or pct is None or s.best_day_share <= pct / 100
    bd = breakdown(trades)
    return {
        "suggestions": suggestions(bd),
        "breakdown": bd,
        "stats": _j(asdict(s)),
        "monte_carlo_eval": _j(asdict(mc)),
        "consistency_ok": cons_ok,
        "day_pnls": {k: str(v) for k, v in by_day.items()},
    }


def breakdown(trades: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """Where the edge is: P&L, trades and win rate by ET hour, weekday, direction, profile, exit reason."""
    from datetime import datetime

    from app.clock import to_et

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    out: dict[str, dict[str, dict[str, Any]]] = {k: {} for k in ("hour_et", "weekday", "direction", "profile", "exit")}
    for t in trades:
        if t["pnl"] is None:
            continue
        et = to_et(datetime.fromisoformat(t["opened_at"]))
        keys = {
            "hour_et": f"{et.hour:02d}",
            "weekday": days[et.weekday()],
            "direction": t["direction"],
            "profile": t.get("profile") or "?",
            "exit": t.get("exit_reason") or "?",
        }
        pnl = Decimal(t["pnl"])
        for dim, k in keys.items():
            b = out[dim].setdefault(k, {"trades": 0, "wins": 0, "pnl": Decimal(0)})
            b["trades"] += 1
            b["wins"] += pnl > 0
            b["pnl"] += pnl
    for buckets in out.values():
        for b in buckets.values():
            b["win_rate"] = str(round(b["wins"] / b["trades"], 4))
            b["pnl"] = str(b["pnl"])
    return out


def suggestions(bd: dict[str, dict[str, dict[str, Any]]], min_trades: int = 10) -> list[str]:
    """Lab (proposals only — nothing changes without your approval): flag hours / weekdays / sides that lose money
    over a meaningful sample."""
    out = []
    names = {"hour_et": "hour {} ET", "weekday": "{}", "direction": "{} trades", "profile": "{} profile"}
    for dim, label in names.items():
        for k, b in sorted(bd.get(dim, {}).items()):
            if b["trades"] >= min_trades and Decimal(b["pnl"]) < 0:
                out.append(
                    f"Consider skipping {label.format(k)}: {b['trades']} trades, "
                    f"win rate {float(b['win_rate']) * 100:.0f}%, net ${Decimal(b['pnl']):.0f}"
                )
    return out


def _d(x: str | None) -> Decimal | None:
    return Decimal(x) if x is not None else None


@router.post("/backtest")
async def start(
    request: Request,
    symbol: str = Query("MNQ"),
    stage: Literal["EVAL", "FUNDED", "LIVE"] = Query("EVAL"),
    bias: Literal["recorded", "LONG_ONLY", "SHORT_ONLY", "NEUTRAL"] = Query("recorded"),
    one_to_one: bool = Query(False),
    scalp: bool = Query(False),
    eval_mode: bool = Query(False),
    data_source: str = Query("futures", pattern="^(futures|spot)$"),
    p: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    st = request.app.state
    body = await request.body()
    if len(body) > MAX_BYTES:
        raise HTTPException(413, "CSV too large (80 MB max) — split it by month")
    try:
        bars = load_csv(body.decode("utf-8-sig"), symbol_contains=symbol)
    except (DataError, UnicodeDecodeError) as e:
        raise HTTPException(422, str(e)) from e
    rec = {
        b.session_date.isoformat(): b.mapped
        for b in db.execute(select(BiasDecision).order_by(BiasDecision.id)).scalars()
        if b.version != "bt"
    }
    params = {
        "symbol": symbol,
        "stage": stage,
        "bias": bias,
        "one_to_one": one_to_one,
        "scalp": scalp,
        "eval_mode": eval_mode,
        "data_source": data_source,
    }
    run = BacktestRun(kind="ON_DEMAND", status="running", cache_key=f"{symbol}-{len(bars)}", params=params)
    db.add(run)
    audit.record(db, st.clock, p.user.username, "backtest.start", str(len(bars)), params)
    db.commit()
    rid = run.id
    cfg = BacktestConfig(
        symbol=symbol,
        stage=stage,
        bias=bias,
        recorded_bias=rec,
        one_to_one=one_to_one,
        scalp=scalp,
        eval_mode=eval_mode,
        data_source=data_source,
    )

    async def work() -> None:
        try:
            res = await asyncio.to_thread(run_backtest, bars, cfg, st.settings.rules_path)
            m = metrics(res.trades, st.rules.rules, stage)
            m |= {"signals": res.signals, "skips": res.skips, "sessions": res.sessions, "assumptions": res.assumptions}
            with st.sessionmaker() as s:
                r = s.get(BacktestRun, rid)
                assert r is not None
                r.status, r.metrics, r.progress = "done", m, 100
                s.add_all(BacktestTrade(run_id=rid, data=t) for t in res.trades)
                s.commit()
        except Exception as e:  # never silent
            with st.sessionmaker() as s:
                r = s.get(BacktestRun, rid)
                if r is not None:
                    r.status, r.error = "failed", f"{type(e).__name__}: {e}"[:2000]
                    s.commit()

    st.bg_backtests = getattr(st, "bg_backtests", set())
    task = asyncio.create_task(work())
    st.bg_backtests.add(task)
    task.add_done_callback(st.bg_backtests.discard)
    return {"id": rid, "bars": len(bars), "first": bars[0].open_ms, "last": bars[-1].open_ms}


@router.get("/backtest")
def list_runs(_: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.execute(select(BacktestRun).order_by(BacktestRun.id.desc()).limit(50)).scalars()
    return {
        "runs": [
            {"id": r.id, "status": r.status, "params": r.params, "metrics": r.metrics, "error": r.error} for r in rows
        ]
    }


@router.get("/backtest/{rid}/trades")
def run_trades(rid: int, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.execute(select(BacktestTrade).where(BacktestTrade.run_id == rid).order_by(BacktestTrade.id)).scalars()
    return {"trades": [t.data for t in rows]}
