"""Market Structure Oscillator — Paytience's spec-derived implementation (docs/INDICATOR_SPEC.md).

NOT verified against BigBeluga's original source yet (D11). Pure and deterministic: feed closed bars, get events.
Events are timestamped at the CONFIRMATION bar (pivot + right bars), never the pivot bar (§5.2).
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
    level: Decimal  # broken pivot level, or the new pivot price for divergence


@dataclass(frozen=True)
class MsoSnapshot:
    trend: Trend
    osc: Decimal | None
    raw: Decimal | None
    time_ms: int


class WilderRSI:
    def __init__(self, length: int) -> None:
        self.n = length
        self.prev: Decimal | None = None
        self.gains: list[Decimal] = []
        self.losses: list[Decimal] = []
        self.ag: Decimal | None = None
        self.al: Decimal | None = None

    def push(self, close: Decimal) -> Decimal | None:
        if self.prev is None:
            self.prev = close
            return None
        ch = close - self.prev
        self.prev = close
        g, lo = max(ch, D0), max(-ch, D0)
        if self.ag is None or self.al is None:
            self.gains.append(g)
            self.losses.append(lo)
            if len(self.gains) < self.n:
                return None
            self.ag = sum(self.gains, D0) / self.n
            self.al = sum(self.losses, D0) / self.n
        else:
            self.ag = (self.ag * (self.n - 1) + g) / self.n
            self.al = (self.al * (self.n - 1) + lo) / self.n
        if self.al == 0:
            return D100 if self.ag > 0 else D50
        rs = self.ag / self.al
        return D100 - D100 / (1 + rs)


@dataclass
class _Pivot:
    price: Decimal
    raw: Decimal | None
    consumed: bool = False


@dataclass
class MsoEngine:
    pivot_left: int = 5
    pivot_right: int = 3
    osc_length: int = 14
    trend: Trend = "NONE"
    _win: deque[tuple[Bar, Decimal | None]] = field(default_factory=deque)
    _rsi: WilderRSI | None = None
    _ph: _Pivot | None = None  # last confirmed pivot high
    _pl: _Pivot | None = None
    _prev_ph: _Pivot | None = None
    _prev_pl: _Pivot | None = None
    last: MsoSnapshot | None = None

    def __post_init__(self) -> None:
        self._rsi = WilderRSI(self.osc_length)

    def osc_for(self, raw: Decimal | None) -> Decimal | None:
        if raw is None:
            return None
        if self.trend == "BULL":
            return D50 + raw / 2
        if self.trend == "BEAR":
            return raw / 2
        return raw

    def push(self, b: Bar) -> list[MsoEvent]:
        assert self._rsi is not None
        raw = self._rsi.push(b.c)
        out: list[MsoEvent] = []
        self._win.append((b, raw))
        size = self.pivot_left + self.pivot_right + 1
        while len(self._win) > size:
            self._win.popleft()
        # 1) pivots confirmed on THIS bar (candidate is pivot_right bars back)
        if len(self._win) == size:
            bars = list(self._win)
            cand, craw = bars[self.pivot_left]
            left, right = bars[: self.pivot_left], bars[self.pivot_left + 1 :]
            if all(cand.h > x.h for x, _ in left) and all(cand.h >= x.h for x, _ in right):
                p = _Pivot(cand.h, craw)
                prev = self._ph
                if (
                    prev is not None
                    and p.price > prev.price
                    and p.raw is not None
                    and prev.raw is not None
                    and p.raw < prev.raw
                ):
                    out.append(MsoEvent("MSO_DIV", "SHORT", b.close_ms, p.price))
                self._prev_ph, self._ph = prev, p
            if all(cand.l < x.l for x, _ in left) and all(cand.l <= x.l for x, _ in right):
                p = _Pivot(cand.l, craw)
                prev = self._pl
                if (
                    prev is not None
                    and p.price < prev.price
                    and p.raw is not None
                    and prev.raw is not None
                    and p.raw > prev.raw
                ):
                    out.append(MsoEvent("MSO_DIV", "LONG", b.close_ms, p.price))
                self._prev_pl, self._pl = prev, p
        # 2) structure breaks on close
        if self._ph is not None and not self._ph.consumed and b.c > self._ph.price:
            ev: MsoName = "MSO_CHOCH" if self.trend == "BEAR" else "MSO_BOS"
            out.append(MsoEvent(ev, "LONG", b.close_ms, self._ph.price))
            self._ph.consumed, self.trend = True, "BULL"
        if self._pl is not None and not self._pl.consumed and b.c < self._pl.price:
            ev2: MsoName = "MSO_CHOCH" if self.trend == "BULL" else "MSO_BOS"
            out.append(MsoEvent(ev2, "SHORT", b.close_ms, self._pl.price))
            self._pl.consumed, self.trend = True, "BEAR"
        self.last = MsoSnapshot(self.trend, self.osc_for(raw), raw, b.close_ms)
        return out
