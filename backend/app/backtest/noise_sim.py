"""D55: bar-by-bar simulation of the NOISE strategy with the LIVE decision code (app/engine/noise.py). Pure.

Same fills as the research script (docs/results/tools/noise_area.py): decision on a check bar's close, fill at the
next bar's open ± 1 tick; emergency stop on every bar (stop first, a gap through it fills at the open ± 1 tick); flat
on the 16:00 bar's close ± 1 tick. Used by the parity test and available to backtests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.config import NoiseCfg
from app.engine.noise import RTH_BARS, Session, bands, decide, is_check, plan, roll_guard, sigma
from app.engine.trade_plan import Direction


@dataclass(frozen=True)
class Bar1m:
    k: int  # minute index (0 = 09:30 bar)
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    v: Decimal


@dataclass(frozen=True)
class SimTrade:
    day: str
    direction: Direction
    entry: Decimal
    exit: Decimal
    reason: str
    pnl: Decimal  # $ net per contract


def simulate(
    days: Sequence[tuple[str, Sequence[Bar1m]]],
    cfg: NoiseCfg,
    *,
    tick: Decimal,
    point_value: Decimal,
    fee_rt: Decimal,
) -> list[SimTrade]:
    out: list[SimTrade] = []
    history: list[Session] = []
    for day, bars in days:
        by_k = {b.k: b for b in bars if 0 <= b.k < RTH_BARS}
        if 0 not in by_k:
            continue
        sess = Session(day, by_k[0].o, {k: b.c for k, b in by_k.items()})
        prior = history[-1].last_close if history else None
        tradable = prior is not None and roll_guard(sess.open, prior, cfg.roll_gap_pct)
        pos: Direction | None = None
        entry = stop = Decimal(0)
        pending: Direction | None = None
        entries = 0
        pv = vol = Decimal(0)

        def close_trade(px: Decimal, why: str, d: str, side: Direction, entry_px: Decimal) -> None:
            out.append(SimTrade(d, side, entry_px, px, why, (px - entry_px) * side.sign * point_value - fee_rt))

        for k in range(RTH_BARS):
            b = by_k.get(k)
            if b is None:
                continue
            if pending is not None and pos is None:
                pos, pending = pending, None
                entry = b.o + pos.sign * tick
                stop = plan(pos, entry, tick, cfg.emergency_stop_pct, cfg.take_profit_pct).stop
            pv += (b.h + b.l + b.c) / 3 * b.v
            vol += b.v
            if pos is not None and (
                (pos is Direction.LONG and b.l <= stop) or (pos is Direction.SHORT and b.h >= stop)
            ):
                px = min(stop, b.o) if pos is Direction.LONG else max(stop, b.o)
                close_trade(px - pos.sign * tick, "EMERGENCY_STOP", day, pos, entry)
                pos = None
            if not tradable:
                continue
            check = is_check(k, cfg.check_minutes, cfg.first_check, cfg.last_check)
            if not check and not (k == RTH_BARS - 1 and pos is not None):
                continue
            sig = sigma(history, k, cfg.lookback_days, cfg.min_history_days, cfg.min_bars_per_day)
            if sig is None:
                if pos is not None and k == RTH_BARS - 1:
                    close_trade(b.c - pos.sign * tick, "NOISE_FLAT_1600", day, pos, entry)
                    pos = None
                continue
            assert prior is not None
            bd = bands(sess.open, prior, sig)
            vw = pv / vol if vol > 0 else None
            for a in decide(
                k=k,
                close=b.c,
                b=bd,
                vw=vw,
                position=pos,
                entries_today=entries,
                max_entries=cfg.max_entries_per_day,
                allow_entry=check,
            ):
                if a.kind == "EXIT" and pos is not None:
                    if a.reason == "NOISE_FLAT_1600":
                        close_trade(b.c - pos.sign * tick, a.reason, day, pos, entry)
                        pos = None
                    else:
                        nxt = by_k.get(k + 1)
                        close_trade((nxt.o if nxt is not None else b.c) - pos.sign * tick, a.reason, day, pos, entry)
                        pos = None
                elif a.kind == "ENTER" and a.direction is not None:
                    pending, entries = a.direction, entries + 1
        if pos is not None:  # data ended before 16:00 → flat at the last bar (never carried overnight)
            last = by_k[max(by_k)]
            close_trade(last.c - pos.sign * tick, "NOISE_FLAT_1600", day, pos, entry)
            pos = None
        history.append(sess)
    return out
