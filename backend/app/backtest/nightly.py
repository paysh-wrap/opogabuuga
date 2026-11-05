"""Nightly self-review (§17): after the session, re-run the last N sessions of recorded 1-minute TradingView bars
through the live pipeline per enabled market, store the result + Lab suggestions. The Lab page shows the trend."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtest.runner import BacktestConfig, run_backtest
from app.indicators.bars import Bar
from app.models import BacktestRun, BiasDecision
from app.models import Bar as BarRow


def recorded_bars(s: Session, symbol: str, since: datetime) -> list[Bar]:
    rows = s.execute(
        select(BarRow)
        .where(BarRow.symbol == symbol, BarRow.tf == "1", BarRow.close_time >= since)
        .order_by(BarRow.close_time)
    ).scalars()
    out = []
    for r in rows:
        close_ms = int(r.close_time.timestamp() * 1000)
        out.append(Bar(close_ms - 60_000, close_ms, r.o, r.h, r.l, r.c, r.v or Decimal(0)))
    return out


async def nightly(app: Any, s: Session, now: datetime, days: int = 30) -> list[int]:
    """Returns the ids of the runs created. Uses the bias actually recorded each day (no assumptions)."""
    from app.api.backtest import metrics

    st = app.state
    r = st.rules.rules
    rec = {b.session_date.isoformat(): b.mapped for b in s.execute(select(BiasDecision)).scalars() if b.version != "bt"}
    made = []
    for sym, inst in r.instruments.items():
        if not inst.enabled:
            continue
        bars = recorded_bars(s, sym, now - timedelta(days=days))
        if len(bars) < 120:
            continue
        cfg = BacktestConfig(
            symbol=sym,
            bias="recorded",
            recorded_bias=rec,
            one_to_one=r.one_to_one_mode.enabled,
            scalp=r.scalp_mode.enabled,
        )
        run = BacktestRun(
            kind="NIGHTLY",
            status="running",
            cache_key=f"nightly-{sym}-{now.date()}",
            params={
                "symbol": sym,
                "stage": "EVAL",
                "bias": "recorded",
                "one_to_one": cfg.one_to_one,
                "scalp": cfg.scalp,
                "eval_mode": False,
                "nightly": True,
            },
        )
        s.add(run)
        s.commit()
        try:
            res = await asyncio.to_thread(run_backtest, bars, cfg, st.settings.rules_path)
            m = metrics(res.trades, r, "EVAL")
            m |= {"signals": res.signals, "skips": res.skips, "sessions": res.sessions, "assumptions": res.assumptions}
            run.status, run.metrics, run.progress = "done", m, 100
        except Exception as e:  # never silent
            run.status, run.error = "failed", f"{type(e).__name__}: {e}"[:2000]
            st.controller.notify("error", "Nightly self-review failed", f"{sym}: {type(e).__name__}")
        s.commit()
        made.append(run.id)
    return made
