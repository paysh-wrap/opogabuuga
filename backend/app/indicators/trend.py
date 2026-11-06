"""Trend-side filters (D44 / D45): session VWAP, EMA 200 5m, UT Bot 5m, Squeeze Momentum rising on 5m AND 15m.

Pure and incremental (closed bars only, no lookahead). Fed by the same TradingView heartbeat bars the engine already
receives (1m or 5m charts); 5- and 15-minute bars are built from finer bars by clock bucket. Math re-implemented from
the public formulas (no copied code): built-in VWAP / EMA; "UT Bot Alerts" (QuantNomad, open source: ATR trailing
stop, key 1, ATR 10); "Squeeze Momentum Indicator" (LazyBear, open source: momentum = linreg(close − avg(avg(highest
high, lowest low), sma close), 20, 0) with length 20).

direction() returns +1 (bullish), −1 (bearish), 0 (no side: squeeze 5m and 15m disagree / flat) or None (warming up).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

FIVE_MIN_MS = 5 * 60_000
FIFTEEN_MIN_MS = 15 * 60_000


@dataclass
class _Ema:
    n: int
    value: Decimal | None = None
    count: int = 0

    def update(self, x: Decimal) -> None:
        a = Decimal(2) / (self.n + 1)
        self.value = x if self.value is None else a * x + (1 - a) * self.value
        self.count += 1

    def ready(self) -> bool:
        return self.count >= self.n


@dataclass
class _UtBot:
    key: Decimal = Decimal(1)
    n: int = 10
    atr: Decimal | None = None
    prev_close: Decimal | None = None
    stop: Decimal = Decimal(0)
    dir: int = 0
    count: int = 0

    def update(self, h: Decimal, lo: Decimal, c: Decimal) -> None:
        pc = self.prev_close
        tr = h - lo if pc is None else max(h - lo, abs(h - pc), abs(lo - pc))
        self.atr = tr if self.atr is None else (self.atr * (self.n - 1) + tr) / self.n  # RMA (Pine ta.atr)
        loss = self.key * self.atr
        if pc is not None:
            p = self.stop
            if c > p and pc > p:
                self.stop = max(p, c - loss)
            elif c < p and pc < p:
                self.stop = min(p, c + loss)
            else:
                self.stop = c - loss if c > p else c + loss
            self.dir = 1 if c > self.stop else -1
        self.prev_close = c
        self.count += 1

    def ready(self) -> bool:
        return self.count > self.n


def linreg_last(ys: list[Decimal]) -> Decimal:
    """Pine ta.linreg(y, n, 0): the least-squares line through ys (oldest first) evaluated at the newest point."""
    n = len(ys)
    xm = Decimal(n - 1) / 2
    ym = sum(ys, Decimal(0)) / n
    num = sum(((Decimal(i) - xm) * (y - ym) for i, y in enumerate(ys)), Decimal(0))
    den = sum(((Decimal(i) - xm) ** 2 for i in range(n)), Decimal(0))
    return ym + num / den * xm


@dataclass
class _Squeeze:
    """LazyBear Squeeze Momentum value per closed bar; rising() = sign of the change vs the previous bar."""

    n: int = 20
    highs: deque[Decimal] = field(default_factory=lambda: deque(maxlen=20))
    lows: deque[Decimal] = field(default_factory=lambda: deque(maxlen=20))
    closes: deque[Decimal] = field(default_factory=lambda: deque(maxlen=20))
    ys: deque[Decimal] = field(default_factory=lambda: deque(maxlen=20))
    val: Decimal | None = None
    prev: Decimal | None = None

    def update(self, h: Decimal, lo: Decimal, c: Decimal) -> None:
        self.highs.append(h)
        self.lows.append(lo)
        self.closes.append(c)
        if len(self.closes) < self.n:
            return
        basis = sum(self.closes, Decimal(0)) / self.n
        self.ys.append(c - ((max(self.highs) + min(self.lows)) / 2 + basis) / 2)
        if len(self.ys) < self.n:
            return
        self.prev, self.val = self.val, linreg_last(list(self.ys))

    def rising(self) -> int | None:
        if self.val is None or self.prev is None:
            return None
        return 1 if self.val > self.prev else -1 if self.val < self.prev else 0


@dataclass
class _Bucket:
    """Builds `ms`-long bars from finer closed bars (clock-aligned) and hands each finished bar to `emit`."""

    ms: int
    emit: Callable[[Decimal, Decimal, Decimal], None]
    cur: list[object] | None = None  # [bucket_ms, high, low, close]

    def push(self, bar_open_ms: int, tf_ms: int, h: Decimal, lo: Decimal, c: Decimal) -> None:
        bucket = bar_open_ms - bar_open_ms % self.ms
        cur = self.cur
        if cur is not None and cur[0] != bucket:
            self._close(cur)
            cur = None
        if cur is None:
            cur = [bucket, h, lo, c]
        else:
            cur[1] = max(cur[1], h)  # type: ignore[call-overload]
            cur[2] = min(cur[2], lo)  # type: ignore[call-overload]
            cur[3] = c
        self.cur = cur
        if bar_open_ms + tf_ms >= bucket + self.ms:  # this bar completes the bucket
            self._close(cur)
            self.cur = None

    def _close(self, cur: list[object]) -> None:
        h, lo, c = cur[1], cur[2], cur[3]
        assert isinstance(h, Decimal) and isinstance(lo, Decimal) and isinstance(c, Decimal)
        self.emit(h, lo, c)


@dataclass
class TrendState:
    session_key: int | None = None
    pv: Decimal = Decimal(0)
    vol: Decimal = Decimal(0)
    vwap: Decimal | None = None
    last_close: Decimal | None = None
    last_bar_ms: int | None = None
    ema200_5m: _Ema = field(default_factory=lambda: _Ema(200))
    ut_5m: _UtBot = field(default_factory=_UtBot)
    sqz_5m: _Squeeze = field(default_factory=_Squeeze)
    sqz_15m: _Squeeze = field(default_factory=_Squeeze)
    close_5m: Decimal | None = None
    b5: _Bucket = field(init=False)
    b15: _Bucket = field(init=False)

    def __post_init__(self) -> None:
        self.b5 = _Bucket(FIVE_MIN_MS, self._close5)
        self.b15 = _Bucket(FIFTEEN_MIN_MS, self.sqz_15m.update)

    def update(
        self,
        bar_open_ms: int,
        tf_ms: int,
        session_key: int,
        o: Decimal,
        h: Decimal,
        lo: Decimal,
        c: Decimal,
        v: Decimal,
    ) -> None:
        """One CLOSED bar (open time bar_open_ms, length tf_ms). Older or repeated bars are ignored."""
        if self.last_bar_ms is not None and bar_open_ms <= self.last_bar_ms:
            return
        self.last_bar_ms, self.last_close = bar_open_ms, c
        if self.session_key != session_key:  # new CME session (18:00 ET) → VWAP restarts
            self.session_key, self.pv, self.vol = session_key, Decimal(0), Decimal(0)
        w = v if v > 0 else Decimal(0)
        self.pv += (h + lo + c) / 3 * w
        self.vol += w
        if self.vol > 0:
            self.vwap = self.pv / self.vol
        if tf_ms <= FIVE_MIN_MS:  # 5-minute indicators need bars of 5 minutes or finer
            self.b5.push(bar_open_ms, tf_ms, h, lo, c)
        if tf_ms <= FIFTEEN_MIN_MS:
            self.b15.push(bar_open_ms, tf_ms, h, lo, c)

    def _close5(self, h: Decimal, lo: Decimal, c: Decimal) -> None:
        self.ema200_5m.update(c)
        self.ut_5m.update(h, lo, c)
        self.sqz_5m.update(h, lo, c)
        self.close_5m = c

    def direction(self) -> dict[str, int | None]:
        def side(x: Decimal | None, ref: Decimal | None) -> int | None:
            if x is None or ref is None or x == ref:
                return None
            return 1 if x > ref else -1

        r5, r15 = self.sqz_5m.rising(), self.sqz_15m.rising()
        sqz = None if r5 is None or r15 is None else (r5 if r5 == r15 else 0)
        return {
            "vwap": side(self.last_close, self.vwap),
            "ema200_5m": side(self.close_5m, self.ema200_5m.value) if self.ema200_5m.ready() else None,
            "utbot_5m": (self.ut_5m.dir or None) if self.ut_5m.ready() else None,
            "squeeze_5m_15m": sqz,
        }
