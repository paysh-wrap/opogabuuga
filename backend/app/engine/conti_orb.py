"""CONTI ORB — opening range breakout, built ONLY from docs/CONTI_RULES.md part B. PURE (no I/O, Decimal).

B1 range = high / low of the 1-minute bars 09:30–10:00 ET. B2/B3 LONG only, on the first 1-minute CLOSE above the range
high ([GAP] 1-minute close; one trade a day; last entry 15:00). B4 stop = the range low. B5 take profit = rr × risk
(rr 1 or 2). B6 time exit at 15:30. B7 sizing (same dollars at risk) is the controller's Lucid fit.
`replay_day(today, cfg, tick)` is a deterministic function of the stored bars: live = backtest.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from app.engine.trade_plan import round_to_tick

ET = ZoneInfo("America/New_York")


class OrbCfg(Protocol):
    @property
    def range_end(self) -> str: ...
    @property
    def last_entry(self) -> str: ...
    @property
    def time_exit(self) -> str: ...
    @property
    def rr(self) -> Decimal: ...
    @property
    def max_trades_per_day(self) -> int: ...


@dataclass(frozen=True)
class MBar:
    close_time: datetime  # aware, a 1-minute bar (close_time − 1 min, close_time]
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    v: Decimal = Decimal(0)


@dataclass
class OrbSignal:
    time: datetime
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    risk_pts: Decimal
    rr: Decimal
    range_high: Decimal
    range_low: Decimal
    outcome: str | None = None  # TP | STOP | TIME | OPEN
    exit_time: datetime | None = None
    exit_price: Decimal | None = None


@dataclass
class OrbDay:
    range_high: Decimal | None
    range_low: Decimal | None
    skip: str | None
    signals: list[OrbSignal]


def _at(d: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=ET)


def follow_long(sig: OrbSignal, bars: Sequence[MBar], exit_at: datetime) -> None:
    """Outcome on later 1-minute bars (stop first when one bar touches both); B6 time exit at `exit_at`."""
    sig.outcome = "OPEN"
    for b in bars:
        if b.close_time <= sig.time:
            continue
        if b.l <= sig.stop:
            sig.outcome, sig.exit_time, sig.exit_price = "STOP", b.close_time, sig.stop
            return
        if b.h >= sig.take_profit:
            sig.outcome, sig.exit_time, sig.exit_price = "TP", b.close_time, sig.take_profit
            return
        if b.close_time >= exit_at:
            sig.outcome, sig.exit_time, sig.exit_price = "TIME", b.close_time, b.c
            return


def replay_day(today: Sequence[MBar], cfg: OrbCfg, tick: Decimal) -> OrbDay:
    """One session of CONTI ORB from this session's 1-minute bars up to now."""
    if not today:
        return OrbDay(None, None, "CORB_NO_BARS", [])
    d = today[-1].close_time.astimezone(ET).date()
    o, r1 = _at(d, "09:30"), _at(d, cfg.range_end)
    bars = sorted((b for b in today if o < b.close_time.astimezone(ET) <= _at(d, "16:00")), key=lambda b: b.close_time)
    rng = [b for b in bars if b.close_time <= r1]
    if not rng or rng[0].close_time.astimezone(ET) != _at(d, "09:31") or rng[-1].close_time.astimezone(ET) != r1:
        return OrbDay(None, None, "CORB_NO_RANGE", [])  # B1 needs the whole 09:30–10:00 range
    hi, lo = max(b.h for b in rng), min(b.l for b in rng)
    out = OrbDay(hi, lo, None, [])
    last, tx = _at(d, cfg.last_entry), _at(d, cfg.time_exit)
    free = r1
    for b in bars:
        if len(out.signals) >= cfg.max_trades_per_day or b.close_time <= free:
            continue
        if b.close_time > last:
            break
        if b.c > hi:  # B2 / B3: a close above the range high, long only
            stop = round_to_tick(lo, tick, away_from=b.c)  # B4
            risk = b.c - stop
            tp = round_to_tick(b.c + cfg.rr * risk, tick, toward=b.c)  # B5
            sig = OrbSignal(b.close_time, b.c, stop, tp, risk, (tp - b.c) / risk, hi, lo)
            follow_long(sig, bars, tx)
            out.signals.append(sig)
            if sig.exit_time is None:
                break
            free = sig.exit_time
    return out
