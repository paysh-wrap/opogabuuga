"""GALA PRICE ACTION — built ONLY from the Gala Trades rule sheet (docs/GALA_RULES.md). PURE (no I/O, Decimal).

Rule ids (A2, C5, …) refer to docs/GALA_RULES.md. Closed 1-minute RTH bars only, no lookahead.

`replay_day(history, today, cfg, tick)` is a deterministic function of the stored bars: live, paper and backtest call
it on every 1-minute close and get the same answer.

  plan (before the open, A1): hourly RTH candles of the prior sessions, the overnight gap = ONE candle (A7).
      trend (A2) from the last two hourly swing highs and lows: HH+HL = LONG, LH+LL = SHORT, else no trade (A3).
      levels (A4) = the OPEN of the hourly candle where the colour changes at a body pivot (`pivot_lookback`
      candles each side); a later candle whose body pierces a level deletes it (A6).
      setup (A8) from today's open: LONG + closer to the level above → break-and-retest of it, else bounce off the
      level below; SHORT mirrors (break-and-retest of the level below, else rejection at the level above).
  entries (5-minute RTH candles, C1): skip the first `skip_first_minutes` (B1); entry candle closes inside the window
      (B2). Entry candle must pass the perfect-entry test (C2: wick through the level ≤ max_wick_through_pts, body on
      the right side) and not be a hammer (C4: wick ≥ hammer_wick_body_mult × body).
      break-and-retest (C5): a 5-min close beyond the level, then a retest candle; a close back through cancels the
      break. Stop below the lowest wick of the retest candles (C6/D1).
      bounce (C7) / rejection (C8): `bounce_candles` consecutive candles, bodies on the right side, wicks through.
  exits (D1/D3): stop `stop_buffer_ticks` beyond the wick, target `target_r` R; time exit after max_hold_minutes (B2).
  limits: E1 max attempts per setup (same level + side), E2 max trades a day, E3 a winner ends the day.

Each signal's outcome is followed on later 1-minute bars (stop first when one bar touches both).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from app.engine.trade_plan import Direction, round_to_tick

D = Decimal
ET = ZoneInfo("America/New_York")
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)


class GalaCfg(Protocol):
    """The settings the engine reads (config.GalaPaCfg)."""

    @property
    def pivot_lookback(self) -> int: ...

    @property
    def trend_swing_lookback(self) -> int: ...

    @property
    def history_sessions(self) -> int: ...

    @property
    def use_open_level(self) -> bool: ...

    @property
    def skip_first_minutes(self) -> int: ...

    @property
    def window_start(self) -> str: ...

    @property
    def window_end(self) -> str: ...

    @property
    def max_wick_through_pts(self) -> Decimal: ...

    @property
    def hammer_wick_body_mult(self) -> Decimal: ...

    @property
    def max_retest_bars(self) -> int: ...

    @property
    def bounce_candles(self) -> int: ...

    @property
    def stop_buffer_ticks(self) -> int: ...

    @property
    def target_r(self) -> Decimal: ...

    @property
    def max_hold_minutes(self) -> int: ...

    @property
    def max_attempts_per_setup(self) -> int: ...

    @property
    def max_trades_per_day(self) -> int: ...

    @property
    def stop_after_win(self) -> bool: ...

    @property
    def skip_news_first_hour(self) -> bool: ...


@dataclass(frozen=True)
class GBar:
    close_time: datetime  # aware; a 1-minute bar covers (close_time − 1 min, close_time]
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal


@dataclass(frozen=True)
class Candle:
    start: datetime
    end: datetime  # close time
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    gap: bool = False  # A7: the extended-hours candle (prior close → next open)

    @property
    def color(self) -> int:
        return 1 if self.c > self.o else -1 if self.c < self.o else 0

    @property
    def top(self) -> Decimal:
        return max(self.o, self.c)

    @property
    def bottom(self) -> Decimal:
        return min(self.o, self.c)


@dataclass(frozen=True)
class Level:
    price: Decimal
    kind: str  # "HIGH" (red after green) | "LOW" (green after red) | "OPEN" (A5)
    at: datetime  # the colour-change candle's start


@dataclass
class GalaSignal:
    time: datetime  # entry candle close (a 1-minute close too)
    direction: Direction
    setup: str  # BREAK_RETEST | BOUNCE | REJECTION
    level: Decimal
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    stop_pts: Decimal
    rr: Decimal
    attempt: int
    outcome: str | None = None  # TP | STOP | TIME | OPEN
    exit_time: datetime | None = None
    exit_price: Decimal | None = None

    @property
    def won(self) -> bool:
        return self.exit_price is not None and (self.exit_price - self.entry) * self.direction.sign > 0


@dataclass
class DayReplay:
    trend: int  # +1 LONG, −1 SHORT, 0 none (A3)
    levels: list[Level]
    setup: str | None
    level: Decimal | None
    skip: str | None  # reason code when the day has no plan
    signals: list[GalaSignal] = field(default_factory=list)


# ---------------------------------------------------------------- candles (A7, C1)


def _et(t: datetime) -> datetime:
    return t.astimezone(ET)


def rth_by_day(bars: Sequence[GBar]) -> dict[date, list[GBar]]:
    """A7: regular trading hours only — 1-minute bars closing in (09:30, 16:00] ET, grouped by ET date."""
    out: dict[date, list[GBar]] = {}
    for b in sorted(bars, key=lambda x: x.close_time):
        t = _et(b.close_time)
        if RTH_OPEN < t.time() <= RTH_CLOSE:
            out.setdefault(t.date(), []).append(b)
    return out


def aggregate(bars: Sequence[GBar], minutes: int, upto: datetime | None = None) -> list[Candle]:
    """RTH candles of `minutes` from 09:30 ET (the hourly chart: 09:30, 10:30, … 15:30–16:00). Only CLOSED candles
    (every 1-minute bar of the bucket up to its end, or the session close, has to be in — a bucket is closed when a
    bar at/after its end exists or `upto` is past its end)."""
    groups: dict[tuple[date, int], list[GBar]] = {}
    for b in bars:
        t = _et(b.close_time)
        k = (t.hour * 60 + t.minute - 1 - (9 * 60 + 30)) // minutes
        groups.setdefault((t.date(), k), []).append(b)
    out: list[Candle] = []
    for (d, k), g in sorted(groups.items()):
        start = datetime.combine(d, RTH_OPEN, tzinfo=ET) + timedelta(minutes=k * minutes)
        end = min(start + timedelta(minutes=minutes), datetime.combine(d, RTH_CLOSE, tzinfo=ET))
        if _et(g[-1].close_time) < end and (upto is None or _et(upto) < end):
            continue  # still forming
        out.append(Candle(start, end, g[0].o, max(x.h for x in g), min(x.l for x in g), g[-1].c))
    return out


def hourly_plan_candles(history: Sequence[GBar], today_open: GBar | None, sessions: int) -> list[Candle]:
    """A1 + A7: hourly RTH candles of the last `sessions` sessions; between sessions ONE extended-hours candle from
    the prior close to the next open (today's open closes the last one)."""
    days = rth_by_day(history)
    keep = sorted(days)[-sessions:] if sessions > 0 else []
    out: list[Candle] = []
    for d in keep:
        hc = aggregate(days[d], 60)
        if out and hc:
            prev = out[-1]
            out.append(_gap(prev, hc[0].start, hc[0].o))
        out += hc
    if out and today_open is not None:
        out.append(_gap(out[-1], today_open.close_time - timedelta(minutes=1), today_open.o))
    return out


def _gap(prev: Candle, nxt: datetime, nxt_open: Decimal) -> Candle:
    return Candle(prev.end, nxt, prev.c, max(prev.c, nxt_open), min(prev.c, nxt_open), nxt_open, gap=True)


# ---------------------------------------------------------------- plan (A2–A6, A8)


def trend(candles: Sequence[Candle], k: int) -> int:
    """A2: hourly highs and lows — the last two swing highs and swing lows (k candles each side).
    Higher high + higher low = +1 (LONG), lower high + lower low = −1 (SHORT), anything else = 0 (A3 choppy)."""
    hs = [c.h for i, c in enumerate(candles) if _swing(candles, i, k, True)]
    ls = [c.l for i, c in enumerate(candles) if _swing(candles, i, k, False)]
    if len(hs) < 2 or len(ls) < 2:
        return 0
    if hs[-1] > hs[-2] and ls[-1] > ls[-2]:
        return 1
    if hs[-1] < hs[-2] and ls[-1] < ls[-2]:
        return -1
    return 0


def _swing(c: Sequence[Candle], i: int, k: int, high: bool) -> bool:
    if i < k or i + k >= len(c):
        return False
    v = c[i].h if high else c[i].l
    others = [c[j].h if high else c[j].l for j in range(i - k, i + k + 1) if j != i]
    return all(v > o for o in others) if high else all(v < o for o in others)


def pivot_levels(candles: Sequence[Candle], k: int) -> list[Level]:
    """A4: a level = the OPEN of the hourly candle where the colour changes, at a body pivot (wicks ignored): red after
    green whose open is the highest body top of the k candles each side (HIGH), green after red whose open is the
    lowest body bottom (LOW). Confirmed only once the k candles after it have closed. A6: a later candle whose BODY
    pierces through the level deletes it."""
    out: list[Level] = []
    for j in range(1, len(candles)):
        a, b = candles[j - 1], candles[j]
        if a.color == 0 or b.color == 0 or a.color == b.color:
            continue
        lo, hi = j - k, j + k
        if lo < 0 or hi >= len(candles):
            continue
        win = candles[lo : hi + 1]
        if b.color < 0 and b.o >= max(x.top for x in win):
            lv = Level(b.o, "HIGH", b.start)
        elif b.color > 0 and b.o <= min(x.bottom for x in win):
            lv = Level(b.o, "LOW", b.start)
        else:
            continue
        if not any(x.bottom < lv.price < x.top for x in candles[j + 1 :]):  # A6
            out.append(lv)
    return out


def choose_setup(direction: int, price: Decimal, levels: Sequence[Level]) -> tuple[str, Decimal] | None:
    """A8: which level and which setup. LONG: closer to the level above → BREAK_RETEST of it, closer to the level
    below → BOUNCE off it. SHORT: closer to the level below → BREAK_RETEST of it, else REJECTION at the level above.
    Only one side present → that side's setup. A tie goes to the break-and-retest."""
    above = min((x.price for x in levels if x.price > price), default=None)
    below = max((x.price for x in levels if x.price < price), default=None)
    if above is None and below is None:
        return None
    up = None if above is None else above - price
    dn = None if below is None else price - below
    if direction > 0:
        if up is not None and (dn is None or up <= dn):
            return "BREAK_RETEST", above  # type: ignore[return-value]
        return "BOUNCE", below  # type: ignore[return-value]
    if dn is not None and (up is None or dn <= up):
        return "BREAK_RETEST", below  # type: ignore[return-value]
    return "REJECTION", above  # type: ignore[return-value]


# ---------------------------------------------------------------- entry candles (C2–C8)


def perfect_entry(c: Candle, level: Decimal, sign: int, max_through: Decimal) -> bool:
    """C2 + C3: the wick touches / goes slightly through the level (≤ max_through), the body is on the right side and
    the candle closes beyond the level (LONG: low ≤ level, body ≥ level, close > level; SHORT mirrors)."""
    if sign > 0:
        return c.l <= level and c.bottom >= level and c.c > level and level - c.l <= max_through
    return c.h >= level and c.top <= level and c.c < level and c.h - level <= max_through


def hammer(c: Candle, sign: int, mult: Decimal, tick: Decimal) -> bool:
    """C4: a big-wick fast reversal off the level (wick toward the level ≥ mult × body) → skip, the stop is too wide."""
    wick = c.bottom - c.l if sign > 0 else c.h - c.top
    return wick >= mult * max(c.top - c.bottom, tick)


def find_entry(
    candles: Sequence[Candle], setup: str, level: Decimal, sign: int, cfg: GalaCfg, tick: Decimal
) -> tuple[int, Decimal] | None:
    """Scan 5-minute candles in order; return (index of the entry candle, extreme wick of the setup candles) for the
    first valid entry, else None. C5/C6 break-and-retest, C7 bounce (LONG), C8 rejection (SHORT)."""
    if setup == "BREAK_RETEST":
        brk: int | None = None
        for i, c in enumerate(candles):
            prev_c = candles[i - 1].c if i > 0 else c.o
            if brk is None:
                if (c.c > level >= prev_c) if sign > 0 else (c.c < level <= prev_c):
                    brk = i  # C5 the breaking candle closes beyond the level
                continue
            if (c.c < level) if sign > 0 else (c.c > level):
                brk = None  # C5 back through the level → not accepted; wait for a new break
                if (c.c > level >= prev_c) if sign > 0 else (c.c < level <= prev_c):
                    brk = i
                continue
            if i - brk > cfg.max_retest_bars:
                brk = None
                continue
            if perfect_entry(c, level, sign, cfg.max_wick_through_pts) and not hammer(
                c, sign, cfg.hammer_wick_body_mult, tick
            ):
                grp: Sequence[Candle] = [
                    x for x in candles[brk + 1 : i + 1] if (x.l <= level if sign > 0 else x.h >= level)
                ]
                ext = min(x.l for x in grp) if sign > 0 else max(x.h for x in grp)  # C6 lowest / highest wick
                return i, ext
        return None
    run = 0
    for i, c in enumerate(candles):
        hold = (c.bottom >= level and c.l < level) if sign > 0 else (c.top <= level and c.h > level)
        run = run + 1 if hold else 0
        if run >= cfg.bounce_candles and perfect_entry(c, level, sign, cfg.max_wick_through_pts):
            if hammer(c, sign, cfg.hammer_wick_body_mult, tick):
                continue
            grp = candles[i - run + 1 : i + 1]
            return i, (min(x.l for x in grp) if sign > 0 else max(x.h for x in grp))
    return None


# ---------------------------------------------------------------- the day


def _at(d: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=ET)


def _follow(sig: GalaSignal, bars: Sequence[GBar], hold_until: datetime, flat_at: datetime) -> None:
    """Outcome on later 1-minute bars: stop first when a bar touches both; time exit at the hold limit (B2)."""
    s = sig.direction.sign
    sig.outcome = "OPEN"
    for b in bars:
        if b.close_time <= sig.time:
            continue
        if (b.l <= sig.stop) if s > 0 else (b.h >= sig.stop):
            sig.outcome, sig.exit_time, sig.exit_price = "STOP", b.close_time, sig.stop
            return
        if (b.h >= sig.take_profit) if s > 0 else (b.l <= sig.take_profit):
            sig.outcome, sig.exit_time, sig.exit_price = "TP", b.close_time, sig.take_profit
            return
        if b.close_time >= min(hold_until, flat_at):
            sig.outcome, sig.exit_time, sig.exit_price = "TIME", b.close_time, b.c
            return


def replay_day(
    history: Sequence[GBar], today: Sequence[GBar], cfg: GalaCfg, tick: Decimal, news_first_hour: bool = False
) -> DayReplay:
    """The whole rule sheet for one session, from the stored bars only (`today` = this session's 1-minute bars up to
    now; `history` = earlier sessions). Deterministic: the same bars give the same signals."""
    rth = rth_by_day(today)
    if not rth:
        return DayReplay(0, [], None, None, "GALA_NO_BARS")
    day = max(rth)
    bars = rth[day]
    first = bars[0]
    if _et(first.close_time) != _at(day, "09:31"):
        return DayReplay(0, [], None, None, "GALA_NO_OPEN")
    plan = hourly_plan_candles([b for b in history if _et(b.close_time).date() < day], first, cfg.history_sessions)
    tr = trend(plan, cfg.trend_swing_lookback)
    levels = pivot_levels(plan, cfg.pivot_lookback)
    if cfg.use_open_level:
        levels.append(Level(first.o, "OPEN", _at(day, "09:30")))  # A5
    if tr == 0:
        return DayReplay(0, levels, None, None, "GALA_NO_TREND")  # A3
    if cfg.skip_news_first_hour and news_first_hour:
        return DayReplay(tr, levels, None, None, "GALA_NEWS_FIRST_HOUR")  # A9
    pick = choose_setup(tr, first.o, levels)
    if pick is None:
        return DayReplay(tr, levels, None, None, "GALA_NO_LEVEL")
    setup, level = pick
    out = DayReplay(tr, levels, setup, level, None)
    sign = tr
    direction = Direction.LONG if sign > 0 else Direction.SHORT
    skip_until = _at(day, "09:30") + timedelta(minutes=cfg.skip_first_minutes)  # B1
    w0, w1 = _at(day, cfg.window_start), _at(day, cfg.window_end)  # B2
    flat = datetime.combine(day, RTH_CLOSE, tzinfo=ET)
    last = bars[-1].close_time
    five = [c for c in aggregate(bars, 5, last) if c.end > skip_until]
    free_after = skip_until
    attempts: dict[tuple[Decimal, int], int] = {}
    while len(out.signals) < cfg.max_trades_per_day:  # E2
        if attempts.get((level, sign), 0) >= cfg.max_attempts_per_setup:
            break  # E1: a third try on the same level + side is a broken rule
        scan = [c for c in five if c.start >= free_after]
        hit = find_entry(scan, setup, level, sign, cfg, tick)
        if hit is None:
            break
        c = scan[hit[0]]
        if not (w0 < c.end <= w1):
            break  # B2: entries inside the window only
        entry = c.c
        stop = round_to_tick(hit[1] - sign * cfg.stop_buffer_ticks * tick, tick, away_from=entry)  # D1
        risk = (entry - stop) * sign
        if risk <= 0:
            break
        tp = round_to_tick(entry + sign * cfg.target_r * risk, tick, toward=entry)  # D3
        attempts[(level, sign)] = attempts.get((level, sign), 0) + 1
        sig = GalaSignal(
            c.end, direction, setup, level, entry, stop, tp, risk, (tp - entry) * sign / risk, attempts[(level, sign)]
        )
        _follow(sig, bars, c.end + timedelta(minutes=cfg.max_hold_minutes), flat)
        out.signals.append(sig)
        if sig.outcome == "OPEN" or sig.exit_time is None or sig.exit_price is None:
            break  # still running at `now`
        if sig.won and cfg.stop_after_win:
            break  # E3 one and done
        free_after = _et(sig.exit_time)
        again = choose_setup(sign, sig.exit_price, levels)  # A8 again from where price is now
        if again is None:
            break
        setup, level = again
    return out
