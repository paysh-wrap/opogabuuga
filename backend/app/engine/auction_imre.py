"""ORDER FLOW · AUCTION (IMRE) — built ONLY from docs/IMRE_AMT_RULES.md. PURE (no I/O, Decimal).

  A2/A3 regime from DAILY candles built from 1-minute RTH bars: one time framing UP = strictly higher high, higher low
     AND higher close than the day before; DOWN mirrors; anything else = BALANCE. (Weekly OTF is reported as context.)
  B1/B5 volume profile from 1-minute bars (each bar's volume spread over its tick bins): POC, 70% value area (VAL/VAH),
     low-volume nodes. The prior cash session's profile is the reference; B7 where today opened vs that value.
  C5 BIG BUBBLE ([GAP]): a 1-minute bar whose |delta| ≥ bubble_mult × the average |delta| of the last bubble_bars bars
     and that closes in the delta's direction. Delta = the bar's ESTIMATED delta (volume × (close − open) / range):
     stored bars carry no footprint delta (C4).
  Setup 1 FAILED AUCTION (BALANCE only, D1–D8): V-shape (D2–D5) — a push beyond the VA edge with an aggressive bubble
     that way, then a close back inside with an opposite big bubble → entry at market, stop beyond the reversal extreme
     + stop_buffer_ticks, target POC then the opposite value extreme. Slower flavour (D6/D7) — a close beyond the edge,
     acceptance fails back inside, a MICRO RANGE builds inside; plan A = an aggressive bubble at the micro range's outer
     edge; plan B = a bubble closing out of its inner side. Risk split between A and B (risk_share 0.5).
  Setup 2 BREAKOUT (IMBALANCE only, with the regime's side, E1–E5): never the first break; a micro range builds
     beyond the prior VA; plan A = absorbed break of its inner boundary reclaimed with a big bubble; plan B = a big
     bubble closing beyond the micro range's value-area extreme. Risk split A / B. Target = breakout_target_r R.
  F7 min_rr to the first target; F1 partial at the first target + stop to entry (controller two-leg bracket);
  F4/F8 window 09:30–11:30, max_trades_per_day; F5 news = the Lucid blackout gate.
`replay_day(history, today, cfg, tick)` is deterministic on the stored bars (live = backtest).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction, round_to_tick

ET = ZoneInfo("America/New_York")
D = Decimal


class AuctionCfg(Protocol):
    @property
    def value_area_pct(self) -> Decimal: ...
    @property
    def lvn_pct(self) -> Decimal: ...
    @property
    def bubble_mult(self) -> Decimal: ...
    @property
    def bubble_bars(self) -> int: ...
    @property
    def micro_bars(self) -> int: ...
    @property
    def micro_max_pts(self) -> Decimal: ...
    @property
    def stop_buffer_ticks(self) -> int: ...
    @property
    def min_rr(self) -> Decimal: ...
    @property
    def breakout_target_r(self) -> Decimal: ...
    @property
    def risk_share_a(self) -> Decimal: ...
    @property
    def window(self) -> str: ...
    @property
    def max_trades_per_day(self) -> int: ...


@dataclass(frozen=True)
class Profile:
    poc: Decimal
    val: Decimal
    vah: Decimal
    lvns: tuple[Decimal, ...]


@dataclass
class AuctionSignal:
    time: datetime
    setup: str  # FAILED_AUCTION_V | FAILED_AUCTION_SLOW_A | _B | BREAKOUT_A | BREAKOUT_B
    direction: Direction
    entry: Decimal
    stop: Decimal
    tp1: Decimal
    tp2: Decimal
    risk_share: Decimal
    outcome: str | None = None  # TP | STOP | OPEN (the replay follows the full target)
    exit_time: datetime | None = None


@dataclass
class AuctionDay:
    regime: str  # OTFU | OTFD | BALANCE | NO_HISTORY
    weekly: str
    prior: Profile | None
    open_vs_value: str | None  # INSIDE | ABOVE | BELOW (B7)
    signals: list[AuctionSignal] = field(default_factory=list)


def _et(t: datetime) -> datetime:
    return t.astimezone(ET)


def _at(d: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=ET)


def rth(bars: Sequence[MBar]) -> dict[date, list[MBar]]:
    out: dict[date, list[MBar]] = {}
    for b in sorted(bars, key=lambda x: x.close_time):
        t = _et(b.close_time)
        if time(9, 30) < t.time() <= time(16, 0):
            out.setdefault(t.date(), []).append(b)
    return out


def ohlc(bars: Sequence[MBar]) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    return bars[0].o, max(b.h for b in bars), min(b.l for b in bars), bars[-1].c


def one_time_framing(candles: Sequence[tuple[Decimal, Decimal, Decimal, Decimal]]) -> str:
    """A2/A3 on the last two candles (o, h, l, c): strict HH + HL + HC = OTFU; LH + LL + LC = OTFD; else BALANCE."""
    if len(candles) < 2:
        return "NO_HISTORY"
    (_, h0, l0, c0), (_, h1, l1, c1) = candles[-2], candles[-1]
    if h1 > h0 and l1 > l0 and c1 > c0:
        return "OTFU"
    if h1 < h0 and l1 < l0 and c1 < c0:
        return "OTFD"
    return "BALANCE"


def profile(bars: Sequence[MBar], pct: Decimal, lvn_pct: Decimal, tick: Decimal) -> Profile | None:
    """B1: tick-bin volume profile → POC, value area (pct of volume around the POC), low-volume nodes inside it
    (bins below lvn_pct × the mean bin)."""
    prof: dict[Decimal, Decimal] = {}
    for b in bars:
        if b.v <= 0:
            continue
        n = int((b.h - b.l) / tick) + 1
        for k in range(n):
            p = b.l + k * tick
            prof[p] = prof.get(p, D(0)) + b.v / n
    if not prof:
        return None
    total = sum(prof.values(), D(0))
    prices = sorted(prof)
    poc = max(prices, key=lambda p: (prof[p], -abs(p - prices[len(prices) // 2])))
    lo = hi = poc
    acc = prof[poc]
    while acc < pct * total:
        below = max((p for p in prices if p < lo), default=None)
        above = min((p for p in prices if p > hi), default=None)
        if below is None and above is None:
            break
        if below is not None and above is not None and prof[below] == prof[above]:
            lo, hi = below, above  # a tie grows both sides (keeps a balanced profile centred)
            acc += prof[lo] + prof[hi]
        elif above is None or (below is not None and prof[below] > prof[above]):
            lo = below  # type: ignore[assignment]
            acc += prof[lo]
        else:
            hi = above
            acc += prof[hi]
    mean = total / len(prices)
    lvns = tuple(p for p in prices if lo < p < hi and prof[p] < lvn_pct * mean)
    return Profile(poc, lo, hi, lvns)


def est_delta(b: MBar) -> Decimal:
    """C4 estimate: volume × (close − open) / range (0 on a zero-range bar)."""
    rng = b.h - b.l
    return D(0) if rng <= 0 else b.v * (b.c - b.o) / rng


def bubble(bars: Sequence[MBar], i: int, cfg: AuctionCfg) -> int:
    """C5: +1 big buy bubble, −1 big sell bubble, 0 none, on bar i (vs the previous bubble_bars bars)."""
    ref = bars[max(0, i - cfg.bubble_bars) : i]
    if not ref:
        return 0
    avg = sum((abs(est_delta(x)) for x in ref), D(0)) / len(ref)
    dl = est_delta(bars[i])
    b = bars[i]
    if avg <= 0 or abs(dl) < cfg.bubble_mult * avg:
        return 0
    if dl > 0 and b.c > b.o:
        return 1
    if dl < 0 and b.c < b.o:
        return -1
    return 0


def micro_range(bars: Sequence[MBar], end: int, cfg: AuctionCfg) -> tuple[Decimal, Decimal] | None:
    """E2/D6: the last micro_bars bars ending at `end` form a tight range (≤ micro_max_pts)."""
    if end + 1 < cfg.micro_bars:
        return None
    xs = bars[end + 1 - cfg.micro_bars : end + 1]
    lo, hi = min(x.l for x in xs), max(x.h for x in xs)
    return (lo, hi) if hi - lo <= cfg.micro_max_pts else None


def _plan(
    t: datetime, setup: str, sign: int, entry: Decimal, extreme: Decimal, t1: Decimal, t2: Decimal, share: Decimal,
    cfg: AuctionCfg, tick: Decimal,
) -> AuctionSignal | None:  # fmt: skip
    stop = round_to_tick(extreme - sign * cfg.stop_buffer_ticks * tick, tick, away_from=entry)  # C3 / D4
    risk = (entry - stop) * sign
    if risk <= 0 or (t1 - entry) * sign < cfg.min_rr * risk:  # F7
        return None
    dr = Direction.LONG if sign > 0 else Direction.SHORT
    tp1 = round_to_tick(t1, tick, toward=entry)
    tp2 = round_to_tick(t2, tick, toward=entry)
    if (tp2 - tp1) * sign < 0:
        tp2 = tp1
    return AuctionSignal(t, setup, dr, entry, stop, tp1, tp2, share)


def replay_day(history: Sequence[MBar], today: Sequence[MBar], cfg: AuctionCfg, tick: Decimal) -> AuctionDay:
    """The rule sheet for this cash session (history = earlier sessions' 1-minute bars, today = this session's)."""
    days = rth(history)
    tb = rth(today)
    d = max(tb) if tb else None
    prior_days = [k for k in sorted(days) if d is None or k < d]
    daily = [ohlc(days[k]) for k in prior_days]
    weeks: dict[tuple[int, int], list[MBar]] = {}
    for k in prior_days:
        weeks.setdefault(k.isocalendar()[:2], []).extend(days[k])
    weekly = one_time_framing([ohlc(v) for _, v in sorted(weeks.items())])
    regime = one_time_framing(daily)
    prior = profile(days[prior_days[-1]], cfg.value_area_pct, cfg.lvn_pct, tick) if prior_days else None
    out = AuctionDay(regime, weekly, prior, None)
    if d is None or prior is None:
        return out
    bars = tb[d]
    o = bars[0].o
    out.open_vs_value = "INSIDE" if prior.val <= o <= prior.vah else "ABOVE" if o > prior.vah else "BELOW"
    a, b = cfg.window.split("-")
    w0, w1 = _at(d, a), _at(d, b)
    taken = 0
    busy_until: datetime | None = None
    state: dict[str, object] = {}
    for i, x in enumerate(bars):
        if busy_until is not None and x.close_time <= busy_until:
            continue
        if not (w0 < x.close_time <= w1) or taken >= cfg.max_trades_per_day:
            continue
        cands: list[AuctionSignal | None] = []
        bb = bubble(bars, i, cfg)
        if regime == "BALANCE":
            cands += _failed_auction(bars, i, bb, prior, state, cfg, tick)
        elif regime in ("OTFU", "OTFD"):
            cands += _breakout(bars, i, bb, prior, 1 if regime == "OTFU" else -1, state, cfg, tick)
        for sig in (c for c in cands if c is not None):
            if taken >= cfg.max_trades_per_day:
                break
            _follow(sig, bars)
            out.signals.append(sig)
            taken += 1
            busy_until = sig.exit_time if sig.exit_time is not None else bars[-1].close_time
            break  # one position at a time
    return out


def _failed_auction(
    bars: Sequence[MBar], i: int, bb: int, p: Profile, st: dict[str, object], cfg: AuctionCfg, tick: Decimal
) -> list[AuctionSignal | None]:
    x = bars[i]
    out: list[AuctionSignal | None] = []
    # D2 V-shape: a push beyond an edge with an aggressive bubble that way, then a reclaim with the opposite bubble
    for side, edge, t2 in ((-1, p.val, p.vah), (1, p.vah, p.val)):
        key = f"v{side}"
        beyond = (x.l < edge) if side < 0 else (x.h > edge)
        ext = x.l if side < 0 else x.h
        if key not in st and beyond and bb == side:
            st[key] = ext
            continue
        if key in st:
            old = st[key]
            assert isinstance(old, Decimal)
            st[key] = ext = min(old, ext) if side < 0 else max(old, ext)
            if ((x.c > edge) if side < 0 else (x.c < edge)) and bb == -side:  # D3 market entry on the reclaim
                out.append(_plan(x.close_time, "FAILED_AUCTION_V", -side, x.c, ext, p.poc, t2, D(1), cfg, tick))
                st.pop(key)
    # D6/D7 slower flavour: beyond an edge, back inside, a micro range inside; plan A at its outer edge, plan B out
    for side, edge in ((1, p.vah), (-1, p.val)):
        key = f"slow{side}"
        if (x.c > edge) if side > 0 else (x.c < edge):
            st[key] = "OUT"
        elif st.get(key) == "OUT":
            st[key] = i  # failed back inside: the micro range must build from here
        start = st.get(key)
        if isinstance(start, int) and i - start >= cfg.micro_bars:
            mr = micro_range(bars, i - 1, cfg)
            if mr is None:
                continue
            lo, hi = mr
            sign, far, t1, t2 = -side, (hi if side > 0 else lo), p.poc, (p.val if side > 0 else p.vah)
            outer = hi if side > 0 else lo
            inner = lo if side > 0 else hi
            share_a = cfg.risk_share_a
            if (
                bb == sign
                and ((x.h >= outer) if side > 0 else (x.l <= outer))
                and ((x.c < outer) if side > 0 else (x.c > outer))
            ):
                out.append(
                    _plan(
                        x.close_time,
                        "FAILED_AUCTION_SLOW_A",
                        sign,
                        x.c,
                        x.h if side > 0 else x.l,
                        t1,
                        t2,
                        share_a,
                        cfg,
                        tick,
                    )
                )
                st.pop(key)
            elif bb == sign and ((x.c < inner) if side > 0 else (x.c > inner)):
                out.append(
                    _plan(x.close_time, "FAILED_AUCTION_SLOW_B", sign, x.c, far, t1, t2, D(1) - share_a, cfg, tick)
                )
                st.pop(key)
    return out


def _breakout(
    bars: Sequence[MBar], i: int, bb: int, p: Profile, sign: int, st: dict[str, object], cfg: AuctionCfg, tick: Decimal
) -> list[AuctionSignal | None]:
    """E1–E5 with the regime's side: break of the prior VA, a micro range beyond it, plan A / plan B."""
    x = bars[i]
    edge = p.vah if sign > 0 else p.val
    if "broke" not in st:
        if (x.c > edge) if sign > 0 else (x.c < edge):
            st["broke"] = i  # E1: never the first break itself
        return []
    mr = micro_range(bars, i - 1, cfg)
    start = int(st["broke"])  # type: ignore[call-overload]
    if mr is None or i - cfg.micro_bars <= start:
        return []
    lo, hi = mr
    if (lo < edge) if sign > 0 else (hi > edge):
        return []  # E2: the micro range must sit beyond the old value
    micro = profile(bars[i - cfg.micro_bars : i], cfg.value_area_pct, cfg.lvn_pct, tick)
    inner, outer = (lo, hi) if sign > 0 else (hi, lo)
    out: list[AuctionSignal | None] = []
    share_a = cfg.risk_share_a
    if bb == sign and ((x.l < inner < x.c) if sign > 0 else (x.h > inner > x.c)):  # E3 plan A: absorbed and reclaimed
        ext = x.l if sign > 0 else x.h
        risk = abs(x.c - ext) + cfg.stop_buffer_ticks * tick
        t = x.c + sign * cfg.breakout_target_r * risk
        out.append(_plan(x.close_time, "BREAKOUT_A", sign, x.c, ext, t, t, share_a, cfg, tick))
    elif (
        micro is not None
        and bb == sign
        and ((x.c > micro.vah) if sign > 0 else (x.c < micro.val))
        and ((x.c > outer) if sign > 0 else (x.c < outer))
    ):  # E4 plan B: aggressive buying breaks the micro range's value-area high
        ext = x.l if sign > 0 else x.h
        risk = abs(x.c - ext) + cfg.stop_buffer_ticks * tick
        t = x.c + sign * cfg.breakout_target_r * risk
        out.append(_plan(x.close_time, "BREAKOUT_B", sign, x.c, ext, t, t, D(1) - share_a, cfg, tick))
    return out


def _follow(sig: AuctionSignal, bars: Sequence[MBar]) -> None:
    """Outcome on later bars to the full target (stop first when one bar touches both)."""
    s = sig.direction.sign
    sig.outcome = "OPEN"
    for b in bars:
        if b.close_time <= sig.time:
            continue
        if (b.l <= sig.stop) if s > 0 else (b.h >= sig.stop):
            sig.outcome, sig.exit_time = "STOP", b.close_time
            return
        if (b.h >= sig.tp2) if s > 0 else (b.l <= sig.tp2):
            sig.outcome, sig.exit_time = "TP", b.close_time
            return
