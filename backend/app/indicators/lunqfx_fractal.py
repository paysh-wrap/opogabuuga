"""ICT fractal model — Python port of "ICT Fractal Model, HTF Candles, CISD & C2 Targets [LunqFX]".

Source: TradingView PUB;121faffd16074f3496121f174a0a0805 (open-source, no license header; © LunqFX). Verified against
the original source 2026-11-05. PERSONAL USE ONLY. Mirrors the original state machine exactly (closed bars only):

stage 0 SEARCHING → 1 C1 SWEPT (forming HTF candle takes exactly one side of the last finished candle)
→ 2 C3 RUNNING (C2 closed strictly inside C1 and did not take both sides; "Require C2 to close back inside" = ON)
→ 0 on T2 (complete), price beyond the sweep extreme (failed, even after T1), or C3 closing.
- An HTF candle is "closed" on the first chart bar of the next HTF period (timeframe.change), so confirmation and C3
  expiry are reported on that bar. The stage-0 search is skipped on that bar.
- CISD level = open of the latest run of opposite-colour candles; a deeper sweep during C2 moves the level but does
  NOT cancel a CISD already printed. CISD counts as early only if printed before the model was confirmed.
- T1 = C1 midpoint (raw), T2 = C1 opposite side, invalid = sweep extreme. T1 counts as already reached when C2 CLOSED
  beyond it (pre-ticked; no T1 event then). Targets are checked from the bar after confirmation, in order.
Additions for Paytience (not in the original): HTF ATR(14) and event payload fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.indicators.atr import WilderATR
from app.indicators.bars import MINUTE_MS, Bar, htf_open_ms

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
class FractalEngine:
    htf_minutes: int
    tick: Decimal  # kept for API compatibility (T1 is the raw midpoint, as in the original)
    atr_period: int = 14
    _atr: WilderATR = field(init=False)
    # forming HTF candle
    _hS: int | None = None
    _hO: Decimal = Decimal(0)
    _hH: Decimal = Decimal(0)
    _hL: Decimal = Decimal(0)
    _finished: list[tuple[int, Decimal, Decimal, Decimal, Decimal]] = field(default_factory=list)  # start,o,h,l,c
    _prev: Bar | None = None
    _dn_run: Decimal | None = None
    _up_run: Decimal | None = None
    _i: int = 0
    # model state
    stage: int = 0
    _dir: int = 0
    _c1: tuple[int, Decimal, Decimal] | None = None  # start, high, low
    _swX: Decimal = Decimal(0)
    _swT: int = 0
    _cisd_lvl: Decimal | None = None
    _cisd_on: bool = False
    _cisd_early: bool = False
    _t1: Decimal = Decimal(0)
    _t2: Decimal = Decimal(0)
    _inv: Decimal = Decimal(0)
    _live: int = 0
    _hit: int = 0
    _pre: bool = False
    _c3_close: int | None = None
    _atr_at_live: Decimal | None = None

    def __post_init__(self) -> None:
        self._atr = WilderATR(self.atr_period)

    @property
    def _d(self) -> Dir:
        return "LONG" if self._dir == 1 else "SHORT"

    def _fields(self) -> FractalFields:
        assert self._c1 is not None
        s, h, lo = self._c1
        t1 = (h + lo) / 2
        t2 = h if self._dir == 1 else lo
        live = self.stage == 2
        return FractalFields(
            h,
            lo,
            s,
            self._atr_at_live if live else self._atr.value,
            self._t1 if live else t1,
            self._t2 if live else t2,
            self._inv if live else self._swX,
            self._swX,
            self._swT,
            self._cisd_lvl,
            self._cisd_early if live else self._cisd_on,
            self._pre if live else False,
            self._c3_close if live else None,
        )

    def push(self, b: Bar) -> list[FractalEvent]:
        out: list[FractalEvent] = []
        span = self.htf_minutes * MINUTE_MS
        start = htf_open_ms(b.open_ms, self.htf_minutes)
        new_h = self._hS is not None and start != self._hS
        htf_closed = False
        if new_h and self._prev is not None:
            assert self._hS is not None
            self._finished.append((self._hS, self._hO, self._hH, self._hL, self._prev.c))
            del self._finished[:-12]
            cand = Bar(self._hS, self._hS + span, self._hO, self._hH, self._hL, self._prev.c)
            self._atr.push(cand)
            htf_closed = True
        if new_h or self._hS is None:
            self._hS, self._hO, self._hH, self._hL = start, b.o, b.h, b.l
        else:
            self._hH, self._hL = max(self._hH, b.h), min(self._hL, b.l)
        prev = self._prev
        if b.bearish and not (prev is not None and prev.bearish):
            self._dn_run = b.o
        if b.bullish and not (prev is not None and prev.bullish):
            self._up_run = b.o
        self._prev = b
        self._i += 1
        t = b.close_ms
        long = self._dir == 1

        # CISD: a close beyond the open of the run that delivered the sweep
        if (
            self.stage >= 1
            and not self._cisd_on
            and self._cisd_lvl is not None
            and (b.c > self._cisd_lvl if long else b.c < self._cisd_lvl)
        ):
            self._cisd_on = True
            out.append(FractalEvent("CISD", self._d, t, self._fields()))

        # stage 2: C3 running
        if self.stage == 2:
            fail = b.l < self._inv if long else b.h > self._inv
            if not fail:
                for k in (1, 2):
                    tk = self._t1 if k == 1 else self._t2
                    if self._hit == k - 1 and (b.h >= tk if long else b.l <= tk):
                        self._hit = k
                        out.append(FractalEvent("T1_HIT" if k == 1 else "T2_HIT", self._d, t, self._fields()))
            expired = htf_closed and self._i > self._live
            if fail or self._hit == 2 or expired:
                if fail:
                    out.append(FractalEvent("MODEL_FAILED", self._d, t, self._fields()))
                elif self._hit != 2:
                    out.append(FractalEvent("C3_CLOSED", self._d, t, self._fields()))
                self.stage, self._dir = 0, 0

        # stage 1: C2 has swept C1
        if self.stage == 1:
            if htf_closed:
                assert self._c1 is not None
                _, _, c2h, c2l, c2c = self._finished[-1]
                _, c1h, c1l = self._c1
                both = c2h > c1h and c2l < c1l
                inside = c1l < c2c < c1h
                if not both and inside:
                    self.stage = 2
                    self._cisd_early = self._cisd_on
                    self._live, self._hit = self._i, 0
                    self._t1 = (c1h + c1l) / 2
                    self._t2 = c1h if long else c1l
                    self._inv = self._swX
                    self._pre = c2c >= self._t1 if long else c2c <= self._t1
                    if self._pre:
                        self._hit = 1
                    assert self._hS is not None
                    self._c3_close = self._hS + span
                    self._atr_at_live = self._atr.value
                    out.append(FractalEvent("MODEL_CONFIRMED", self._d, t, self._fields()))
                else:
                    self.stage, self._dir = 0, 0
            elif b.l < self._swX if long else b.h > self._swX:
                self._swX, self._swT = (b.l if long else b.h), t
                self._cisd_lvl = self._dn_run if long else self._up_run

        # stage 0: the forming HTF candle (C2) takes the last finished one (C1)
        if self.stage == 0 and self._finished and not htf_closed:
            ps, _, ph, pl, _ = self._finished[-1]
            up, dn = self._hH > ph, self._hL < pl
            if up != dn:
                self.stage, self._dir = 1, (1 if dn else -1)
                self._c1 = (ps, ph, pl)
                self._swX, self._swT = (self._hL if dn else self._hH), t
                self._cisd_on = self._cisd_early = False
                self._cisd_lvl = self._dn_run if dn else self._up_run
                out.append(FractalEvent("C1_SWEPT", self._d, t, self._fields()))
        return out
