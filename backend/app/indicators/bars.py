"""Bar primitives shared by every indicator. Decimal prices; times are epoch milliseconds."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MINUTE_MS = 60_000


@dataclass(frozen=True)
class Bar:
    open_ms: int
    close_ms: int
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    v: Decimal = Decimal(0)

    @property
    def bullish(self) -> bool:
        return self.c > self.o

    @property
    def bearish(self) -> bool:
        return self.c < self.o


def tf_minutes(tf: str) -> int:
    """TradingView timeframe string → minutes ("1", "5", "15", "60", "1H", "240")."""
    t = tf.strip().upper()
    if t.endswith("H"):
        return int(t[:-1]) * 60
    if t.isdigit():
        return int(t)
    raise ValueError(f"unsupported timeframe {tf!r}")


def htf_open_ms(open_ms: int, htf_min: int) -> int:
    span = htf_min * MINUTE_MS
    return (open_ms // span) * span


def round_tick(x: Decimal, tick: Decimal) -> Decimal:
    return ((x / tick).quantize(Decimal(1), rounding=ROUND_HALF_UP)) * tick


class HtfAggregator:
    """Builds HTF candles from LTF bars.

    `roll(b)` closes an unfinished candle late when `b` starts a new HTF period (its last LTF bar was missing —
    TradingView closes the candle anyway). `add(b)` adds `b` and returns the candle if `b` completes it.
    """

    def __init__(self, htf_min: int) -> None:
        self.htf_min = htf_min
        self.span = htf_min * MINUTE_MS
        self.cur: Bar | None = None

    def roll(self, b: Bar) -> Bar | None:
        if self.cur is not None and htf_open_ms(b.open_ms, self.htf_min) != self.cur.open_ms:
            done, self.cur = self.cur, None
            return done
        return None

    def add(self, b: Bar) -> Bar | None:
        start = htf_open_ms(b.open_ms, self.htf_min)
        if self.cur is None:
            self.cur = Bar(start, start + self.span, b.o, b.h, b.l, b.c, b.v)
        else:
            c = self.cur
            self.cur = Bar(c.open_ms, c.close_ms, c.o, max(c.h, b.h), min(c.l, b.l), b.c, c.v + b.v)
        if b.close_ms >= self.cur.close_ms:
            done, self.cur = self.cur, None
            return done
        return None

    def push(self, b: Bar) -> list[Bar]:
        """roll + add; returns 0, 1 or 2 completed candles in order."""
        out = [x for x in (self.roll(b), self.add(b)) if x is not None]
        return out
