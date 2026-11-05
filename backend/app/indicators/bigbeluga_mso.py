"""Market Structure Oscillator — Python port of "Market Structure Oscillator [BigBeluga]".

Source: TradingView PUB;8eb87677ae7d4fcfb0a84aee27e29405 (open-source), © BigBeluga,
licensed CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/). This port is a derivative work under
the same license — PERSONAL / NON-COMMERCIAL USE ONLY. Verified against the original source 2026-11-05.

Original logic (mirrored exactly):
- structure: ta.pivothigh/low(5, 5); close crossing over the latest unbroken swing high → bullish break (count +1,
  bear count reset); first break in a direction = "ChoCh", later ones = "BoS"; the swing is then consumed.
- oscillator: roc = change(close, 14); vol = stdev(change(close), 14); raw = roc/vol; sigmoid = 100/(1+e^-raw);
  smoothed = ema(sigmoid, 10); trend-filtered = 50 ± |smoothed − 50| (above 50 only while trend is up).
- divergence: pivots (5, 5) of the SMOOTHED oscillator; price = high/low at that pivot bar; higher price + lower osc
  → bearish; lower price + higher osc → bullish. Events stamped at the confirmation bar (pivot + right bars).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.indicators.bars import Bar

Trend = Literal["BULL", "BEAR", "NONE"]
MsoName = Literal["MSO_CHOCH", "MSO_BOS", "MSO_DIV"]
D0, D50, D100 = Decimal(0), Decimal(50), Decimal(100)


@dataclass(frozen=True)
class MsoEvent:
    event: MsoName
    direction: Literal["LONG", "SHORT"]
    confirm_time_ms: int
    level: Decimal


@dataclass(frozen=True)
class MsoSnapshot:
    trend: Trend
    osc: Decimal | None  # trend-filtered oscillator (0–100)
    raw: Decimal | None  # smoothed momentum line (before trend filter)
    time_ms: int


def _pivot(values: list[Decimal], left: int, high: bool) -> bool:
    """TradingView-style pivot on a window of left+right+1 values: candidate strictly beyond the left side and not
    exceeded on the right side."""
    c = values[left]
    lft, rgt = values[:left], values[left + 1 :]
    if high:
        return all(c > x for x in lft) and all(c >= x for x in rgt)
    return all(c < x for x in lft) and all(c <= x for x in rgt)


@dataclass
class MsoEngine:
    pivot_left: int = 5
    pivot_right: int = 5
    mom_length: int = 14
    smooth_length: int = 10
    div_left: int = 5
    div_right: int = 5
    trend: Trend = "NONE"
    last: MsoSnapshot | None = None
    _bars: deque[Bar] = field(default_factory=deque)
    _closes: deque[Decimal] = field(default_factory=deque)
    _sig_seed: list[Decimal] = field(default_factory=list)
    _ema: Decimal | None = None
    _osc_win: deque[tuple[Decimal | None, Bar]] = field(default_factory=deque)
    _hi: Decimal | None = None
    _lo: Decimal | None = None
    _bull_n: int = 0
    _bear_n: int = 0
    _prev_close: Decimal | None = None
    _prev_osc_hi: tuple[Decimal, Decimal] | None = None  # (osc, price)
    _prev_osc_lo: tuple[Decimal, Decimal] | None = None

    def _momentum(self, c: Decimal) -> Decimal | None:
        self._closes.append(c)
        while len(self._closes) > self.mom_length + 1:
            self._closes.popleft()
        if len(self._closes) < self.mom_length + 1:
            return None
        cl = list(self._closes)
        roc = cl[-1] - cl[0]
        changes = [cl[i] - cl[i - 1] for i in range(1, len(cl))]
        mean = sum(changes, D0) / len(changes)
        var = sum(((x - mean) ** 2 for x in changes), D0) / len(changes)  # population stdev (ta.stdev default)
        vol = var.sqrt()
        raw = roc / vol if vol != 0 else D0
        sig = D100 / (1 + (-raw).exp())
        if self._ema is None:  # ta.ema seeds with the SMA of the first `length` values
            self._sig_seed.append(sig)
            if len(self._sig_seed) < self.smooth_length:
                return None
            self._ema = sum(self._sig_seed, D0) / self.smooth_length
        else:
            alpha = Decimal(2) / (self.smooth_length + 1)
            self._ema = alpha * sig + (1 - alpha) * self._ema
        return self._ema

    def push(self, b: Bar) -> list[MsoEvent]:
        out: list[MsoEvent] = []
        # structure pivots (confirmed pivot_right bars later)
        self._bars.append(b)
        size = self.pivot_left + self.pivot_right + 1
        while len(self._bars) > size:
            self._bars.popleft()
        if len(self._bars) == size:
            bars = list(self._bars)
            if _pivot([x.h for x in bars], self.pivot_left, True):
                self._hi = bars[self.pivot_left].h
            if _pivot([x.l for x in bars], self.pivot_left, False):
                self._lo = bars[self.pivot_left].l
        prev = self._prev_close
        # ta.crossover(close, level): close > level and close[1] <= level
        if self._hi is not None and prev is not None and b.c > self._hi >= prev:
            self._bull_n, self._bear_n, self.trend = self._bull_n + 1, 0, "BULL"
            out.append(MsoEvent("MSO_CHOCH" if self._bull_n <= 1 else "MSO_BOS", "LONG", b.close_ms, self._hi))
            self._hi = None
        if self._lo is not None and prev is not None and b.c < self._lo <= prev:
            self._bear_n, self._bull_n, self.trend = self._bear_n + 1, 0, "BEAR"
            out.append(MsoEvent("MSO_CHOCH" if self._bear_n <= 1 else "MSO_BOS", "SHORT", b.close_ms, self._lo))
            self._lo = None
        self._prev_close = b.c
        smoothed = self._momentum(b.c)
        osc = None
        if smoothed is not None:
            off = abs(smoothed - D50)
            osc = D50 + off if self.trend == "BULL" else D50 - off  # isTrendUp starts false in the original
        # divergence on pivots of the smoothed oscillator
        self._osc_win.append((smoothed, b))
        dsize = self.div_left + self.div_right + 1
        while len(self._osc_win) > dsize:
            self._osc_win.popleft()
        if len(self._osc_win) == dsize and all(v is not None for v, _ in self._osc_win):
            vals = [v for v, _ in self._osc_win if v is not None]
            cand_bar = self._osc_win[self.div_left][1]
            if _pivot(vals, self.div_left, True):
                cur = (vals[self.div_left], cand_bar.h)
                p = self._prev_osc_hi
                if p is not None and cur[1] > p[1] and cur[0] < p[0]:
                    out.append(MsoEvent("MSO_DIV", "SHORT", b.close_ms, cur[1]))
                self._prev_osc_hi = cur
            if _pivot(vals, self.div_left, False):
                cur = (vals[self.div_left], cand_bar.l)
                p = self._prev_osc_lo
                if p is not None and cur[1] < p[1] and cur[0] > p[0]:
                    out.append(MsoEvent("MSO_DIV", "LONG", b.close_ms, cur[1]))
                self._prev_osc_lo = cur
        self.last = MsoSnapshot(self.trend, osc, smoothed, b.close_ms)
        return out
