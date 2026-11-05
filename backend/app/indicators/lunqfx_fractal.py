"""ICT fractal model — Paytience's spec-derived implementation (docs/INDICATOR_SPEC.md).

NOT verified against LunqFX's original source yet (D11). Pure and deterministic: feed closed LTF bars, get events.
"Require C2 to close back inside C1" is always ON (pillar).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.indicators.atr import WilderATR
from app.indicators.bars import Bar, HtfAggregator, round_tick

Dir = Literal["LONG", "SHORT"]
EventName = Literal["C1_SWEPT", "CISD", "MODEL_CONFIRMED", "T1_HIT", "T2_HIT", "MODEL_FAILED", "C3_CLOSED"]


@dataclass(frozen=True)
class FractalFields:
    c1_high: Decimal
    c1_low: Decimal
    c1_time_ms: int
    htf_atr14: Decimal | None
    t1: Decimal
    t2: Decimal
    invalid: Decimal
    sweep_extreme: Decimal
    sweep_time_ms: int
    cisd_level: Decimal | None
    cisd_before_c2_close: bool
    t1_preticked: bool
    c3_close_time_ms: int | None


@dataclass(frozen=True)
class FractalEvent:
    event: EventName
    direction: Dir
    time_ms: int
    fields: FractalFields


@dataclass
class _Side:
    """Sweep + CISD tracker for one side of C1 (LONG = low side swept, SHORT = high side swept)."""

    direction: Dir
    c1: Bar
    swept: bool = False
    extreme: Decimal = Decimal(0)
    extreme_time: int = 0
    cisd_level: Decimal | None = None
    cisd_time: int | None = None
    t1_touched: bool = False

    def past(self, price: Decimal, ref: Decimal) -> bool:
        """price is beyond ref in the sweep direction (below for LONG, above for SHORT)."""
        return price < ref if self.direction == "LONG" else price > ref

    def sweep_price(self, b: Bar) -> Decimal:
        return b.l if self.direction == "LONG" else b.h

    def closes_through_cisd(self, b: Bar) -> bool:
        if self.cisd_level is None:
            return False
        return b.c > self.cisd_level if self.direction == "LONG" else b.c < self.cisd_level


@dataclass
class _Model:
    side: _Side
    t1: Decimal
    t2: Decimal
    atr: Decimal | None
    c3_close_ms: int
    cisd_before_c2_close: bool
    t1_preticked: bool
    t1_hit: bool = False
    done: bool = False  # failed or T2 reached


@dataclass
class FractalEngine:
    htf_minutes: int
    tick: Decimal
    atr_period: int = 14
    _agg: HtfAggregator = field(init=False)
    _atr: WilderATR = field(init=False)
    _c1: Bar | None = None
    _sides: list[_Side] = field(default_factory=list)
    _model: _Model | None = None
    _prev: Bar | None = None
    _bear_run_open: Decimal | None = None  # open of first candle of the latest bearish run
    _bull_run_open: Decimal | None = None

    def __post_init__(self) -> None:
        self._agg = HtfAggregator(self.htf_minutes)
        self._atr = WilderATR(self.atr_period)

    # ---------- field builders ----------
    def _targets(self, s: _Side) -> tuple[Decimal, Decimal]:
        t1 = round_tick((s.c1.h + s.c1.l) / 2, self.tick)
        return t1, (s.c1.h if s.direction == "LONG" else s.c1.l)

    def _fields(
        self, s: _Side, *, atr: Decimal | None, c3_close: int | None, cisd_before: bool, preticked: bool
    ) -> FractalFields:
        t1, t2 = self._targets(s)
        return FractalFields(
            s.c1.h,
            s.c1.l,
            s.c1.open_ms,
            atr,
            t1,
            t2,
            s.extreme,
            s.extreme,
            s.extreme_time,
            s.cisd_level,
            cisd_before,
            preticked,
            c3_close,
        )

    def _model_fields(self, m: _Model) -> FractalFields:
        return self._fields(
            m.side, atr=m.atr, c3_close=m.c3_close_ms, cisd_before=m.cisd_before_c2_close, preticked=m.t1_preticked
        )

    # ---------- steps ----------
    def _update_runs(self, b: Bar) -> None:
        if b.bearish and not (self._prev is not None and self._prev.bearish):
            self._bear_run_open = b.o
        if b.bullish and not (self._prev is not None and self._prev.bullish):
            self._bull_run_open = b.o
        self._prev = b

    def _on_htf_close(self, c2: Bar, now_ms: int, out: list[FractalEvent]) -> None:
        atr = self._atr.push(c2)
        swept = [s for s in self._sides if s.swept]
        c1 = self._c1
        if c1 is not None and len(swept) == 1 and c1.l < c2.c < c1.h:  # pillar: close back inside C1
            s = swept[0]
            t1, t2 = self._targets(s)
            cisd_before = s.cisd_time is not None
            m = _Model(s, t1, t2, atr, c2.close_ms + self._agg.span, cisd_before, s.t1_touched)
            self._model = m
            out.append(FractalEvent("MODEL_CONFIRMED", s.direction, now_ms, self._model_fields(m)))
        self._c1 = c2
        self._sides = []

    def _manage_model(self, b: Bar, out: list[FractalEvent]) -> None:
        m = self._model
        if m is None:
            return
        if b.close_ms > m.c3_close_ms:  # C3's last bar was missing → close late
            out.append(FractalEvent("C3_CLOSED", m.side.direction, b.close_ms, self._model_fields(m)))
            self._model = None
            return
        s, d = m.side, m.side.direction
        if not m.done:
            if not m.t1_hit and s.past(s.sweep_price(b), s.extreme):  # same-bar T1 + invalid → FAILED
                m.done = True
                out.append(FractalEvent("MODEL_FAILED", d, b.close_ms, self._model_fields(m)))
            else:
                if s.cisd_time is None and s.closes_through_cisd(b):
                    s.cisd_time = b.close_ms
                    out.append(FractalEvent("CISD", d, b.close_ms, self._model_fields(m)))
                reach = b.h if d == "LONG" else b.l
                if not m.t1_hit and (reach >= m.t1 if d == "LONG" else reach <= m.t1):
                    m.t1_hit = True
                    out.append(FractalEvent("T1_HIT", d, b.close_ms, self._model_fields(m)))
                if m.t1_hit and (reach >= m.t2 if d == "LONG" else reach <= m.t2):
                    m.done = True
                    out.append(FractalEvent("T2_HIT", d, b.close_ms, self._model_fields(m)))
        if b.close_ms == m.c3_close_ms:
            out.append(FractalEvent("C3_CLOSED", d, b.close_ms, self._model_fields(m)))
            self._model = None

    def _track_c2(self, b: Bar, out: list[FractalEvent]) -> None:
        c1 = self._c1
        if c1 is None:
            return
        if not self._sides:
            self._sides = [_Side("LONG", c1), _Side("SHORT", c1)]
        atr = self._atr.value
        for s in self._sides:
            price = s.sweep_price(b)
            ref = s.extreme if s.swept else (c1.l if s.direction == "LONG" else c1.h)
            if s.past(price, ref):
                first = not s.swept
                s.swept, s.extreme, s.extreme_time = True, price, b.close_ms
                run = self._bear_run_open if s.direction == "LONG" else self._bull_run_open
                s.cisd_level, s.cisd_time = (run if run is not None else b.o), None
                if first:
                    out.append(
                        FractalEvent(
                            "C1_SWEPT",
                            s.direction,
                            b.close_ms,
                            self._fields(s, atr=atr, c3_close=None, cisd_before=False, preticked=False),
                        )
                    )
            elif s.swept:
                if s.cisd_time is None and s.closes_through_cisd(b):
                    s.cisd_time = b.close_ms
                    out.append(
                        FractalEvent(
                            "CISD",
                            s.direction,
                            b.close_ms,
                            self._fields(s, atr=atr, c3_close=None, cisd_before=True, preticked=s.t1_touched),
                        )
                    )
                t1, _ = self._targets(s)
                if b.h >= t1 if s.direction == "LONG" else b.l <= t1:
                    s.t1_touched = True

    def push(self, b: Bar) -> list[FractalEvent]:
        out: list[FractalEvent] = []
        self._update_runs(b)
        late = self._agg.roll(b)
        if late is not None:
            self._on_htf_close(late, b.close_ms, out)
        self._manage_model(b, out)
        self._track_c2(b, out)
        done = self._agg.add(b)
        if done is not None:
            self._on_htf_close(done, b.close_ms, out)
        return out
