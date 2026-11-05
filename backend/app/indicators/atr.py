"""Wilder ATR (used for HTF ATR(14) and the C1 range filter)."""

from __future__ import annotations

from decimal import Decimal

from app.indicators.bars import Bar


class WilderATR:
    def __init__(self, period: int = 14) -> None:
        self.period = period
        self.prev_close: Decimal | None = None
        self.trs: list[Decimal] = []
        self.value: Decimal | None = None

    def push(self, b: Bar) -> Decimal | None:
        tr = (
            b.h - b.l
            if self.prev_close is None
            else max(b.h - b.l, abs(b.h - self.prev_close), abs(b.l - self.prev_close))
        )
        self.prev_close = b.c
        if self.value is None:
            self.trs.append(tr)
            if len(self.trs) == self.period:
                self.value = sum(self.trs, Decimal(0)) / self.period
        else:
            self.value = (self.value * (self.period - 1) + tr) / self.period
        return self.value
