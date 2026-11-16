"""JJ F.P.T STRAT — JJ's Fair Pricing Theory, built ONLY from his transcripts (docs/JJ_FPT_RULES.md). PURE.

Rule numbers (#n) refer to docs/JJ_FPT_RULES.md. Closed 1-minute bars only, no lookahead.

A session is replayed bar by bar from its open every time a new bar closes (deterministic: live, paper and backtest
call the same `replay`). Each bar can produce at most one signal:

  continuation (minute 0–4, #14–#20): opening-candle colour, must break the previous candle; later bars inside the
      first 5 minutes enter on a break of structure in that direction. Body > 25 → 50 / 76, else 25 / 38.
  reversion (minute 5–89, #21–#27): toward fair price only. BREAK OF STRUCTURE (close beyond the latest unbroken
      3-bar swing) or DISPLACEMENT (body > previous body, close beyond the previous wick, previous candle the
      opposite colour). Room to fair ≥ 30 → 25 / 38; 15–30 → 12.5 / 19; < 15 → none. After 2 losses in a row only
      breaks of structure; 3 losses in a row → the session is done.
  fair price (#7–#13): the session open (or the pre-news / 6 PM / 09:30 price the caller gives); a break of
      structure AWAY from fair that closes ≥ adjust_min_pts beyond it moves fair to the middle of the most recent
      consolidation (the bars before the break) and restarts the loss count.

Each signal's outcome is followed on later bars (stop first when one bar touches both) — that is how the loss rules
know what happened, independent of which account took the trade.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from app.engine.lucid_fit import contracts_for as contracts_for  # D144: moved to lucid_fit, re-exported
from app.engine.lucid_fit import trade_risk_usd as trade_risk_usd
from app.engine.trade_plan import Direction

D = Decimal


@dataclass(frozen=True)
class JBar:
    close_time: datetime  # aware
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal

    @property
    def color(self) -> int:  # +1 green, −1 red, 0 doji
        return 1 if self.c > self.o else -1 if self.c < self.o else 0

    @property
    def body(self) -> Decimal:
        return abs(self.c - self.o)


class Params(Protocol):
    """The JJ settings the engine reads (config.JjFptCfg)."""

    @property
    def window_minutes(self) -> int: ...

    @property
    def continuation_minutes(self) -> int: ...

    @property
    def base_stop_pts(self) -> Decimal: ...

    @property
    def base_target_pts(self) -> Decimal: ...

    @property
    def big_open_body_pts(self) -> Decimal: ...

    @property
    def big_stop_pts(self) -> Decimal: ...

    @property
    def big_target_pts(self) -> Decimal: ...

    @property
    def room_full_min_pts(self) -> Decimal: ...

    @property
    def small_room_tier(self) -> bool: ...

    @property
    def room_small_min_pts(self) -> Decimal: ...

    @property
    def small_stop_pts(self) -> Decimal: ...

    @property
    def small_target_pts(self) -> Decimal: ...

    @property
    def bos_only_after_losses(self) -> int: ...

    @property
    def stop_after_losses(self) -> int: ...

    @property
    def adapt_fair_price(self) -> bool: ...

    @property
    def adjust_min_pts(self) -> Decimal: ...

    @property
    def consolidation_bars(self) -> int: ...

    @property
    def wick_rejection_filter(self) -> bool: ...

    @property
    def htf_filter(self) -> bool: ...

    @property
    def combine_candles(self) -> int: ...

    @property
    def extend_under_trades(self) -> int: ...

    @property
    def extend_minutes(self) -> int: ...


@dataclass(frozen=True)
class SessionInput:
    """What the caller knows about the session (all prices from stored bars / the calendar)."""

    name: str  # NY | NEWS | NY_PM | 6PM | ASIA
    open_at: datetime  # aware: open time of the session's first 1-minute bar
    fair: Decimal | None = None  # fair price given by the caller (pre-news, 09:30, …); None → the session open
    news_fair: Decimal | None = None  # NY on an 8:30 news day: the pre-news price (#9)
    alt_fair: Decimal | None = None  # ASIA: the 6 PM open (#12)
    continuation: bool = True  # NEWS session: False (#20)
    htf_bias: int | None = None  # +1 / −1 = reverse of the previous 6–12 h (#15); None = unknown (filter passes)
    gap_prior_close: Decimal | None = None  # 6 PM: last close before the daily break (#19)
    window: int | None = None  # minutes; None = cfg.window_minutes (+ the #6 extension). NEWS: 08:30 → 09:30


@dataclass
class JjSignal:
    index: int  # index into the bars passed to replay
    at: datetime
    kind: str  # CONTINUATION | BREAK_OF_STRUCTURE | DISPLACEMENT
    direction: Direction
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    stop_pts: Decimal
    target_pts: Decimal
    fair: Decimal
    room: Decimal | None
    tier: str  # BASE | BIG_OPEN | SMALL_ROOM
    epoch: int
    outcome: str = "OPEN"  # WIN | LOSS | OPEN
    resolved_index: int | None = None

    @property
    def rr(self) -> Decimal:
        return (self.target_pts / self.stop_pts).quantize(D("0.01"))


@dataclass
class Replay:
    signals: list[JjSignal] = field(default_factory=list)
    fair: Decimal | None = None
    fair_changes: list[tuple[int, Decimal]] = field(default_factory=list)  # (bar index, new fair)
    stopped_at: int | None = None  # bar index where 3 losses in a row ended the session
    notes: list[str] = field(default_factory=list)


def minute_of(bar: JBar, open_at: datetime) -> int:
    """Minutes from the session open to the bar's OPEN (0 = the opening candle)."""
    return int((bar.close_time - timedelta(minutes=1) - open_at).total_seconds() // 60)


def _resolve(sig: JjSignal, bars: Sequence[JBar], upto: int) -> None:
    """Follow an open signal through bars index+1 … upto. Stop first when one bar touches both."""
    if sig.outcome != "OPEN":
        return
    start = sig.index + 1 if sig.resolved_index is None else sig.resolved_index + 1
    for j in range(start, upto + 1):
        b = bars[j]
        if sig.direction is Direction.LONG:
            hit_stop, hit_tp = b.l <= sig.stop, b.h >= sig.take_profit
        else:
            hit_stop, hit_tp = b.h >= sig.stop, b.l <= sig.take_profit
        if hit_stop or hit_tp:
            sig.outcome = "LOSS" if hit_stop else "WIN"
            sig.resolved_index = j
            return
    sig.resolved_index = upto


def _losses_in_row(signals: Sequence[JjSignal], upto: int, epoch: int) -> int:
    done = sorted(
        (s for s in signals if s.outcome != "OPEN" and s.resolved_index is not None and s.resolved_index <= upto),
        key=lambda s: (s.resolved_index, s.index),
    )
    n = 0
    for s in done:
        if s.epoch != epoch:
            continue
        n = n + 1 if s.outcome == "LOSS" else 0
    return n


def _displacement(bars: Sequence[JBar], i: int, d: int, combine: int) -> bool:
    """#22 + #23: candle(s) in direction d, body larger than the previous (opposite-colour) candle's body, closing
    beyond that candle's wick. combine > 1 lets 2…combine same-colour candles count as one (#22 discretion; off)."""
    for n in range(1, max(1, combine) + 1):
        first = i - n + 1
        prev = first - 1
        if prev < 0:
            return False
        group = bars[first : i + 1]
        if any(b.color != d for b in group):
            return False  # the group must be all in the direction (a larger n can only add more candles)
        p = bars[prev]
        if p.color != -d:
            continue
        body = abs(bars[i].c - bars[first].o)
        beyond = bars[i].c < p.l if d < 0 else bars[i].c > p.h
        if body > p.body and beyond:
            return True
    return False


@dataclass
class _Swings:
    """3-bar swings (#24): a wick lower (higher) than the candle before AND after it; confirmed one bar later."""

    lows: list[tuple[int, Decimal]] = field(default_factory=list)  # unbroken swing lows (index, level)
    highs: list[tuple[int, Decimal]] = field(default_factory=list)

    def confirm(self, bars: Sequence[JBar], i: int) -> None:
        j = i - 1  # bar i confirms a swing at j
        if j < 1:
            return
        a, b, c = bars[j - 1], bars[j], bars[i]
        if b.l < a.l and b.l < c.l:
            self.lows.append((j, b.l))
        if b.h > a.h and b.h > c.h:
            self.highs.append((j, b.h))

    def broken(self, close: Decimal, d: int) -> bool:
        """True when this close breaks the most recent unbroken swing in direction d; every swing it closes beyond
        is marked broken (structure is used once)."""
        if d < 0:
            hit = bool(self.lows) and close < self.lows[-1][1]
            self.lows = [x for x in self.lows if close >= x[1]]
        else:
            hit = bool(self.highs) and close > self.highs[-1][1]
            self.highs = [x for x in self.highs if close <= x[1]]
        return hit


def _dir(d: int) -> Direction:
    return Direction.LONG if d > 0 else Direction.SHORT


def _make(
    i: int, bar: JBar, kind: str, d: int, stop_pts: Decimal, tp_pts: Decimal, fair: Decimal,
    room: Decimal | None, tier: str, epoch: int,
) -> JjSignal:  # fmt: skip
    return JjSignal(
        i, bar.close_time, kind, _dir(d), bar.c, bar.c - d * stop_pts, bar.c + d * tp_pts, stop_pts, tp_pts,
        fair, room, tier, epoch,
    )  # fmt: skip


def replay(bars: Sequence[JBar], start: int, s: SessionInput, cfg: Params) -> Replay:
    """Replay one session. `bars` = closed 1-minute bars in time order (a few bars BEFORE the session open may be
    included for structure); `start` = index of the opening candle. Returns every signal so far with its outcome."""
    out = Replay()
    if start >= len(bars) or start < 0:
        return out
    open_bar = bars[start]
    fair = s.fair if s.fair is not None else open_bar.o
    window = s.window or cfg.window_minutes
    extend_on = s.window is None and cfg.extend_under_trades > 0
    sw = _Swings()
    for i in range(1, start + 1):
        sw.confirm(bars, i)  # structure formed before the open counts (#14 "previous candles")
    epoch = 0
    cont_dir = 0
    stopped = False
    for i in range(start, len(bars)):
        bar = bars[i]
        m = minute_of(bar, s.open_at)
        if i > start:
            sw.confirm(bars, i)
        for x in out.signals:
            _resolve(x, bars, i)
        if m >= window:
            extra = extend_on and len(out.signals) < cfg.extend_under_trades
            if not extra or m >= window + cfg.extend_minutes:  # #6: sometimes past 11:00 when < 10 trades
                # still follow the open signals' outcomes, no new entries
                continue
        if m < 0:
            continue
        if i == start and m == 0:
            if s.news_fair is not None:  # #9: the open continues away from the pre-news price → the open is fair
                away = (bar.o - s.news_fair) * bar.color > 0
                fair = bar.o if away else s.news_fair
            elif s.alt_fair is not None:  # #12 Asia: first move goes to the 6 PM open → 6 PM is fair
                fair = s.alt_fair if (s.alt_fair - bar.o) * bar.color > 0 else bar.o
            out.fair = fair
        if stopped:
            continue
        losses = _losses_in_row(out.signals, i - 1, epoch)  # outcomes known before this bar closed
        if losses >= cfg.stop_after_losses:
            stopped = True
            out.stopped_at = i
            out.notes.append(f"STOP_{cfg.stop_after_losses}_LOSSES")
            continue
        sig: JjSignal | None = None
        cont_minutes = cfg.continuation_minutes if s.continuation else 1  # #20 NEWS: revert from the next candle
        if m < cont_minutes:
            if not s.continuation:  # the news candle itself: no trade
                _ = sw.broken(bar.c, 1), sw.broken(bar.c, -1)  # keep structure state in step
                continue
            big = open_bar.body > cfg.big_open_body_pts  # #18
            stop_pts, tp_pts, tier = (
                (cfg.big_stop_pts, cfg.big_target_pts, "BIG_OPEN")
                if big
                else (cfg.base_stop_pts, cfg.base_target_pts, "BASE")
            )
            if i == start:
                d = bar.color
                prev = bars[i - 1] if i > 0 else None
                ok = d != 0 and prev is not None and (bar.c > prev.h if d > 0 else bar.c < prev.l)  # #14
                if ok and cfg.wick_rejection_filter:  # #16: a wick rejecting this side at least as big as the body
                    wick = bar.h - max(bar.o, bar.c) if d > 0 else min(bar.o, bar.c) - bar.l
                    ok = wick < bar.body
                if ok and cfg.htf_filter and s.htf_bias is not None:
                    ok = d == s.htf_bias  # #15
                if ok and s.gap_prior_close is not None:  # #19: 6 PM gap
                    fill = 1 if s.gap_prior_close > bar.o else -1 if s.gap_prior_close < bar.o else d
                    filled = bar.l <= s.gap_prior_close <= bar.h
                    ok = d == fill or filled
                _ = sw.broken(bar.c, 1), sw.broken(bar.c, -1)
                if ok:
                    cont_dir = d
                    sig = _make(i, bar, "CONTINUATION", d, stop_pts, tp_pts, fair, None, tier, epoch)
                else:
                    cont_dir = 0
            else:
                up, down = sw.broken(bar.c, 1), sw.broken(bar.c, -1)
                if cont_dir and (up if cont_dir > 0 else down):  # #17
                    sig = _make(i, bar, "CONTINUATION", cont_dir, stop_pts, tp_pts, fair, None, tier, epoch)
        else:
            side = 1 if bar.c < fair else -1 if bar.c > fair else 0  # #21: toward fair
            up, down = sw.broken(bar.c, 1), sw.broken(bar.c, -1)
            away = (down and side > 0) or (up and side < 0)  # broke structure further from fair (#10)
            if cfg.adapt_fair_price and away and abs(bar.c - fair) >= cfg.adjust_min_pts:
                lo = max(start, i - cfg.consolidation_bars)
                cons = bars[lo:i] or [bar]
                fair = (max(b.h for b in cons) + min(b.l for b in cons)) / 2
                epoch += 1
                out.fair_changes.append((i, fair))
                out.fair = fair
                side = 1 if bar.c < fair else -1 if bar.c > fair else 0
            if side == 0:
                continue
            bos = up if side > 0 else down
            kind = None
            if bos:
                kind = "BREAK_OF_STRUCTURE"
            elif losses < cfg.bos_only_after_losses and _displacement(bars, i, side, cfg.combine_candles):
                kind = "DISPLACEMENT"  # #26: after 2 losses only breaks of structure
            if kind is None:
                continue
            room = abs(fair - bar.c)
            if room >= cfg.room_full_min_pts:  # #25
                sig = _make(i, bar, kind, side, cfg.base_stop_pts, cfg.base_target_pts, fair, room, "BASE", epoch)
            elif cfg.small_room_tier and room >= cfg.room_small_min_pts:
                sig = _make(
                    i, bar, kind, side, cfg.small_stop_pts, cfg.small_target_pts, fair, room, "SMALL_ROOM", epoch
                )
        if sig is not None:
            out.signals.append(sig)
    out.fair = fair
    return out


def htf_bias(session_open: Decimal, price_hours_ago: Decimal | None) -> int | None:
    """#15: the higher-time-frame bias is the REVERSE of the previous 6–12 hours' move."""
    if price_hours_ago is None or session_open == price_hours_ago:
        return None
    return -1 if session_open > price_hours_ago else 1
