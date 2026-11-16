"""CONTI VWAP — price vs the session VWAP, built ONLY from docs/CONTI_RULES.md part C. PURE (no I/O, Decimal).

C1 VWAP anchored at 09:30 ET = Σ(typical price × volume) / Σ volume, typical = (high + low + close) / 3, from the app's
own 1-minute bar volume. C2 1-minute bars. C3 a close above VWAP = LONG, C4 a close below = SHORT. C5 exit when a
1-minute bar closes back through VWAP. [GAP] emergency stop `emergency_stop_pts` (Lucid needs a broker stop), window
09:30–15:30 (flat at 15:30), re-entry = the next close on the OTHER side after an exit (a reversal still waits for the
old position to be confirmed flat, D139, in the controller), [GAP] max losses a day (Lucid sizing divisor).
`replay_day(today, cfg, tick)` is deterministic on the stored bars: live = backtest.
"""

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


class VwapCfg(Protocol):
    @property
    def window_end(self) -> str: ...
    @property
    def emergency_stop_pts(self) -> Decimal: ...
    @property
    def far_target_pts(self) -> Decimal: ...
    @property
    def max_losses_per_day(self) -> int: ...


@dataclass
class VwapSignal:
    time: datetime
    direction: Direction
    entry: Decimal
    vwap: Decimal
    stop: Decimal
    take_profit: Decimal
    outcome: str | None = None  # CROSS | STOP | TIME | TP | OPEN
    exit_time: datetime | None = None
    exit_price: Decimal | None = None


def _at(d: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=ET)


def vwap_series(bars: Sequence[MBar]) -> list[Decimal | None]:
    """C1: the anchored VWAP after each bar (None until some volume has traded)."""
    pv, vol = Decimal(0), Decimal(0)
    out: list[Decimal | None] = []
    for b in bars:
        pv += (b.h + b.l + b.c) / 3 * b.v
        vol += b.v
        out.append(pv / vol if vol > 0 else None)
    return out


def replay_day(today: Sequence[MBar], cfg: VwapCfg, tick: Decimal) -> list[VwapSignal]:
    """Every entry and exit of the session so far (this session's 1-minute bars up to now)."""
    if not today:
        return []
    d = today[-1].close_time.astimezone(ET).date()
    o, end = _at(d, "09:30"), _at(d, cfg.window_end)
    bars = sorted((b for b in today if o < b.close_time <= _at(d, "16:00")), key=lambda b: b.close_time)
    vw = vwap_series(bars)
    out: list[VwapSignal] = []
    pos: VwapSignal | None = None
    last_side, losses = 0, 0
    for b, v in zip(bars, vw, strict=True):
        if pos is not None:
            s = pos.direction.sign
            hit = (b.l <= pos.stop) if s > 0 else (b.h >= pos.stop)
            won = (b.h >= pos.take_profit) if s > 0 else (b.l <= pos.take_profit)
            if hit:
                pos.outcome, pos.exit_price = "STOP", pos.stop
            elif won:
                pos.outcome, pos.exit_price = "TP", pos.take_profit
            elif b.close_time >= end:
                pos.outcome, pos.exit_price = "TIME", b.c
            elif v is not None and (b.c - v) * s < 0:
                pos.outcome, pos.exit_price = "CROSS", b.c  # C5 closed back through VWAP
            if pos.outcome != "OPEN":
                pos.exit_time = b.close_time
                assert pos.exit_price is not None
                losses += (pos.exit_price - pos.entry) * s < 0
                pos = None
        if pos is not None or v is None or b.close_time >= end or losses >= cfg.max_losses_per_day:
            continue
        side = 1 if b.c > v else -1 if b.c < v else 0
        if side == 0 or side == last_side:
            continue  # re-entry only on the other side after an exit
        dr = Direction.LONG if side > 0 else Direction.SHORT
        stop = round_to_tick(b.c - side * cfg.emergency_stop_pts, tick, away_from=b.c)
        tp = round_to_tick(b.c + side * cfg.far_target_pts, tick, toward=b.c)
        pos = VwapSignal(b.close_time, dr, b.c, v, stop, tp, "OPEN")
        out.append(pos)
        last_side = side
    return out
