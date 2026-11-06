"""Trend-side filters (D44, research Results L): session VWAP, EMA 200 on 5-minute bars, UT Bot on 5-minute bars.

Pure and incremental (closed bars only, no lookahead). Fed by the same TradingView heartbeat bars the engine already
receives (1m or 5m charts); 5-minute bars are built from finer bars by clock bucket. Math re-implemented from the
public formulas — built-in VWAP / EMA, and "UT Bot Alerts" (QuantNomad, open source: ATR trailing stop, key 1, ATR 10).

direction() returns +1 (bullish), −1 (bearish) or None (not warmed up yet).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

FIVE_MIN_MS = 5 * 60_000


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


@dataclass
class TrendState:
    session_key: int | None = None
    pv: Decimal = Decimal(0)
    vol: Decimal = Decimal(0)
    vwap: Decimal | None = None
    last_close: Decimal | None = None
    last_bar_ms: int | None = None
    # 5-minute bar being built: [bucket_ms, high, low, close]
    cur5: list[object] | None = None
    ema200_5m: _Ema = field(default_factory=lambda: _Ema(200))
    ut_5m: _UtBot = field(default_factory=_UtBot)
    close_5m: Decimal | None = None

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
        if tf_ms > FIVE_MIN_MS:
            return  # 5-minute indicators need bars of 5 minutes or finer
        bucket = bar_open_ms - bar_open_ms % FIVE_MIN_MS
        cur = self.cur5
        if cur is not None and cur[0] != bucket:
            self._close5(cur)
            cur = None
        if cur is None:
            cur = [bucket, h, lo, c]
        else:
            cur[1] = max(cur[1], h)  # type: ignore[call-overload]
            cur[2] = min(cur[2], lo)  # type: ignore[call-overload]
            cur[3] = c
        self.cur5 = cur
        if bar_open_ms + tf_ms >= bucket + FIVE_MIN_MS:  # this bar completes the 5-minute bucket
            self._close5(cur)
            self.cur5 = None

    def _close5(self, cur: list[object]) -> None:
        h, lo, c = cur[1], cur[2], cur[3]
        assert isinstance(h, Decimal) and isinstance(lo, Decimal) and isinstance(c, Decimal)
        self.ema200_5m.update(c)
        self.ut_5m.update(h, lo, c)
        self.close_5m = c

    def direction(self) -> dict[str, int | None]:
        def side(x: Decimal | None, ref: Decimal | None) -> int | None:
            if x is None or ref is None or x == ref:
                return None
            return 1 if x > ref else -1

        return {
            "vwap": side(self.last_close, self.vwap),
            "ema200_5m": side(self.close_5m, self.ema200_5m.value) if self.ema200_5m.ready() else None,
            "utbot_5m": (self.ut_5m.dir or None) if self.ut_5m.ready() else None,
        }
