"""OKALA 8020 — NASDAQ 80/20 levels + market structure, built ONLY from docs/OKALA_8020_RULES.md. PURE (Decimal).

Rule ids (A1, D4, …) refer to the rule sheet. Closed 1-minute RTH bars only, no lookahead.

  A1 levels: every price ending in 20 or 80 in each hundred.
  B1 structure on 10-minute bars built exactly from 1-minute bars; entries on 3-MINUTE bars built from 1-minute bars
     ([GAP] the video's 200-second chart cannot be built from 1-minute data — flagged).
  setups (3-minute bars unless noted):
     LEVEL  (A3/A4): a candle taps a level (may stop `level_tap_tol_pts` short of it or pass it by `level_through_pts`)
            and closes `reaction_pts` away from it in the reaction direction (A2: either level, either way).
     FORK   (D1): after a strong move down off the open (≥ strong_move_pts), an initiation candle with a long lower wick
            (≥ wick_body_mult × body); the next candle holds its low and makes a higher high → LONG.
     REVERSE_FORK (D2): the mirror after a strong move up → SHORT.
     CROSS  (D4): two strong same-colour candles (body ≥ strong_body_pts); the cross = candle 1's close; a later candle
            taps the cross (± cross_tol_pts) and closes back in the move's direction → entry with the move.
     H      (D3, 10-minute): strong down candle, a bounce candle with a long lower wick, then a roll-over close below
            the bounce low = a SHORT structure (mirror LONG); not an entry by itself — it adds a confluence to a CROSS.
     REPAIR (D5, 10-minute): a candle that opens with no wick on its opening side (≤ no_wick_ticks) is a magnet at its
            open until touched; the nearest untouched magnet ahead is the runner target and a confluence.
  C1 stop always 10 pt; C2 TP1 15 pt; C3 stop to break even + be_cover_pts after TP1; C4 runner to the magnet or
  runner_target_pts; B3 windows (NY open, lunch excluded); E1/E3 no trade cap, [GAP] max_losses_per_day.
  D6 / D145 adds: a same-direction setup while the open trade has taken TP1 (stop at break even) is an ADD signal
  (at most max_adds); the controller sizes it from the remaining per-trade risk cap.
`replay_day(today, cfg, tick)` is a deterministic function of the stored bars (live = backtest).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction, round_to_tick

ET = ZoneInfo("America/New_York")
D = Decimal


class OkalaCfg(Protocol):
    @property
    def entry_minutes(self) -> int: ...
    @property
    def structure_minutes(self) -> int: ...
    @property
    def windows(self) -> Sequence[str]: ...
    @property
    def stop_pts(self) -> Decimal: ...
    @property
    def tp1_pts(self) -> Decimal: ...
    @property
    def be_cover_pts(self) -> Decimal: ...
    @property
    def runner_target_pts(self) -> Decimal: ...
    @property
    def level_tap_tol_pts(self) -> Decimal: ...
    @property
    def level_through_pts(self) -> Decimal: ...
    @property
    def reaction_pts(self) -> Decimal: ...
    @property
    def strong_move_pts(self) -> Decimal: ...
    @property
    def strong_body_pts(self) -> Decimal: ...
    @property
    def wick_body_mult(self) -> Decimal: ...
    @property
    def cross_tol_pts(self) -> Decimal: ...
    @property
    def cross_max_bars(self) -> int: ...
    @property
    def no_wick_ticks(self) -> int: ...
    @property
    def setups(self) -> Sequence[str]: ...
    @property
    def max_losses_per_day(self) -> int: ...
    @property
    def max_hold_minutes(self) -> int: ...
    @property
    def add_after_tp1(self) -> bool: ...
    @property
    def max_adds(self) -> int: ...


@dataclass(frozen=True)
class Candle:
    start: datetime
    end: datetime
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal

    @property
    def color(self) -> int:
        return 1 if self.c > self.o else -1 if self.c < self.o else 0

    @property
    def body(self) -> Decimal:
        return abs(self.c - self.o)


@dataclass
class OkalaSignal:
    time: datetime
    direction: Direction
    setup: str
    entry: Decimal
    stop: Decimal
    tp1: Decimal
    runner_target: Decimal
    confluences: list[str]
    add_no: int = 0  # 0 = a new position, n = the n-th add to the open one (D145)
    outcome: str | None = None  # STOP | BE | RUNNER | TIME | OPEN
    tp1_time: datetime | None = None
    exit_time: datetime | None = None

    @property
    def lost(self) -> bool:
        return self.outcome == "STOP"


@dataclass
class OkalaDay:
    signals: list[OkalaSignal] = field(default_factory=list)
    magnets: list[Decimal] = field(default_factory=list)


# ---------------------------------------------------------------- candles + levels


def _at(d: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=ET)


def build(bars: Sequence[MBar], minutes: int) -> list[Candle]:
    """Closed `minutes` candles from 09:30 ET, built exactly from the 1-minute bars (a candle is closed when its last
    minute is in)."""
    groups: dict[tuple[date, int], list[MBar]] = {}
    for b in bars:
        t = b.close_time.astimezone(ET)
        k = (t.hour * 60 + t.minute - 1 - (9 * 60 + 30)) // minutes
        groups.setdefault((t.date(), k), []).append(b)
    out: list[Candle] = []
    for (d, k), g in sorted(groups.items()):
        st = _at(d, "09:30") + timedelta(minutes=k * minutes)
        end = st + timedelta(minutes=minutes)
        if g[-1].close_time.astimezone(ET) < end:
            continue
        out.append(Candle(st, end, g[0].o, max(x.h for x in g), min(x.l for x in g), g[-1].c))
    return out


SPAN = D(200)


def levels_near(price: Decimal, span: Decimal = SPAN) -> list[Decimal]:
    """A1: every xx20 and xx80 within `span` of price."""
    base = (price // 100) * 100
    out = []
    for h in range(-int(span // 100) - 1, int(span // 100) + 2):
        for e in (20, 80):
            lv = base + h * 100 + e
            if abs(lv - price) <= span:
                out.append(lv)
    return sorted(out)


def is_level(x: Decimal) -> bool:
    return x % 100 in (20, 80)


def nearest_level(x: Decimal) -> Decimal:
    return min(levels_near(x), key=lambda lv: abs(lv - x))


# ---------------------------------------------------------------- setups


def level_reaction(c: Candle, cfg: OkalaCfg) -> tuple[int, Decimal] | None:
    """A3/A4: (direction, level) when the candle tapped a level and closed `reaction_pts` away from it."""
    for lv in levels_near(c.c):
        # LONG: the low reached the level (or stopped tap_tol short above it) and did not pass it by more than through
        if lv - cfg.level_through_pts <= c.l <= lv + cfg.level_tap_tol_pts and c.c >= lv + cfg.reaction_pts:
            return 1, lv
        if lv - cfg.level_tap_tol_pts <= c.h <= lv + cfg.level_through_pts and c.c <= lv - cfg.reaction_pts:
            return -1, lv
    return None


def fork(c: Sequence[Candle], i: int, session_open: Decimal, cfg: OkalaCfg) -> int | None:
    """D1 / D2 on entry candle i: candle i−1 = the initiation candle (long wick on the move's side, short body), candle
    i holds its extreme and breaks its other side. +1 FORK (after a strong move down), −1 REVERSE_FORK."""
    if i < 1:
        return None
    a, b = c[i - 1], c[i]
    low_so_far = min(x.l for x in c[: i + 1])
    high_so_far = max(x.h for x in c[: i + 1])
    lower_wick, upper_wick = min(a.o, a.c) - a.l, a.h - max(a.o, a.c)
    body = max(a.body, D("0.25"))
    w = cfg.wick_body_mult * body
    if session_open - a.l >= cfg.strong_move_pts and a.l == low_so_far and lower_wick >= w and b.l >= a.l and b.h > a.h:
        return 1
    if (
        a.h - session_open >= cfg.strong_move_pts
        and a.h == high_so_far
        and upper_wick >= w
        and b.h <= a.h
        and b.l < a.l
    ):
        return -1
    return None


def crosses(c: Sequence[Candle], upto: int, cfg: OkalaCfg) -> list[tuple[int, int, Decimal]]:
    """D4: (index of the 2nd strong candle, direction, cross price = candle 1's close) for every strong pair before
    `upto` (the tap must come after the pair)."""
    out = []
    for j in range(1, upto):
        a, b = c[j - 1], c[j]
        if a.color == b.color != 0 and a.body >= cfg.strong_body_pts and b.body >= cfg.strong_body_pts:
            out.append((j, a.color, a.c))
    return out


def cross_entry(c: Sequence[Candle], i: int, cfg: OkalaCfg) -> tuple[int, Decimal] | None:
    """D4: candle i taps a recent cross and closes back in the move's direction (rejection of the cross)."""
    x = c[i]
    for j, d, px in reversed(crosses(c, i, cfg)):
        if i - j > cfg.cross_max_bars or i - j < 2:
            continue
        tapped = (x.l <= px + cfg.cross_tol_pts) if d > 0 else (x.h >= px - cfg.cross_tol_pts)
        held = (x.c > px and x.color > 0) if d > 0 else (x.c < px and x.color < 0)
        if tapped and held:
            return d, px
    return None


def h_pattern(c10: Sequence[Candle], cfg: OkalaCfg) -> int | None:
    """D3 on the last three closed 10-minute candles: a strong move one way, a bounce candle with a long wick on the
    move's side, then a close beyond the bounce candle (lowercase h) → −1 (short continuation) / +1 mirror."""
    if len(c10) < 3:
        return None
    a, b, x = c10[-3], c10[-2], c10[-1]
    body = max(b.body, D("0.25"))
    strong = a.body >= cfg.strong_body_pts
    if a.color < 0 and strong and min(b.o, b.c) - b.l >= cfg.wick_body_mult * body and x.c < b.l:
        return -1
    if a.color > 0 and strong and b.h - max(b.o, b.c) >= cfg.wick_body_mult * body and x.c > b.h:
        return 1
    return None


def repair_magnets(c10: Sequence[Candle], after: Sequence[MBar], tick: Decimal, cfg: OkalaCfg) -> list[Decimal]:
    """D5: 10-minute candles that open with no wick on the opening side (a down candle opening at its high, an up
    candle at its low) are magnets at their open, valid while no later 1-minute bar has touched them."""
    out = []
    for k in c10:
        tol = cfg.no_wick_ticks * tick
        if (k.color < 0 and k.h - k.o <= tol) or (k.color > 0 and k.o - k.l <= tol):
            later = [b for b in after if b.close_time > k.end]
            if not any(b.l <= k.o <= b.h for b in later):
                out.append(k.o)
    return out


# ---------------------------------------------------------------- the day


def _in_windows(t: datetime, windows: Sequence[str]) -> bool:
    d = t.astimezone(ET).date()
    for w in windows:
        a, b = w.split("-")
        if _at(d, a) < t <= _at(d, b):
            return True
    return False


def _follow(sig: OkalaSignal, bars: Sequence[MBar], cfg: OkalaCfg, flat: datetime) -> None:
    """C1–C4 outcome: stop 10 → STOP; TP1 → stop to break even + cover; then the runner target, break even or time."""
    s = sig.direction.sign
    stop = sig.stop
    sig.outcome = "OPEN"
    for b in bars:
        if b.close_time <= sig.time:
            continue
        if (b.l <= stop) if s > 0 else (b.h >= stop):
            sig.outcome, sig.exit_time = ("STOP" if sig.tp1_time is None else "BE"), b.close_time
            return
        if sig.tp1_time is None and ((b.h >= sig.tp1) if s > 0 else (b.l <= sig.tp1)):
            sig.tp1_time = b.close_time
            stop = sig.entry + s * cfg.be_cover_pts  # C3
        if sig.tp1_time is not None and ((b.h >= sig.runner_target) if s > 0 else (b.l <= sig.runner_target)):
            sig.outcome, sig.exit_time = "RUNNER", b.close_time
            return
        if b.close_time >= min(flat, sig.time + timedelta(minutes=cfg.max_hold_minutes)):
            sig.outcome, sig.exit_time = "TIME", b.close_time
            return


def replay_day(today: Sequence[MBar], cfg: OkalaCfg, tick: Decimal) -> OkalaDay:
    """Every OKALA 8020 entry and add of this session so far, from its 1-minute bars."""
    out = OkalaDay()
    if not today:
        return out
    d = today[-1].close_time.astimezone(ET).date()
    o = _at(d, "09:30")
    bars = sorted((b for b in today if o < b.close_time <= _at(d, "16:00")), key=lambda b: b.close_time)
    if not bars or bars[0].close_time != o + timedelta(minutes=1):
        return out
    sopen = bars[0].o
    c3 = build(bars, cfg.entry_minutes)
    last_window_end = max(_at(d, w.split("-")[1]) for w in cfg.windows)
    open_pos: OkalaSignal | None = None
    adds, losses = 0, 0
    for i, x in enumerate(c3):
        now = x.end
        if open_pos is not None and open_pos.exit_time is not None and open_pos.exit_time <= now:
            losses += open_pos.lost
            open_pos, adds = None, 0
        if losses >= cfg.max_losses_per_day or not _in_windows(now, cfg.windows):
            continue
        seen = [b for b in bars if b.close_time <= now]
        c10 = build(seen, cfg.structure_minutes)
        hit: tuple[int, str] | None = None
        conf: list[str] = []
        f = fork(c3, i, sopen, cfg) if "FORK" in cfg.setups else None
        if f is not None:
            hit = (f, "FORK" if f > 0 else "REVERSE_FORK")
        if hit is None and "CROSS" in cfg.setups:
            ce = cross_entry(c3, i, cfg)
            if ce is not None:
                hit = (ce[0], "CROSS")
                if is_level(ce[1]) or abs(nearest_level(ce[1]) - ce[1]) <= cfg.cross_tol_pts:
                    conf.append("LEVEL")
                if h_pattern(c10, cfg) == ce[0]:
                    conf.append("H")
        if hit is None and "LEVEL" in cfg.setups:
            lr = level_reaction(x, cfg)
            if lr is not None:
                hit = (lr[0], "LEVEL")
        if hit is None:
            continue
        sign, setup = hit
        if setup != "CROSS" and abs(nearest_level(x.l if sign > 0 else x.h) - (x.l if sign > 0 else x.h)) <= D(3):
            conf.append("LEVEL")
        add_no = 0
        if open_pos is not None:
            ok = (
                open_pos.direction.sign == sign
                and cfg.add_after_tp1
                and open_pos.tp1_time is not None
                and open_pos.tp1_time <= now
                and adds < cfg.max_adds
            )
            if not ok:
                continue  # one position at a time; an add only on the winner's side after TP1 (D145)
            adds += 1
            add_no = adds
        entry = x.c
        mags = repair_magnets(c10, seen, tick, cfg)
        ahead = [m for m in mags if (m - entry) * sign > cfg.tp1_pts]
        runner = min(ahead, key=lambda m: abs(m - entry)) if ahead else entry + sign * cfg.runner_target_pts
        if ahead:
            conf.append("REPAIR")
        dr = Direction.LONG if sign > 0 else Direction.SHORT
        sig = OkalaSignal(
            now,
            dr,
            setup,
            entry,
            round_to_tick(entry - sign * cfg.stop_pts, tick, away_from=entry),  # C1
            round_to_tick(entry + sign * cfg.tp1_pts, tick, toward=entry),  # C2
            round_to_tick(runner, tick, toward=entry),
            sorted(set(conf)),
            add_no,
        )
        _follow(sig, bars, cfg, last_window_end + timedelta(minutes=cfg.max_hold_minutes))
        out.signals.append(sig)
        if add_no == 0:
            open_pos = sig
        out.magnets = mags
    return out
