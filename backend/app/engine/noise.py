"""D55 NOISE strategy — noise-area intraday momentum (Zarattini, Aziz & Barbon 2024, "Beat the Market"). PURE.

Verified on Databento MNQ 1-minute bars 2019–2026 (docs/results/tools/noise_area.py, held-out 2024–2026: 440 trades,
45.0% win, PF 1.33). This module is the live implementation of the same rules; tests/unit/test_noise_engine.py checks
it trade-for-trade against the research script.

Minute index k = minutes from 09:30 ET to the bar's OPEN (k = 0 is the 09:30–09:31 bar, k = 389 closes at 16:00).
Decisions happen on the CLOSE of the bar k where (k + 1 − 30) is a multiple of check_minutes (10:00, 11:00, …):
  σ_k      = mean over the previous `lookback_days` complete RTH sessions of |close_k / open_0930 − 1|
  upper_k  = max(open, prior RTH close) · (1 + σ_k);  lower_k = min(open, prior RTH close) · (1 − σ_k)
  flat:    close_k > upper_k → LONG;  close_k < lower_k → SHORT   (≤ max_entries_per_day entries)
  long:    close_k < max(upper_k, VWAP_k) → EXIT;   short: close_k > min(lower_k, VWAP_k) → EXIT
  16:00 bar → EXIT (flat).  |open / prior close − 1| > roll_gap_pct → no trades that day (roll / shock guard).
The broker holds a 1% emergency stop and a far safety target (NoisePlan); the trailing rule above does the exiting.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal

from app.clock import ET
from app.engine.trade_plan import Direction, round_to_tick

RTH_OPEN = time(9, 30)
RTH_BARS = 390


@dataclass(frozen=True)
class Session:
    """One RTH session of 1-minute bars: closes by minute index k (missing minutes simply absent)."""

    day: str  # YYYY-MM-DD (ET)
    open: Decimal  # open of the 09:30 bar
    closes: Mapping[int, Decimal]

    @property
    def last_close(self) -> Decimal | None:
        return self.closes.get(RTH_BARS - 1)


@dataclass(frozen=True)
class Bands:
    upper: Decimal
    lower: Decimal
    sigma: Decimal


@dataclass(frozen=True)
class NoiseAction:
    kind: str  # ENTER | EXIT | NONE
    direction: Direction | None = None
    reason: str = ""
    close: Decimal | None = None
    upper: Decimal | None = None
    lower: Decimal | None = None
    vwap: Decimal | None = None


@dataclass(frozen=True)
class NoisePlan:
    direction: Direction
    entry: Decimal
    stop: Decimal  # emergency stop (broker side)
    take_profit: Decimal  # far safety target (broker side)
    risk_pts: Decimal
    rr: Decimal


def minute_index(bar_close: datetime) -> int:
    """k of the bar that CLOSES at `bar_close` (any tz): minutes from 09:30 ET to its open."""
    et = bar_close.astimezone(ET)
    return et.hour * 60 + et.minute - 1 - (RTH_OPEN.hour * 60 + RTH_OPEN.minute)


def hhmm_to_k(hhmm: str) -> int:
    """'10:00' → k of the bar closing at 10:00 (= 29)."""
    h, m = (int(x) for x in hhmm.split(":"))
    return h * 60 + m - 1 - (RTH_OPEN.hour * 60 + RTH_OPEN.minute)


def is_check(k: int, check_minutes: int, first_check: str, last_check: str) -> bool:
    first = hhmm_to_k(first_check)
    return first <= k <= hhmm_to_k(last_check) and (k - first) % check_minutes == 0


def complete(s: Session, min_bars: int) -> bool:
    return len(s.closes) >= min_bars and 0 in s.closes


def sigma(history: Sequence[Session], k: int, lookback: int, min_days: int, min_bars: int) -> Decimal | None:
    """Mean |close_k / open − 1| over the last `lookback` complete sessions that have minute k. None if too few."""
    days = [s for s in history if complete(s, min_bars)][-lookback:]
    moves = [abs(s.closes[k] / s.open - 1) for s in days if k in s.closes]
    if len(days) < min_days or not moves:
        return None
    return sum(moves, Decimal(0)) / len(moves)


def bands(today_open: Decimal, prior_close: Decimal, sig: Decimal) -> Bands:
    return Bands(max(today_open, prior_close) * (1 + sig), min(today_open, prior_close) * (1 - sig), sig)


def roll_guard(today_open: Decimal, prior_close: Decimal, max_gap: Decimal) -> bool:
    """True = trading allowed (no contract-roll jump / extreme gap)."""
    return prior_close > 0 and abs(today_open / prior_close - 1) <= max_gap


def vwap(bars: Sequence[tuple[Decimal, Decimal, Decimal, Decimal]]) -> Decimal | None:
    """Session VWAP from (high, low, close, volume) bars since 09:30; None when the feed carries no volume."""
    pv = sum(((h + lo + c) / 3 * v for h, lo, c, v in bars), Decimal(0))
    vol = sum((v for *_, v in bars), Decimal(0))
    return pv / vol if vol > 0 else None


def decide(
    *,
    k: int,
    close: Decimal,
    b: Bands,
    vw: Decimal | None,
    position: Direction | None,
    entries_today: int,
    max_entries: int,
    allow_entry: bool,
) -> tuple[NoiseAction, ...]:
    """Decisions on a check bar (or the 16:00 bar), in order. An exit and a new entry can happen on the same check
    (e.g. a long below VWAP but still above the band exits and re-enters; below the lower band it reverses) — exactly
    like the research script. `allow_entry` = within the entry window and trading allowed today."""
    info = {"close": close, "upper": b.upper, "lower": b.lower, "vwap": vw}
    out: list[NoiseAction] = []
    if position is not None:
        if k >= RTH_BARS - 1:
            return (NoiseAction("EXIT", position, "NOISE_FLAT_1600", **info),)
        if position is Direction.LONG:
            trail = b.upper if vw is None else max(b.upper, vw)
            stop_out = close < trail
        else:
            trail = b.lower if vw is None else min(b.lower, vw)
            stop_out = close > trail
        if not stop_out:
            return (NoiseAction("NONE", position, "HOLD", **info),)
        out.append(NoiseAction("EXIT", position, "NOISE_TRAIL", **info))
    if not allow_entry or entries_today >= max_entries or k >= RTH_BARS - 1:
        return tuple(out) or (NoiseAction("NONE", None, "NO_ENTRY", **info),)
    if close > b.upper:
        out.append(NoiseAction("ENTER", Direction.LONG, "ABOVE_UPPER_BAND", **info))
    elif close < b.lower:
        out.append(NoiseAction("ENTER", Direction.SHORT, "BELOW_LOWER_BAND", **info))
    return tuple(out) or (NoiseAction("NONE", None, "INSIDE_NOISE_AREA", **info),)


def plan(direction: Direction, entry: Decimal, tick: Decimal, stop_pct: Decimal, tp_pct: Decimal) -> NoisePlan:
    """Broker bracket: emergency stop stop_pct away (rounded away from entry), safety target tp_pct away (toward)."""
    s = direction.sign
    stop = round_to_tick(entry * (1 - s * stop_pct), tick, away_from=entry)
    tp = round_to_tick(entry * (1 + s * tp_pct), tick, toward=entry)
    risk = (entry - stop) * s
    return NoisePlan(direction, entry, stop, tp, risk, ((tp - entry) * s / risk).quantize(Decimal("0.01")))
