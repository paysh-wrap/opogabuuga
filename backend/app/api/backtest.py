"""Backtest API (§16): upload a 1-minute CSV → replay through the live pipeline in the background → stats + MC."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.backtest.data import DataError, load_csv
from app.backtest.payout_sim import FundedSim, income_monte_carlo, simulate_payouts
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
    days_sorted = [by_day[k] for k in sorted(by_day)]
    fc = funded_sim_cfg(rules)
    sim = simulate_payouts(days_sorted, fc)
    inc = income_monte_carlo(days_sorted, fc, rules.plan.annual_floor_net, rules.plan.annual_target_net)
    return {
        "payout_sim": _j(
            {
                "weeks": [asdict(w) for w in sim.weeks],
                "total_gross": sim.total_gross,
                "total_net": sim.total_net,
                "breached": sim.breached,
            }
        ),
        "income_mc": {
            "runs": inc.runs,
            "sessions": inc.sessions,
            "floor": str(rules.plan.annual_floor_net),
            "target": str(rules.plan.annual_target_net),
            "by_accounts": {str(n): _j(v) for n, v in inc.by_accounts.items()},
        },
        "suggestions": suggestions(bd),
        "breakdown": bd,
        "stats": _j(asdict(s)),
        "monte_carlo_eval": _j(asdict(mc)),
        "consistency_ok": cons_ok,
        "day_pnls": {k: str(v) for k, v in by_day.items()},
    }


def funded_sim_cfg(rules: Any) -> FundedSim:
    f, pr, pc = rules.funded, rules.funded.payout, rules.payouts
    start = Decimal(rules.account_size)
    return FundedSim(
        start_balance=start,
        max_loss=f.max_loss_limit,
        lock_trigger=f.lock_trigger,
        lock_level=f.lock_level,
        sweep_above=pc.sweep_above,
        skim_mode=pc.skim_mode,
        buffer=pr.buffer,
        min_request=pr.min_request,
        split=pr.split,
        max_first=pr.max_first,
        max_next=pr.max_next,
        max_pct_of_profit=pr.max_pct_of_profit,
    )


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
    low_risk: bool = Query(False),
    eval_mode: bool = Query(False),
    drawdown_type: Literal["eod", "intraday"] | None = Query(None),  # guard ON/OFF compare (§8 auto → intraday = ON)
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
        "low_risk": low_risk,
        "eval_mode": eval_mode,
        "drawdown_type": drawdown_type,
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
        low_risk=low_risk,
        eval_mode=eval_mode,
        drawdown_type=drawdown_type,
        data_source=data_source,
    )

    bus = st.bus
    jid, label = f"backtest-{rid}", f"Backtest #{rid} {symbol} {stage}"
    bus.job(jid, "backtest", label, "running", 0)

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
            bus.job(jid, "backtest", label, "done", 100)
        except Exception as e:  # never silent
            with st.sessionmaker() as s:
                r = s.get(BacktestRun, rid)
                if r is not None:
                    r.status, r.error = "failed", f"{type(e).__name__}: {e}"[:2000]
                    s.commit()
            bus.job(jid, "backtest", label, "failed", 100)
            bus.notify("error", "Backtest failed", f"#{rid}: {type(e).__name__}", "job")

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


@router.delete("/backtest/{rid}")
async def delete_run(
    rid: int, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    st = request.app.state
    run = db.get(BacktestRun, rid)
    if run is None:
        raise HTTPException(404, "no such backtest")
    if run.status in ("running", "queued"):
        raise HTTPException(409, "backtest is still running")
    n = db.execute(delete(BacktestTrade).where(BacktestTrade.run_id == rid)).rowcount  # type: ignore[attr-defined]
    db.delete(run)
    audit.record(db, st.clock, p.user.username, "backtest.delete", str(rid), {"trades": n, "kind": run.kind})
    db.commit()
    st.bus.publish("job.progress", {"id": f"backtest-{rid}", "kind": "backtest", "status": "deleted"})
    return {"deleted": rid}
