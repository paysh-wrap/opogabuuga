"""Run backtests fast: one process per CSV file (e.g. one per month), in parallel.

Usage (from backend/):
  ../.venv/bin/python scripts/backtest.py --symbol MGC --bias NEUTRAL \
      --plan ../config/rules/lucid_flex_25k.yaml ../data/gold/csv/xauusd_2026-*.csv

Each file is an independent run (fresh $25K account), so results are per file plus a combined summary.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def _one(args: tuple[str, str, str, str, bool, bool]) -> dict[str, Any]:
    path, symbol, bias, plan, one_to_one, scalp = args
    logging.disable(logging.CRITICAL)
    from app.backtest.data import load_csv
    from app.backtest.runner import BacktestConfig, run_backtest

    bars = load_csv(Path(path).read_text())
    src = "spot" if any(x in Path(path).name.lower() for x in ("xauusd", "xau", "spot")) else "futures"
    cfg = BacktestConfig(symbol=symbol, bias=bias, one_to_one=one_to_one, scalp=scalp, data_source=src)
    r = run_backtest(bars, cfg, Path(plan))
    return {
        "file": Path(path).name,
        "sessions": r.sessions,
        "trades": r.trades,
        "signals": r.signals,
        "skips": r.skips,
        "rejects": r.rejects,
        "balance": r.final_balance,
        "assumptions": r.assumptions,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--symbol", default="MGC")
    ap.add_argument("--bias", default="NEUTRAL")
    ap.add_argument("--plan", default="../config/rules/lucid_flex_25k.yaml")
    ap.add_argument("--one-to-one", action="store_true")
    ap.add_argument("--scalp", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    from app.backtest.stats import monte_carlo, stats
    from app.clock import session_date

    jobs = [(c, a.symbol, a.bias, a.plan, a.one_to_one, a.scalp) for c in a.csv]
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        runs = list(ex.map(_one, jobs))
    rows = []
    skips: Counter[str] = Counter()
    sig: Counter[str] = Counter()
    for run in runs:
        skips.update(run["skips"])
        sig.update(run["signals"])
        for t in run["trades"]:
            if t["pnl"] is None:
                continue
            dt = datetime.fromisoformat(t["opened_at"])
            dt = dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            rows.append(
                (
                    session_date(dt).isoformat(),
                    Decimal(t["pnl"]),
                    Decimal(t["net_r"]) if t["net_r"] else None,
                    dt.astimezone(ET).hour,
                )
            )
    rows.sort()
    st = stats([(d, p, r) for d, p, r, _ in rows])
    day: dict[str, Decimal] = defaultdict(Decimal)
    hour: dict[int, list[Any]] = defaultdict(lambda: [0, 0, Decimal(0)])
    for d, p, _, h in rows:
        day[d] += p
        hour[h][0] += 1
        hour[h][1] += int(p > 0)
        hour[h][2] += p
    mc = monte_carlo(list(day.values()), Decimal(1250), Decimal(1000)) if day else None
    print(
        json.dumps(
            {
                "per_file": [{k: (len(v) if k == "trades" else v) for k, v in r.items()} for r in runs],
                "stats": {k: str(v) for k, v in st.__dict__.items()},
                "monte_carlo": {k: str(v) for k, v in mc.__dict__.items()} if mc else None,
                "signals": dict(sig),
                "skips": dict(skips.most_common()),
                "by_hour_et": {h: {"n": v[0], "wins": v[1], "net": str(v[2])} for h, v in sorted(hour.items())},
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
