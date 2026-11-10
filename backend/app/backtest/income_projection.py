"""D59 projected income from FUNDED Lucid accounts (dashboard). PURE: no I/O except reading the shipped research file.

Replays the MAIN strategy's real per-trade results (app/backtest/data/main_strategy_5y.csv: D58 NOISE + CAUSAL
afternoon fade, session 14; the old hindsight set is main_strategy_5y_hindsight.csv; Databento MNQ 2021-11 → 2026-10,
1 micro, net of costs) through a funded account with the plan's OWN funded rules
(RulesConfig.funded: EOD trailing MLL + lock, soft DLL, payout buffer / minimum / cycle profit / caps / consistency /
max payouts / split, LucidFlex 50%-of-profit + profitable-days + MLL lock on payout). Rolling starts every `step`
sessions; each start is followed for `horizon` sessions or until bust / max payouts. A payout is requested every
`cadence` sessions (5 = weekly, 10 = bi-weekly). All accounts take the same trades → N accounts = N × one account
(they also bust together). Projection, NOT a promise: research data, open-trade drawdown and news not modeled.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from statistics import median

from app.config import RulesConfig

ZERO = Decimal(0)
CENT = Decimal("0.01")
DATA = Path(__file__).parent / "data" / "main_strategy_5y.csv"


@dataclass(frozen=True)
class FundedRulesView:
    start: Decimal
    mll: Decimal
    lock_trigger: Decimal
    lock_level: Decimal
    dll: Decimal | None
    split: Decimal
    buffer: Decimal
    min_request: Decimal
    min_cycle_profit: Decimal
    max_first: Decimal | None
    max_next: Decimal | None
    max_pct_of_profit: Decimal | None
    min_profitable_days: int
    min_day_profit: Decimal
    max_payouts: int | None
    consistency_pct: Decimal | None
    lock_mll_on_payout: bool


def rules_view(r: RulesConfig) -> FundedRulesView:
    f, p = r.funded, r.funded.payout
    return FundedRulesView(
        r.account_size,
        f.max_loss_limit,
        f.lock_trigger,
        f.lock_level,
        f.daily_loss_limit,
        p.split,
        p.buffer,
        p.min_request,
        p.min_cycle_profit,
        p.max_first,
        p.max_next,
        p.max_pct_of_profit,
        p.min_profitable_days,
        p.min_day_profit,
        p.max_payouts,
        f.consistency_max_day_pct,
        p.lock_mll_on_payout,
    )


@dataclass(frozen=True)
class Path1:
    paid: Decimal  # to you, after the split
    payouts: tuple[tuple[int, Decimal], ...]  # (session index from the start, amount to you)
    status: str  # BUST | MAX_PAYOUTS | OPEN
    sessions: int


def payout_amount(r: FundedRulesView, balance: Decimal, cycle: Sequence[Decimal], n_paid: int) -> Decimal:
    """Gross amount the firm would pay now (0 = not eligible)."""
    cp = sum(cycle, ZERO)
    if cp < r.min_cycle_profit or cp <= 0:
        return ZERO
    if r.consistency_pct is not None and max(cycle) > r.consistency_pct / 100 * cp:
        return ZERO
    if r.min_profitable_days and sum(1 for x in cycle if x >= r.min_day_profit) < r.min_profitable_days:
        return ZERO
    amt = balance - r.buffer
    if r.max_pct_of_profit is not None:
        amt = min(amt, r.max_pct_of_profit * cp)
    cap = r.max_first if n_paid == 0 else r.max_next
    if cap is not None:
        amt = min(amt, cap)
    return amt.quantize(CENT) if amt >= r.min_request else ZERO


def size_for(base: int, cushion: Decimal, grow_per: Decimal | None, max_micros: int) -> int:
    """D60 account growth: base micros, +1 for every `grow_per` dollars of cushion (balance − trailing MLL floor) beyond
    the first `grow_per`; never above max_micros; None = fixed size. Shrinks again as the cushion shrinks."""
    if grow_per is None or grow_per <= 0:
        return base
    extra = int(cushion // grow_per) - 1
    return max(base, min(max_micros, base + max(0, extra)))


def funded_path(
    days: Sequence[Sequence[Decimal]],
    r: FundedRulesView,
    qty: int,
    cadence: int,
    grow_per: Decimal | None = None,
    max_micros: int = 5,
    take: Decimal = Decimal(1),
    brake: tuple[Decimal, int] | None = None,
) -> Path1:
    bal = peak = r.start
    floor = r.start - r.mll
    cycle: list[Decimal] = []
    paid = ZERO
    pays: list[tuple[int, Decimal]] = []
    base = qty
    for n, trades in enumerate(days):
        day = ZERO
        qty = size_for(base, bal - floor, grow_per, max_micros)  # sized at the start of each session
        if brake is not None and bal - floor < brake[0] * r.mll:  # D63 drawdown brake: cushion < x·MLL → brake size
            qty = min(qty, brake[1])
        for p in trades:
            p *= qty
            if r.dll is not None and day + p <= -r.dll:
                p = -r.dll - day  # soft DLL: the day stops at −DLL
            bal += p
            day += p
            if bal <= floor:
                return Path1(paid, tuple(pays), "BUST", n + 1)
            if r.dll is not None and day <= -r.dll:
                break
        if trades:
            cycle.append(day)
        peak = max(peak, bal)
        floor = r.lock_level if peak >= r.lock_trigger else max(floor, peak - r.mll)
        if (n + 1) % cadence == 0 and (r.max_payouts is None or len(pays) < r.max_payouts):
            amt = payout_amount(r, bal, cycle, len(pays))
            if take < 1 and amt > 0:  # D61: withdraw only part, leave the rest to compound (still ≥ min request)
                amt = (amt * take).quantize(CENT)
                amt = amt if amt >= r.min_request else ZERO
            if amt > 0:
                bal -= amt
                mine = (amt * r.split).quantize(CENT)
                paid += mine
                pays.append((n + 1, mine))
                cycle = []
                if r.lock_mll_on_payout:
                    floor = max(floor, r.lock_level)
        if r.max_payouts is not None and len(pays) >= r.max_payouts:
            return Path1(paid, tuple(pays), "MAX_PAYOUTS", n + 1)
    return Path1(paid, tuple(pays), "OPEN", len(days))


@dataclass(frozen=True)
class EvalRulesView:
    start: Decimal
    target: Decimal
    mll: Decimal
    lock_trigger: Decimal
    lock_level: Decimal
    dll: Decimal | None
    consistency_pct: Decimal | None
    min_profitable_days: int


def eval_view(r: RulesConfig) -> EvalRulesView:
    e = r.eval
    return EvalRulesView(
        r.account_size,
        e.profit_target,
        e.max_loss_limit,
        e.lock_trigger,
        e.lock_level,
        e.daily_loss_limit,
        e.consistency_max_day_pct,
        e.min_profitable_days,
    )


def eval_path(
    days: Sequence[Sequence[Decimal]],
    r: EvalRulesView,
    qty: int,
    grow_per: Decimal | None = None,
    max_micros: int = 5,
    horizon: int = 120,
    brake: tuple[Decimal, int] | None = None,
) -> tuple[str, int]:
    """("PASS" | "BUST" | "OPEN", sessions) for one evaluation started on days[0]."""
    bal = peak = r.start
    floor = r.start - r.mll
    pos: list[Decimal] = []
    for n, trades in enumerate(days[:horizon]):
        day = ZERO
        q = size_for(qty, bal - floor, grow_per, max_micros)
        if brake is not None and bal - floor < brake[0] * r.mll:
            q = min(q, brake[1])
        for p in trades:
            p *= q
            if r.dll is not None and day + p <= -r.dll:
                p = -r.dll - day
            bal += p
            day += p
            if bal <= floor:
                return "BUST", n + 1
            if r.dll is not None and day <= -r.dll:
                break
        if trades:
            pos.append(day)
        peak = max(peak, bal)
        floor = r.lock_level if peak >= r.lock_trigger else max(floor, peak - r.mll)
        prof = bal - r.start
        target_hit = prof >= r.target and sum(1 for x in pos if x > 0) >= r.min_profitable_days
        consistent = r.consistency_pct is None or max(pos, default=ZERO) <= r.consistency_pct / 100 * prof
        if target_hit and consistent:
            return "PASS", n + 1
    return "OPEN", min(horizon, len(days))


@lru_cache(maxsize=1)
def research_days() -> tuple[tuple[str, ...], tuple[tuple[Decimal, ...], ...]]:
    """Business days of the research period with that day's trade P&Ls (1 micro), zero-trade days included."""
    by: dict[str, list[Decimal]] = {}
    with DATA.open() as fh:
        rows = csv.DictReader(line for line in fh if not line.startswith("#"))
        for row in rows:
            by.setdefault(row["d"], []).append(Decimal(row["pnl"]))
    first, last = date.fromisoformat(min(by)), date.fromisoformat(max(by))
    names, out, d = [], [], first
    while d <= last:
        if d.weekday() < 5:
            names.append(d.isoformat())
            out.append(tuple(by.get(d.isoformat(), ())))
        d += timedelta(days=1)
    return tuple(names), tuple(out)


