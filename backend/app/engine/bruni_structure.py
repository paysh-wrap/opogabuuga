"""BRUNI STRUCTURE — built ONLY from docs/BRUNI_RULES.md. PURE (no I/O, Decimal).

Rule ids refer to the rule sheet. Closed 1-minute RTH bars only, no lookahead.

  A1 one time frame: 15-minute candles built from 1-minute RTH bars (earlier sessions + today).
  A2 a breakout = a candle BODY closing beyond the last confirmed swing level by ≥ breakout_min_ticks ([GAP]).
  A3 only the last two breakouts count: ACTUAL (A) = the latest, PERIPHERAL (P) = the one before.
  A4 A and P agree → that side. A5/A6/A7 they disagree → follow A until its DIRECTIONAL POTENTIAL is used up (price
     reached the 75% level of P's leg — FIB — or the value-area limit of P's leg — VALUE_AREA), then follow P.
  A12 no breakout = no trade.
  B1–B5 triple print: the zone = the latest three VALID candles (body > longest wick) of the opposite colour before
     the impulse of the actual breakout (B4); none → no zone → no trade (B5). B7 the zone uses the A1 chart.
  C1–C5 wick gap: the two wicks closest to the stop; a gap smaller than wick_gap_min_pts skips ([GAP] default OFF).
  D (flagged [GAP], the trigger is not shown in the video): a 1-minute bar returns into the zone while the context
     side holds → entry at that close, stop stop_buffer_ticks beyond the zone's far edge.
  E1/E2 fixed target `target_r` (default 2, never above 3).
  F6 regime flip (OFF by default): realized volatility of the last N 15-minute bars → bucket; the side flips only when
     the stored in-sample table says FLIP for that bucket.
`replay_day(history, today, cfg, tick)` is deterministic on the stored bars: live = backtest.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction, round_to_tick

ET = ZoneInfo("America/New_York")
D = Decimal


class BruniCfg(Protocol):
    @property
    def tf_minutes(self) -> int: ...
    @property
    def history_sessions(self) -> int: ...
    @property
    def swing_lookback(self) -> int: ...
    @property
    def breakout_min_ticks(self) -> int: ...
    @property
    def potential(self) -> str: ...
    @property
    def potential_fib(self) -> Decimal: ...
    @property
    def value_area_pct(self) -> Decimal: ...
    @property
    def zone_candles(self) -> int: ...
    @property
    def zone_lookback(self) -> int: ...
    @property
    def wick_gap_min_pts(self) -> Decimal | None: ...
    @property
    def stop_buffer_ticks(self) -> int: ...
    @property
    def target_r(self) -> Decimal: ...
    @property
    def window_start(self) -> str: ...
    @property
    def last_entry(self) -> str: ...
    @property
    def time_exit(self) -> str: ...
    @property
    def max_losses_per_day(self) -> int: ...
    @property
    def regime_flip(self) -> bool: ...
    @property
    def regime_bars(self) -> int: ...
    @property
    def regime_edges(self) -> Sequence[Decimal]: ...
    @property
    def regime_table(self) -> Mapping[str, str]: ...


BUCKETS = ("CALM", "MIDDLE", "HIGH", "EXTREME")


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

    @property
    def valid(self) -> bool:
        """B1: the body is larger than the longest wick."""
        return self.body > max(self.h - max(self.o, self.c), min(self.o, self.c) - self.l)


@dataclass(frozen=True)
class Breakout:
    index: int  # the breaking candle
    direction: int  # +1 bullish, −1 bearish
    level: Decimal
    leg_lo: Decimal  # the leg the breakout completes (for the directional potential)
    leg_hi: Decimal
    leg_start: int  # index of the leg's origin swing (the impulse starts there)


@dataclass
class BruniSignal:
    time: datetime
    direction: Direction
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    zone: tuple[Decimal, Decimal]
    context: str  # AGREE | FOLLOW_A | FOLLOW_P
    regime: str | None = None
    flipped: bool = False
    outcome: str | None = None  # TP | STOP | TIME | OPEN
    exit_time: datetime | None = None
    exit_price: Decimal | None = None

    @property
    def lost(self) -> bool:
        return self.exit_price is not None and (self.exit_price - self.entry) * self.direction.sign < 0


@dataclass
class BruniDay:
    side: int
    context: str | None
    skip: str | None
    signals: list[BruniSignal] = field(default_factory=list)


def _at(d: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=ET)


def build(bars: Sequence[MBar], minutes: int) -> list[Candle]:
    """A1: closed RTH candles of `minutes` from 09:30 ET, built from 1-minute bars (every session in `bars`)."""
    groups: dict[tuple[date, int], list[MBar]] = {}
    for b in sorted(bars, key=lambda x: x.close_time):
        t = b.close_time.astimezone(ET)
        if not (time(9, 30) < t.time() <= time(16, 0)):
            continue
        k = (t.hour * 60 + t.minute - 1 - (9 * 60 + 30)) // minutes
        groups.setdefault((t.date(), k), []).append(b)
    out = []
    for (d, k), g in sorted(groups.items()):
        st = _at(d, "09:30") + timedelta(minutes=k * minutes)
        end = min(st + timedelta(minutes=minutes), _at(d, "16:00"))
        if g[-1].close_time.astimezone(ET) < end:
            continue
        out.append(Candle(st, end, g[0].o, max(x.h for x in g), min(x.l for x in g), g[-1].c))
    return out


def swings(c: Sequence[Candle], k: int) -> list[tuple[int, int, Decimal]]:
    """(index, +1 high / −1 low, price) of every swing confirmed by k candles each side."""
    out = []
    for i in range(k, len(c) - k):
        nb = [c[j] for j in range(i - k, i + k + 1) if j != i]
        if all(c[i].h > x.h for x in nb):
            out.append((i, 1, c[i].h))
        if all(c[i].l < x.l for x in nb):
            out.append((i, -1, c[i].l))
    return out


def breakouts(c: Sequence[Candle], cfg: BruniCfg, tick: Decimal) -> list[Breakout]:
    """A2: a body close beyond the latest confirmed (and not yet broken) swing high / low by ≥ breakout_min_ticks."""
    sw = swings(c, cfg.swing_lookback)
    out: list[Breakout] = []
    broken: set[int] = set()
    for i, x in enumerate(c):
        conf = [s for s in sw if s[0] + cfg.swing_lookback < i and s[0] not in broken]
        hi = next((s for s in reversed(conf) if s[1] > 0), None)
        lo = next((s for s in reversed(conf) if s[1] < 0), None)
        m = cfg.breakout_min_ticks * tick
        if hi is not None and min(x.o, x.c) <= hi[2] < x.c and x.c - hi[2] >= m:
            org = min(range(hi[0], i + 1), key=lambda n: c[n].l)  # the impulse starts at the pullback low
            out.append(Breakout(i, 1, hi[2], c[org].l, max(y.h for y in c[org : i + 1]), org))
            broken.add(hi[0])
        elif lo is not None and max(x.o, x.c) >= lo[2] > x.c and lo[2] - x.c >= m:
            org = max(range(lo[0], i + 1), key=lambda n: c[n].h)
            out.append(Breakout(i, -1, lo[2], min(y.l for y in c[org : i + 1]), c[org].h, org))
            broken.add(lo[0])
    return out


def value_area(bars: Sequence[MBar], pct: Decimal, tick: Decimal) -> tuple[Decimal, Decimal] | None:
    """A7: (VAL, VAH) of the 1-minute volume profile (each bar's volume spread over its tick bins), `pct` of volume."""
    prof: dict[Decimal, Decimal] = {}
    for b in bars:
        n = int((b.h - b.l) / tick) + 1
        if b.v <= 0:
            continue
        for k in range(n):
            p = b.l + k * tick
            prof[p] = prof.get(p, D(0)) + b.v / n
    if not prof:
        return None
    total = sum(prof.values())
    poc = max(prof, key=lambda p: prof[p])
    lo = hi = poc
    acc = prof[poc]
    prices = sorted(prof)
    while acc < pct * total:
        below = max((p for p in prices if p < lo), default=None)
        above = min((p for p in prices if p > hi), default=None)
        if below is None and above is None:
            break
        if above is None or (below is not None and prof[below] >= prof[above]):
            lo = below  # type: ignore[assignment]
            acc += prof[lo]
        else:
            hi = above
            acc += prof[hi]
    return lo, hi


def context_side(
    c: Sequence[Candle], bos: Sequence[Breakout], upto: int, cfg: BruniCfg, bars: Sequence[MBar], tick: Decimal
) -> tuple[int, str]:
    """A3–A7: the side to trade at candle `upto` from the last two breakouts (0 = none)."""
    seen = [b for b in bos if b.index <= upto]
    if not seen:
        return 0, "NO_BREAKOUT"  # A12
    a = seen[-1]
    if len(seen) == 1:
        return a.direction, "FOLLOW_A"
    p = seen[-2]
    if a.direction == p.direction:
        return a.direction, "AGREE"  # A4
    since = c[a.index : upto + 1]
    if cfg.potential == "VALUE_AREA":
        leg = [b for b in bars if c[p.leg_start].start < b.close_time <= c[p.index].end]
        va = value_area(leg, cfg.value_area_pct, tick)
        if va is None:
            return a.direction, "FOLLOW_A"
        limit = va[0] if a.direction < 0 else va[1]
    else:  # FIB: the 75% level of P's leg = the discount (bearish A) / premium (bullish A) limit
        rng = p.leg_hi - p.leg_lo
        limit = p.leg_hi - cfg.potential_fib * rng if a.direction < 0 else p.leg_lo + cfg.potential_fib * rng
    used = any(x.l <= limit for x in since) if a.direction < 0 else any(x.h >= limit for x in since)  # A7 wick ok
    return (p.direction, "FOLLOW_P") if used else (a.direction, "FOLLOW_A")  # A5


def triple_print(c: Sequence[Candle], b: Breakout, side: int, cfg: BruniCfg) -> tuple[Decimal, Decimal] | None:
    """B2–B5: the latest `zone_candles` valid opposite-colour candles before the impulse that made breakout `b`
    (a demand zone = valid SELL candles before a bullish impulse); (low, high) from the first to the last of them."""
    if b.direction != side:
        return None
    want = -side
    picked: list[Candle] = []
    for i in range(b.leg_start, max(-1, b.leg_start - cfg.zone_lookback), -1):
        if c[i].valid and c[i].color == want:
            picked.append(c[i])
            if len(picked) == cfg.zone_candles:
                return min(x.l for x in picked), max(x.h for x in picked)
    return None  # B3 / B5


def wick_gap(c: Sequence[Candle], side: int, upto: int, lookback: int = 20) -> Decimal | None:
    """C1: distance between the two wicks closest to the stop (the two lowest lows for a long) of recent candles."""
    xs = c[max(0, upto - lookback) : upto + 1]
    if len(xs) < 2:
        return None
    ws = sorted(x.l for x in xs) if side > 0 else sorted((x.h for x in xs), reverse=True)
    return abs(ws[1] - ws[0])


def regime(c: Sequence[Candle], upto: int, cfg: BruniCfg) -> str | None:
    """F6 [GAP] proxy for his GARCH forecast: mean |close-to-close| of the last regime_bars candles → bucket."""
    xs = c[max(0, upto - cfg.regime_bars) : upto + 1]
    if len(xs) < 2:
        return None
    vol = sum((abs(xs[i].c - xs[i - 1].c) for i in range(1, len(xs))), D(0)) / (len(xs) - 1)
    k = sum(1 for e in cfg.regime_edges if vol > e)
    return BUCKETS[min(k, len(BUCKETS) - 1)]


def replay_day(history: Sequence[MBar], today: Sequence[MBar], cfg: BruniCfg, tick: Decimal) -> BruniDay:
    """The rule sheet for this New York session from the stored 1-minute bars (earlier sessions give the structure)."""
    if not today:
        return BruniDay(0, None, "BRUNI_NO_BARS")
    d = today[-1].close_time.astimezone(ET).date()
    days = sorted({b.close_time.astimezone(ET).date() for b in history if b.close_time.astimezone(ET).date() < d})
    keep = set(days[-cfg.history_sessions :])
    allb = [b for b in history if b.close_time.astimezone(ET).date() in keep] + list(today)
    c = build(allb, cfg.tf_minutes)
    bos = breakouts(c, cfg, tick)
    out = BruniDay(0, None, None)
    w0, last, tx = _at(d, cfg.window_start), _at(d, cfg.last_entry), _at(d, cfg.time_exit)
    mins = sorted((b for b in today if _at(d, "09:30") < b.close_time <= _at(d, "16:00")), key=lambda b: b.close_time)
    pos: BruniSignal | None = None
    losses = 0
    used_zones: set[tuple[Decimal, Decimal]] = set()
    for b in mins:
        if pos is not None:
            _step(pos, b, tx)
            if pos.outcome != "OPEN":
                losses += pos.lost
                pos = None
            continue
        if not (w0 < b.close_time <= last) or losses >= cfg.max_losses_per_day:
            continue
        upto = max((i for i, x in enumerate(c) if x.end <= b.close_time), default=-1)
        if upto < 0:
            continue
        side, ctx = context_side(c, bos, upto, cfg, allb, tick)
        out.side, out.context = side, ctx
        if side == 0:
            continue
        a = next((x for x in reversed(bos) if x.index <= upto and x.direction == side), None)
        zone = triple_print(c, a, side, cfg) if a is not None else None
        if zone is None or zone in used_zones:
            continue
        inside = b.l <= zone[1] and b.c >= zone[0] if side > 0 else b.h >= zone[0] and b.c <= zone[1]
        if not inside:
            continue
        gap = wick_gap(c, side, upto)
        if cfg.wick_gap_min_pts is not None and gap is not None and gap < cfg.wick_gap_min_pts:
            used_zones.add(zone)
            continue  # C2: too small a wick gap tends to stop out
        used_zones.add(zone)
        sign = side
        rg = regime(c, upto, cfg) if cfg.regime_flip else None
        flip = rg is not None and cfg.regime_table.get(rg) == "FLIP"
        entry = b.c
        far = zone[0] if sign > 0 else zone[1]
        stop = round_to_tick(far - sign * cfg.stop_buffer_ticks * tick, tick, away_from=entry)
        risk = (entry - stop) * sign
        if risk <= 0:
            continue
        if flip:  # F6: the opposite side, same distances (mirrored around the entry)
            sign, stop = -sign, entry + sign * risk
        tp = round_to_tick(entry + sign * cfg.target_r * risk, tick, toward=entry)
        dr = Direction.LONG if sign > 0 else Direction.SHORT
        pos = BruniSignal(b.close_time, dr, entry, stop, tp, zone, ctx, rg, flip, "OPEN")
        out.signals.append(pos)
    return out


def _step(p: BruniSignal, b: MBar, tx: datetime) -> None:
    s = p.direction.sign
    if (b.l <= p.stop) if s > 0 else (b.h >= p.stop):
        p.outcome, p.exit_time, p.exit_price = "STOP", b.close_time, p.stop
    elif (b.h >= p.take_profit) if s > 0 else (b.l <= p.take_profit):
        p.outcome, p.exit_time, p.exit_price = "TP", b.close_time, p.take_profit
    elif b.close_time >= tx:
        p.outcome, p.exit_time, p.exit_price = "TIME", b.close_time, b.c
