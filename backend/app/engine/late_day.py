"""LATE-DAY MOMENTUM (D166) — the 3rd edge of the Lucid Pro fast pass. PURE (no I/O, Decimal, closed bars only).

Source: docs/results/new_edge (research.py `lastmom_day`, candidate lastmom239), MNQ RTH 1-minute bars 2021-10..2026-10.
  trend  = close of the bar closing at `ref_close` (13:30) - the 09:30 session open; |trend| must be >= min_range_atr x
           the mean (high - low) of the previous `atr_days` RTH sessions (>= min_history_days of them)
  entry  = decided on the bar closing at `entry_at` (15:00), WITH the trend sign (up -> LONG), at that close
  stop   = stop_pts hard stop; flat at the bar closing `flat_at` (15:59); no target in the study (a far safety target
           of target_r x the stop is added only because every bracket needs one)
No lookahead: only bars whose close_time <= `at` are read, so the signal on `at` cannot change when later bars arrive.
`replay` is deterministic on the stored bars (live = backtest). UNVERIFIED (held-out 2024+ PF 1.12); sizing and every
Lucid check live elsewhere (risk/fast_pass.py, the controller) and only ever shrink or skip."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction, round_to_tick

ET = ZoneInfo("America/New_York")
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)


class LateDayParams(Protocol):
    @property
    def ref_close(self) -> str: ...
    @property
    def entry_at(self) -> str: ...
    @property
    def flat_at(self) -> str: ...
    @property
    def min_range_atr(self) -> Decimal: ...
    @property
    def atr_days(self) -> int: ...
    @property
    def min_history_days(self) -> int: ...
    @property
    def stop_pts(self) -> Decimal: ...
    @property
    def target_r(self) -> Decimal: ...


@dataclass(frozen=True)
class LateDaySignal:
    time: datetime
    direction: Direction
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    risk_pts: Decimal
    rr: Decimal
    trend_pts: Decimal
    atr: Decimal


def _hm(hhmm: str) -> time:
    h, m = hhmm.split(":")
    return time(int(h), int(m))


def _tod(b: MBar) -> time:
    return b.close_time.astimezone(ET).time()


def _rth(bars: Sequence[MBar]) -> list[MBar]:
    """Bars of the cash session: closing in (09:30, 16:00]."""
    return [b for b in bars if RTH_OPEN < _tod(b) <= RTH_CLOSE]


def session_ranges(history: Sequence[MBar], before: date) -> list[Decimal]:
    """(high - low) of each RTH session strictly before `before`, oldest first."""
    by_day: dict[date, list[MBar]] = {}
    for b in _rth(history):
        d = b.close_time.astimezone(ET).date()
        if d < before:
            by_day.setdefault(d, []).append(b)
    return [max(x.h for x in v) - min(x.l for x in v) for _, v in sorted(by_day.items())]


def average_range(ranges: Sequence[Decimal], atr_days: int, min_days: int) -> Decimal | None:
    """Mean of the last `atr_days` session ranges; None while fewer than `min_days` sessions are stored."""
    if len(ranges) < min_days:
        return None
    last = ranges[-atr_days:]
    return sum(last, Decimal(0)) / len(last)


def is_flat_time(at: datetime, cfg: LateDayParams) -> bool:
    """True on the bar closing at `flat_at` (the app exit; the broker stop covers everything before)."""
    return at.astimezone(ET).time() == _hm(cfg.flat_at)


def decide(
    history: Sequence[MBar], today: Sequence[MBar], cfg: LateDayParams, tick: Decimal, at: datetime
) -> LateDaySignal | None:
    """The entry signal on the bar closing at `at` (None unless `at` is the entry bar). Closed bars only."""
    if at.astimezone(ET).time() != _hm(cfg.entry_at):
        return None
    day = at.astimezone(ET).date()
    bars = [b for b in _rth(today) if b.close_time <= at and b.close_time.astimezone(ET).date() == day]
    if not bars or bars[-1].close_time != at:
        return None  # the entry bar itself must be stored
    ref = next((b for b in bars if _tod(b) == _hm(cfg.ref_close)), None)
    opening = next((b for b in bars if b.close_time == min(x.close_time for x in bars)), None)
    if ref is None or opening is None or _tod(opening) != time(9, 31):
        return None  # no 09:30 open or no reference bar stored: no trade
    atr = average_range(session_ranges(history, day), cfg.atr_days, cfg.min_history_days)
    if atr is None:
        return None
    trend = ref.c - opening.o
    if trend == 0 or abs(trend) < cfg.min_range_atr * atr:
        return None
    d = Direction.LONG if trend > 0 else Direction.SHORT
    entry = bars[-1].c
    stop = round_to_tick(entry - d.sign * cfg.stop_pts, tick, away_from=entry)
    risk = (entry - stop) * d.sign
    tp = round_to_tick(entry + d.sign * cfg.target_r * risk, tick, toward=entry)
    return LateDaySignal(at, d, entry, stop, tp, risk, (tp - entry) * d.sign / risk, trend, atr)