@dataclass(frozen=True)
class Projection:
    accounts: int
    micros: int
    cadence_sessions: int
    starts: int
    horizon_sessions: int
    year_mean: Decimal  # all accounts, first `horizon` sessions
    year_median: Decimal
    year_p25: Decimal
    year_p75: Decimal
    week_mean: Decimal
    per_paycheck_mean: Decimal  # mean amount per payout cadence (all accounts)
    any_payout_pct: Decimal
    bust_pct: Decimal
    max_payouts_pct: Decimal
    median_sessions_to_first: int | None
    max_possible_year: Decimal


def _pct(x: float) -> Decimal:
    return Decimal(str(round(x * 100, 1)))


def _q(xs: list[Decimal], q: float) -> Decimal:
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * (len(s) - 1) + 0.5))]


def project(
    r: FundedRulesView,
    *,
    accounts: int,
    micros: int,
    cadence: int = 10,
    horizon: int = 260,
    step: int = 2,
    days: Sequence[Sequence[Decimal]] | None = None,
    grow_per: Decimal | None = None,
    max_micros: int = 5,
    take: Decimal = Decimal(1),
    brake: tuple[Decimal, int] | None = None,
) -> Projection:
    if accounts < 1 or micros < 1 or cadence < 1 or horizon < cadence:
        raise ValueError("accounts, micros ≥ 1 and horizon ≥ cadence")
    all_days = list(days) if days is not None else list(research_days()[1])
    starts = range(0, max(1, len(all_days) - horizon), step)
    paths = [
        funded_path(all_days[i : i + horizon], r, micros, cadence, grow_per, max_micros, take, brake) for i in starts
    ]
    paid = [p.paid * accounts for p in paths]
    firsts = [p.payouts[0][0] for p in paths if p.payouts]
    n = len(paths)
    weeks = Decimal(horizon) / 5
    caps = [r.max_first or ZERO] + [r.max_next or ZERO] * ((r.max_payouts or 1) - 1)
    mean = sum(paid, ZERO) / n
    return Projection(
        accounts,
        micros,
        cadence,
        n,
        horizon,
        mean.quantize(CENT),
        Decimal(str(median(paid))).quantize(CENT),
        _q(paid, 0.25),
        _q(paid, 0.75),
        (mean / weeks).quantize(CENT),
        (mean / (Decimal(horizon) / cadence)).quantize(CENT),
        _pct(sum(1 for p in paths if p.payouts) / n),
        _pct(sum(1 for p in paths if p.status == "BUST") / n),
        _pct(sum(1 for p in paths if p.status == "MAX_PAYOUTS") / n),
        int(median(firsts)) if firsts else None,
        (sum(caps, ZERO) * r.split * accounts).quantize(CENT),
    )
