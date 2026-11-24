"""CANDACE ICT SCALP — built ONLY from docs/CANDACE_ICT_RULES.md. PURE (no I/O, Decimal). 1-minute bars only.

  A3 liquidity pools: equal highs / lows (within eq_tol_ticks), 1-minute swing highs / lows, the previous day's and
     today's session high / low so far, 1-HOUR FVG edges (A1/C7, hourly candles built from 1-minute bars).
  A4 sweep: a bar trades beyond a pool and CLOSES back inside → trade the reversal (high swept → SHORT).
  C1/C2 the FVG left by the run into the sweep (opposite colour) becomes an IFVG when a candle BODY closes completely
     through it; C5 that candle must displace: body ≥ displacement_mult × the average body of the last 10 bars.
  C3 entry = the retrace back into the IFVG (the next bar that trades into it), at that bar's close.
  A2 premium / discount: shorts only above premium_pct of the dealing range (lows / highs of the last range_bars).
  D1 stop beyond the sweep extreme (+ stop_buffer_ticks); D2 max stop NY 40 / LONDON 25 pt → skip (never widen).
  D3 target ≥ min_rr R, moved to the nearest pool beyond it.
  C8 RTH gap (prior 16:00 close → 09:30 open) 25 / 50 / 75 % levels = reference + confluence.
  E3 grade by confluence count (A+ ≥ 4, B 3, C ≤ 2) → size multiplier 2.0 / 1.0 / 0.5, applied TIGHTEN-ONLY by the
     controller (multiplier / 2.0 of the Lucid-fit size).
  B1/B4 sessions NY 09:00–10:00 (on), LONDON 02:00–05:00 (off; cannot be tested: RTH-only history); max hold.
  D154 keep_all_sweeps: every sweep is followed on its own (a later sweep no longer replaces a pending one).
`replay_day(history, today, cfg, tick)` is deterministic on the stored bars (live = backtest).
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


class CandaceCfg(Protocol):
    @property
    def ny_window(self) -> str: ...
    @property
    def london_window(self) -> str: ...
    @property
    def london(self) -> bool: ...
    @property
    def ny_max_stop_pts(self) -> Decimal: ...
    @property
    def london_max_stop_pts(self) -> Decimal: ...
    @property
    def ny_max_hold_minutes(self) -> int: ...
    @property
    def london_max_hold_minutes(self) -> int: ...
    @property
    def eq_tol_ticks(self) -> int: ...
    @property
    def swing_lookback(self) -> int: ...
    @property
    def displacement_mult(self) -> Decimal: ...
    @property
    def displacement_bars(self) -> int: ...
    @property
    def fvg_lookback(self) -> int: ...
    @property
    def ifvg_max_bars(self) -> int: ...
    @property
    def premium_pct(self) -> Decimal: ...
    @property
    def range_bars(self) -> int: ...
    @property
    def stop_buffer_ticks(self) -> int: ...
    @property
    def min_rr(self) -> Decimal: ...
    @property
    def gap_level_tol_pts(self) -> Decimal: ...
    @property
    def grade_a_min(self) -> int: ...
    @property
    def grade_b_min(self) -> int: ...
    @property
    def max_losses_per_day(self) -> int: ...
    @property
    def keep_all_sweeps(self) -> bool: ...


GRADE_MULT = {"A+": D("2.0"), "B": D("1.0"), "C": D("0.5")}


@dataclass(frozen=True)
class Pool:
    price: Decimal
    side: int  # +1 buy-side (highs), −1 sell-side (lows)
    kind: str  # EQUAL | SWING | PDH | PDL | SESSION | FVG1H


@dataclass(frozen=True)
class Fvg:
    i: int  # index of the 3rd candle
    color: int  # +1 bullish gap (c1.h < c3.l), −1 bearish
    lo: Decimal
    hi: Decimal


@dataclass
class CandaceSignal:
    time: datetime
    session: str
    direction: Direction
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    swept: Pool
    confluences: list[str]
    grade: str
    hold_until: datetime
    outcome: str | None = None  # TP | STOP | TIME | OPEN
    exit_time: datetime | None = None
    exit_price: Decimal | None = None

    @property
    def size_mult(self) -> Decimal:
        return GRADE_MULT[self.grade]


@dataclass
class CandaceDay:
    gap_levels: list[Decimal] = field(default_factory=list)
    signals: list[CandaceSignal] = field(default_factory=list)


def _at(d: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=ET)


def fvgs(bars: Sequence[MBar]) -> list[Fvg]:
    """C1: three-candle gaps (candle 1's wick to candle 3's wick)."""
    out = []
    for i in range(2, len(bars)):
        a, c = bars[i - 2], bars[i]
        if a.h < c.l:
            out.append(Fvg(i, 1, a.h, c.l))
        elif a.l > c.h:
            out.append(Fvg(i, -1, c.h, a.l))
    return out


def hourly(bars: Sequence[MBar]) -> list[MBar]:
    """A1: clock-hour candles built from 1-minute bars (closed hours only)."""
    g: dict[datetime, list[MBar]] = {}
    for b in bars:
        t = (b.close_time - timedelta(minutes=1)).astimezone(ET)
        g.setdefault(t.replace(minute=0, second=0, microsecond=0), []).append(b)
    out = []
    for h, xs in sorted(g.items()):
        if xs[-1].close_time.astimezone(ET) >= h + timedelta(hours=1):
            out.append(MBar(h + timedelta(hours=1), xs[0].o, max(x.h for x in xs), min(x.l for x in xs), xs[-1].c))
    return out


def pools(
    prev_day: Sequence[MBar], before: Sequence[MBar], hist_1h: Sequence[MBar], cfg: CandaceCfg, tick: Decimal
) -> list[Pool]:
    """A3 the liquidity pools known before the current bar."""
    out: list[Pool] = []
    if prev_day:
        out += [Pool(max(b.h for b in prev_day), 1, "PDH"), Pool(min(b.l for b in prev_day), -1, "PDL")]
    if before:
        out += [Pool(max(b.h for b in before), 1, "SESSION"), Pool(min(b.l for b in before), -1, "SESSION")]
    k = cfg.swing_lookback
    hs, ls = [], []
    for i in range(k, len(before) - k):
        nb = [before[j] for j in range(i - k, i + k + 1) if j != i]
        if all(before[i].h > x.h for x in nb):
            hs.append(before[i].h)
        if all(before[i].l < x.l for x in nb):
            ls.append(before[i].l)
    tol = cfg.eq_tol_ticks * tick
    for xs, side in ((hs, 1), (ls, -1)):
        for i, p in enumerate(xs):
            eq = any(abs(p - q) <= tol for q in xs[i + 1 :])
            out.append(Pool(p, side, "EQUAL" if eq else "SWING"))
    for f in fvgs(hist_1h):
        out += [Pool(f.hi, 1, "FVG1H"), Pool(f.lo, -1, "FVG1H")]
    return out


def rth_gap_levels(prior_close: Decimal | None, rth_open: Decimal | None) -> list[Decimal]:
    """C8: the RTH gap and its 25 / 50 / 75 % levels (a reference)."""
    if prior_close is None or rth_open is None or prior_close == rth_open:
        return []
    return [prior_close + (rth_open - prior_close) * D(p) / 100 for p in (0, 25, 50, 75, 100)]


def grade(n: int, cfg: CandaceCfg) -> str:
    """E3: A+ ≥ grade_a_min confluences, B ≥ grade_b_min, else C."""
    return "A+" if n >= cfg.grade_a_min else "B" if n >= cfg.grade_b_min else "C"


def _session(t: datetime, cfg: CandaceCfg) -> str | None:
    d = t.astimezone(ET).date()
    for name, w, on in (("NY", cfg.ny_window, True), ("LONDON", cfg.london_window, cfg.london)):
        a, b = w.split("-")
        if on and _at(d, a) < t <= _at(d, b):
            return name
    return None


@dataclass
class _Episode:
    """One sweep being followed toward an entry (A4 → C1/C2/C5 → C3)."""

    si: int  # bar index of the sweep
    pool: Pool
    ext: Decimal  # the sweep extreme (D1 stop anchor)
    ifvg: tuple[int, Fvg] | None = None  # (bar index of the displacing close, the FVG) once valid


_RANK = {"A+": 2, "B": 1, "C": 0}


def rth_only(bars: Sequence[MBar]) -> list[MBar]:
    """Regular trading hours only: bars closing in (09:30, 16:00] ET. The research ran on RTH bars alone, so the live
    feed (a 24 h store) is cut to the same bars before replay_day: no 09:01-09:30 trades, session/swing/hourly pools
    and the displacement average without overnight bars, and a Monday's previous day = Friday's RTH session."""
    return [b for b in bars if time(9, 30) < b.close_time.astimezone(ET).time() <= time(16, 0)]


def replay_day(history: Sequence[MBar], today: Sequence[MBar], cfg: CandaceCfg, tick: Decimal) -> CandaceDay:
    """Every CANDACE ICT entry of this ET day so far (today = this day's 1-minute bars, any hour).

    D154 `keep_all_sweeps` (default ON): every sweep is its own episode, followed in parallel until it trades, times
    out or fails, and episodes keep being followed while a trade is open; an entry on a bar that started with a trade
    open is not taken (max 1 position); two entries on one bar → the higher grade, then the earlier sweep. OFF = the
    D149 behaviour: one episode at a time, a new sweep replaces it, nothing is followed during a trade."""
    out = CandaceDay()
    if not today:
        return out
    keep_all = cfg.keep_all_sweeps
    d = today[-1].close_time.astimezone(ET).date()
    bars = sorted((b for b in today if b.close_time.astimezone(ET).date() == d), key=lambda b: b.close_time)
    prior = [b for b in history if b.close_time.astimezone(ET).date() < d]
    pdays = sorted({b.close_time.astimezone(ET).date() for b in prior})
    prev = [b for b in prior if pdays and b.close_time.astimezone(ET).date() == pdays[-1]]
    prev_rth = [b for b in prev if time(9, 30) < b.close_time.astimezone(ET).time() <= time(16, 0)]
    first_rth = next((b for b in bars if b.close_time.astimezone(ET).time() == time(9, 31)), None)
    out.gap_levels = rth_gap_levels(prev_rth[-1].c if prev_rth else None, first_rth.o if first_rth else None)
    h1 = hourly([*prior[-60 * 24 :], *bars])
    pos: CandaceSignal | None = None
    losses = 0
    swept_used: set[tuple[Decimal, int]] = set()
    eps: list[_Episode] = []
    for i, b in enumerate(bars):
        busy = pos is not None  # a trade was open when this bar started
        if pos is not None:
            _step(pos, b)
            if pos.outcome != "OPEN":
                losses += pos.exit_price is not None and (pos.exit_price - pos.entry) * pos.direction.sign < 0
                pos = None
                if not keep_all:
                    eps = []
            if not keep_all:
                continue
        sess = _session(b.close_time, cfg)
        if sess is None or losses >= cfg.max_losses_per_day:
            eps = []
            continue
        before = bars[:i]
        h1_known = [x for x in h1 if x.close_time <= b.close_time]
        pl = pools(prev, before, h1_known, cfg, tick)
        new: _Episode | None = None
        for p in pl:  # A4 sweep: beyond a pool, close back inside (one new sweep a bar)
            if (p.price, p.side) in swept_used:
                continue
            if (p.side > 0 and b.h > p.price > b.c) or (p.side < 0 and b.l < p.price < b.c):
                swept_used.add((p.price, p.side))
                new = _Episode(i, p, b.h if p.side > 0 else b.l)
                eps = [*eps, new] if keep_all else [new]
                break
        keep: list[_Episode] = []
        cands: list[tuple[int, int, CandaceSignal]] = []
        for e in eps:
            if e is new:
                keep.append(e)
                continue
            r = _advance(e, i, b, bars, pl, sess, out.gap_levels, cfg, tick)
            if r is None:
                keep.append(e)
            elif isinstance(r, CandaceSignal):
                cands.append((-_RANK[r.grade], e.si, r))
        eps = keep
        if cands and not busy:
            pos = min(cands, key=lambda c: (c[0], c[1]))[2]
            out.signals.append(pos)
    return out


def _advance(
    e: _Episode,
    i: int,
    b: MBar,
    bars: Sequence[MBar],
    pl: Sequence[Pool],
    sess: str,
    gap_levels: Sequence[Decimal],
    cfg: CandaceCfg,
    tick: Decimal,
) -> CandaceSignal | bool | None:
    """Move one episode on by bar i: None = still pending, False = dropped, a CandaceSignal = an entry on this bar."""
    sign = -e.pool.side  # high swept → SHORT
    if e.ifvg is None:
        run = [f for f in fvgs(bars[max(0, e.si - cfg.fvg_lookback) : e.si + 1]) if f.color == -sign]
        if not run or i == e.si:
            return None
        f = run[-1]
        body = abs(b.c - b.o)
        ref = bars[max(0, i - cfg.displacement_bars) : i]
        avg = sum((abs(x.c - x.o) for x in ref), D(0)) / max(len(ref), 1)
        through = (b.c < f.lo and b.o > f.lo) if sign < 0 else (b.c > f.hi and b.o < f.hi)  # C2 body through
        if through and body >= cfg.displacement_mult * avg:  # C5 displacement
            e.ifvg = (i, f)
            return None
        return False if i - e.si > cfg.ifvg_max_bars else None
    fi, f = e.ifvg
    if i - fi > cfg.ifvg_max_bars:
        return False
    into = (b.h >= f.lo and b.c <= f.hi) if sign < 0 else (b.l <= f.hi and b.c >= f.lo)  # C3 retrace
    if not into:
        return None
    rng = bars[max(0, i - cfg.range_bars) : i + 1]
    lo, hi = min(x.l for x in rng), max(x.h for x in rng)
    mid = lo + cfg.premium_pct * (hi - lo)
    entry = b.c
    if (sign < 0 and entry < mid) or (sign > 0 and entry > mid):
        return False  # A2: shorts in premium, longs in discount
    stop = round_to_tick(e.ext - sign * cfg.stop_buffer_ticks * tick, tick, away_from=entry)  # D1
    risk = (entry - stop) * sign
    cap = cfg.ny_max_stop_pts if sess == "NY" else cfg.london_max_stop_pts
    if risk <= 0 or risk > cap:
        return False  # D2: never widen — not the entry
    min_tp = entry + sign * cfg.min_rr * risk
    ahead = [p.price for p in pl if p.side == sign and (p.price - min_tp) * sign >= 0]
    tp_raw = min(ahead, key=lambda x: abs(x - entry)) if ahead else min_tp  # D3
    tp = round_to_tick(tp_raw, tick, toward=entry)
    if (tp - entry) * sign < cfg.min_rr * risk:
        tp = round_to_tick(min_tp, tick, away_from=entry)
    sp = e.pool
    conf = ["DISPLACEMENT"]
    if sp.kind == "EQUAL":
        conf.append("EQUAL_POOL")
    if sp.kind == "FVG1H" or any(p.kind == "FVG1H" and abs(p.price - e.ext) <= cfg.gap_level_tol_pts for p in pl):
        conf.append("HTF_FVG")
    if any(abs(g - e.ext) <= cfg.gap_level_tol_pts or abs(g - entry) <= cfg.gap_level_tol_pts for g in gap_levels):
        conf.append("RTH_GAP")
    if sp.kind in ("PDH", "PDL"):
        conf.append("PREV_DAY")
    dr = Direction.LONG if sign > 0 else Direction.SHORT
    hold = cfg.ny_max_hold_minutes if sess == "NY" else cfg.london_max_hold_minutes
    until = b.close_time + timedelta(minutes=hold)
    return CandaceSignal(b.close_time, sess, dr, entry, stop, tp, sp, conf, grade(len(conf), cfg), until, "OPEN")


def _step(p: CandaceSignal, b: MBar) -> None:
    s = p.direction.sign
    if (b.l <= p.stop) if s > 0 else (b.h >= p.stop):
        p.outcome, p.exit_time, p.exit_price = "STOP", b.close_time, p.stop
    elif (b.h >= p.take_profit) if s > 0 else (b.l <= p.take_profit):
        p.outcome, p.exit_time, p.exit_price = "TP", b.close_time, p.take_profit
    elif b.close_time >= p.hold_until:
        p.outcome, p.exit_time, p.exit_price = "TIME", b.close_time, b.c
