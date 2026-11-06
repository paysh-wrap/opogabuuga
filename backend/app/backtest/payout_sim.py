"""Backtest payout simulation + income Monte Carlo (§16.4, §16.5). PURE: no I/O, Decimal money, seeded RNG.

A backtest's per-session P&L is replayed through a FUNDED account with the SAME payout rule as live
(`phases.payout_plan.plan_payout`): EOD trailing MLL that locks at `lock_trigger`, a payout check at the end of
every 5th session (the Friday check), payouts never leave the balance under the buffer. An MLL breach ends the
account (no further income). The Monte Carlo block-bootstraps whole sessions into 12-month paths.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from app.phases.payout_plan import plan_payout

ZERO = Decimal(0)
CENT = Decimal("0.01")
Q4 = Decimal("0.0001")
SESSIONS_PER_WEEK = 5
SESSIONS_PER_YEAR = 252


@dataclass(frozen=True)
class FundedSim:
    start_balance: Decimal
    max_loss: Decimal  # EOD trailing distance
    lock_trigger: Decimal  # EOD peak at which the MLL locks
    lock_level: Decimal
    sweep_above: Decimal
    skim_mode: str
    buffer: Decimal
    min_request: Decimal
    split: Decimal
    max_first: Decimal | None = None
    max_next: Decimal | None = None
    max_pct_of_profit: Decimal | None = None


@dataclass(frozen=True)
class Week:
    week: int
    profit: Decimal
    balance: Decimal
    kind: str | None
    amount: Decimal
    net: Decimal
    reason: str


@dataclass(frozen=True)
class PayoutSim:
    weeks: list[Week]
    total_gross: Decimal
    total_net: Decimal
    breached: bool


def simulate_payouts(day_pnls: list[Decimal], c: FundedSim) -> PayoutSim:
    bal = peak = c.start_balance
    mll = c.start_balance - c.max_loss
    locked = False
    weeks: list[Week] = []
    week_profit = cycle = ZERO
    paid = 0
    gross = net = ZERO
    for i, p in enumerate(day_pnls, start=1):
        bal += p
        week_profit += p
        cycle += p
        if bal <= mll:
            return PayoutSim(weeks, gross, net, True)
        if not locked:  # EOD trailing, then lock
            peak = max(peak, bal)
            mll = max(mll, peak - c.max_loss)
            if peak >= c.lock_trigger:
                locked, mll = True, c.lock_level
        if i % SESSIONS_PER_WEEK == 0:
            pp = plan_payout(
                balance=bal,
                week_profit=week_profit,
                cycle_profit=cycle,
                locked=locked,
                sweep_above=c.sweep_above,
                skim_mode=c.skim_mode,
                buffer=c.buffer,
                min_request=c.min_request,
                min_cycle_profit=ZERO,
                split=c.split,
                payout_no=paid + 1,
                max_first=c.max_first,
                max_next=c.max_next,
                max_pct_of_profit=c.max_pct_of_profit,
            )
            if pp.kind is not None:
                paid += 1
                cycle = ZERO
            bal -= pp.amount
            gross += pp.amount
            net += pp.net
            weeks.append(Week(i // SESSIONS_PER_WEEK, week_profit, bal + pp.amount, pp.kind, pp.amount, pp.net, pp.reason))
            week_profit = ZERO
    return PayoutSim(weeks, gross, net, False)


@dataclass(frozen=True)
class IncomeMC:
    runs: int
    sessions: int
    by_accounts: dict[int, dict[str, Decimal]]  # N → median_net, p_floor, p_target, p_breach


def income_monte_carlo(
    day_pnls: list[Decimal],
    c: FundedSim,
    floor: Decimal,
    target: Decimal,
    runs: int = 10_000,
    sessions: int = SESSIONS_PER_YEAR,
    block: int = SESSIONS_PER_WEEK,
    seed: int = 11,
) -> IncomeMC:
    """Block-bootstrap (blocks of `block` consecutive sessions) 12-month paths. N accounts take the same signals, so
    one path's net income is multiplied by N (fully correlated — the §12 warning). P(≥floor) / P(≥target) per N."""
    if not day_pnls:
        return IncomeMC(runs, sessions, {})
    rng = random.Random(seed)  # noqa: S311 (simulation, not crypto)
    starts = range(max(len(day_pnls) - block + 1, 1))
    nets: list[Decimal] = []
    breaches = 0
    for _ in range(runs):
        path: list[Decimal] = []
        while len(path) < sessions:
            s = rng.choice(starts)
            path.extend(day_pnls[s : s + block])
        r = simulate_payouts(path[:sessions], c)
        nets.append(r.total_net)
        breaches += r.breached
    nets.sort()
    out: dict[int, dict[str, Decimal]] = {}
    for n in range(1, 6):
        out[n] = {
            "median_net": (nets[len(nets) // 2] * n).quantize(CENT, rounding=ROUND_DOWN),
            "p_floor": (Decimal(sum(1 for x in nets if x * n >= floor)) / runs).quantize(Q4),
            "p_target": (Decimal(sum(1 for x in nets if x * n >= target)) / runs).quantize(Q4),
            "p_breach": (Decimal(breaches) / runs).quantize(Q4),
        }
    return IncomeMC(runs, sessions, out)
