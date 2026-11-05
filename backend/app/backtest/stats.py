"""Backtest statistics + Monte Carlo (§16). PURE. Money in Decimal; Monte Carlo uses a seeded RNG (reproducible)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal

ZERO = Decimal(0)


@dataclass(frozen=True)
class Stats:
    trades: int
    wins: int
    win_rate: Decimal | None
    net: Decimal
    avg_r: Decimal | None
    profit_factor: Decimal | None
    max_drawdown: Decimal
    best_day: Decimal
    best_day_share: Decimal | None  # best day ÷ total profit (consistency check)
    days: int


def stats(trades: list[tuple[str, Decimal, Decimal | None]]) -> Stats:
    """trades = [(session iso date, pnl, net_r)] in time order."""
    n = len(trades)
    pnls = [p for _, p, _ in trades]
    wins = sum(1 for p in pnls if p > 0)
    gross_win = sum((p for p in pnls if p > 0), ZERO)
    gross_loss = -sum((p for p in pnls if p < 0), ZERO)
    rs = [r for _, _, r in trades if r is not None]
    eq = peak = dd = ZERO
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    by_day: dict[str, Decimal] = {}
    for d, p, _ in trades:
        by_day[d] = by_day.get(d, ZERO) + p
    net = sum(pnls, ZERO)
    best = max(by_day.values(), default=ZERO)
    q = Decimal("0.0001")
    return Stats(
        trades=n,
        wins=wins,
        win_rate=(Decimal(wins) / n).quantize(q) if n else None,
        net=net,
        avg_r=(sum(rs, ZERO) / len(rs)).quantize(q) if rs else None,
        profit_factor=(gross_win / gross_loss).quantize(q) if gross_loss > 0 else None,
        max_drawdown=dd,
        best_day=best,
        best_day_share=(best / net).quantize(q) if net > 0 else None,
        days=len(by_day),
    )


@dataclass(frozen=True)
class MonteCarlo:
    runs: int
    pass_rate: Decimal  # reached target before the drawdown limit
    fail_rate: Decimal  # hit the drawdown limit first
    median_trades_to_pass: int | None


def monte_carlo(
    day_pnls: list[Decimal], target: Decimal, max_loss: Decimal, runs: int = 5000, max_days: int = 60, seed: int = 7
) -> MonteCarlo:
    """Resample whole trading DAYS (keeps intraday dependence) with replacement. EOD trailing drawdown: the floor
    trails the highest end-of-day balance by `max_loss`. Pass = cumulative profit ≥ target before the floor is hit."""
    if not day_pnls:
        return MonteCarlo(runs, ZERO, ZERO, None)
    rng = random.Random(seed)  # noqa: S311 (simulation, not crypto)
    passed = failed = 0
    days_to_pass: list[int] = []
    for _ in range(runs):
        bal = peak = ZERO
        for d in range(1, max_days + 1):
            bal += rng.choice(day_pnls)
            if bal <= peak - max_loss:
                failed += 1
                break
            peak = max(peak, bal)
            if bal >= target:
                passed += 1
                days_to_pass.append(d)
                break
    days_to_pass.sort()
    q = Decimal("0.0001")
    return MonteCarlo(
        runs,
        (Decimal(passed) / runs).quantize(q),
        (Decimal(failed) / runs).quantize(q),
        days_to_pass[len(days_to_pass) // 2] if days_to_pass else None,
    )
