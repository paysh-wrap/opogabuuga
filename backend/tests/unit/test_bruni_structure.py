"""BRUNI STRUCTURE engine (D148): one test per rule id of docs/BRUNI_RULES.md that is built, on hand-built bars."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

from app.config import BruniStructureCfg
from app.engine import bruni_structure as B
from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction

TICK = D("0.25")
CFG = BruniStructureCfg(swing_lookback=1)
DAY1 = datetime(2026, 10, 12, 9, 30, tzinfo=B.ET)
DAY2 = datetime(2026, 10, 13, 9, 30, tzinfo=B.ET)
SETUP = [  # 15-minute o, h, l, c: swing high 110 (idx 1), three valid red candles, impulse, body breakout at idx 6
    (100, 102, 99, 101),
    (101, 110, 100, 108),
    (108, 109, 103, 104),
    (104, 105, 100, 101),
    (101, 102, 97, 98),
    (98, 105, 98, 104),
    (104, 113, 103, 112),
]


def quarter(t0, k, o, h, lo, c, v=10):
    """One 15-minute candle as 15 one-minute bars (low first, then high, then the close)."""
    o, h, lo, c = (D(str(x)) for x in (o, h, lo, c))
    st = t0 + timedelta(minutes=15 * k)
    bars = [MBar(st + timedelta(minutes=1), o, o, lo, o, D(v)), MBar(st + timedelta(minutes=2), o, h, o, o, D(v))]
    bars += [MBar(st + timedelta(minutes=m), o, o, o, o, D(v)) for m in range(3, 15)]
    return [*bars, MBar(st + timedelta(minutes=15), o, max(o, c), min(o, c), c, D(v))]


def hist(rows=SETUP):
    out: list[MBar] = []
    for k, r in enumerate(rows):
        out += quarter(DAY1, k, *r)
    return out


def C(o, h, lo, c, k=0):
    st = DAY1 + timedelta(minutes=15 * k)
    return B.Candle(st, st + timedelta(minutes=15), D(str(o)), D(str(h)), D(str(lo)), D(str(c)))


def candles(rows=SETUP):
    return [C(*r, k=i) for i, r in enumerate(rows)]


def m1(minute, o, h, lo, c):
    return MBar(DAY2 + timedelta(minutes=minute), *(D(str(x)) for x in (o, h, lo, c)), D(10))


def test_a1_one_fifteen_minute_chart_from_one_minute_bars():
    c = B.build(hist(), 15)
    assert len(c) == 7 and c[6].c == D(112) and c[1].h == D(110)
    assert B.build(hist()[:-1], 15)[-1].end == DAY1 + timedelta(minutes=90)  # the last one is not closed yet


def test_a2_breakout_is_a_body_close_beyond_the_swing():
    [bo] = B.breakouts(candles(), CFG, TICK)
    assert (bo.index, bo.direction, bo.level, bo.leg_lo) == (6, 1, D(110), D(97))
    wick_only = [*SETUP[:6], (104, 113, 103, 109)]  # the wick passes 110, the body does not
    assert B.breakouts(candles(wick_only), CFG, TICK) == []
    tiny = CFG.model_copy(update={"breakout_min_ticks": 20})  # needs 5 pt beyond
    assert B.breakouts(candles(), tiny, TICK) == []


def test_a3_a4_a5_a6_last_two_breakouts_and_the_fib_potential():
    c = [C(150, 160, 100, 150, 0), C(150, 151, 140, 141, 1), C(141, 142, 130, 131, 2)]
    p = B.Breakout(0, 1, D(150), D(100), D(200), 0)
    a = B.Breakout(1, -1, D(145), D(130), D(160), 1)
    fib = CFG.model_copy(update={"potential": "FIB"})
    assert B.context_side(c, [p], 2, fib, [], TICK) == (1, "FOLLOW_A")
    assert B.context_side(c, [p, B.Breakout(1, 1, D(1), D(1), D(2), 1)], 2, fib, [], TICK) == (1, "AGREE")  # A4
    assert B.context_side(c, [p, a], 2, fib, [], TICK) == (-1, "FOLLOW_A")  # 125 not reached
    deep = [*c, C(131, 132, 124, 126, 3)]
    assert B.context_side(deep, [p, a], 3, fib, [], TICK) == (1, "FOLLOW_P")  # A6: discount reached → follow P
    up = B.Breakout(1, 1, D(145), D(130), D(160), 1)
    pdn = B.Breakout(0, -1, D(150), D(100), D(200), 0)
    assert B.context_side([*c, C(170, 180, 169, 176, 3)], [pdn, up], 3, fib, [], TICK) == (-1, "FOLLOW_P")


def test_a7_value_area_potential():
    bars = [MBar(DAY1 + timedelta(minutes=i + 1), D(100), D(100), D(100), D(100), D(1000)) for i in range(10)]
    bars += [MBar(DAY1 + timedelta(minutes=20), D(90), D(110), D(90), D(110), D(10))]
    val, vah = B.value_area(bars, D("0.7"), D(1))
    assert val <= D(100) <= vah and vah - val < 5
    assert B.value_area([], D("0.7"), TICK) is None
    assert B.value_area([MBar(DAY1, D(1), D(1), D(1), D(1), D(0))], D("0.7"), TICK) is None
    c = [C(150, 160, 100, 150, 0), C(150, 151, 140, 141, 1), C(141, 142, 99, 100, 2)]
    p = B.Breakout(0, 1, D(150), D(100), D(200), 0)
    a = B.Breakout(1, -1, D(145), D(130), D(160), 1)
    leg = [MBar(DAY1 + timedelta(minutes=5), D(120), D(120), D(120), D(120), D(100))]
    assert B.context_side(c, [p, a], 2, CFG, leg, D(1)) == (1, "FOLLOW_P")  # the VAL (120) was taken by a wick
    assert B.context_side(c, [p, a], 2, CFG, [], D(1)) == (-1, "FOLLOW_A")  # no profile → follow A


def test_a12_no_breakout_no_trade():
    assert B.context_side(candles(), [], 6, CFG, [], TICK) == (0, "NO_BREAKOUT")
    rep = B.replay_day(hist(SETUP[:6]), [m1(1, 104, 104, 100, 101)], CFG, TICK)
    assert rep.signals == [] and rep.context == "NO_BREAKOUT"


def test_b1_valid_candle_body_larger_than_the_longest_wick():
    assert C(100, 101, 95, 96).valid and not C(100, 106, 95, 99).valid


def test_b2_b4_triple_print_zone_and_b3_two_is_not_a_zone():
    [bo] = B.breakouts(candles(), CFG, TICK)
    assert B.triple_print(candles(), bo, 1, CFG) == (D(97), D(109))
    assert B.triple_print(candles(), bo, -1, CFG) is None
    two = [SETUP[0], SETUP[1], (108, 109, 100, 107), *SETUP[3:]]  # candle 2 is no longer valid
    [bo2] = B.breakouts(candles(two), CFG, TICK)
    assert B.triple_print(candles(two), bo2, 1, CFG) is None


def test_d_entry_back_in_the_zone_and_e_target():
    rep = B.replay_day(hist(), [m1(1, 112, 112, 108, 110)], CFG, TICK)
    [s] = rep.signals
    assert s.direction == Direction.LONG and s.entry == D(110) and s.stop == D("96.5") and s.zone == (D(97), D(109))
    assert s.take_profit == D(137) and s.outcome == "OPEN"
    assert B.replay_day(hist(), [m1(1, 112, 114, 111, 113)], CFG, TICK).signals == []  # not back in the zone
    assert B.replay_day(hist(), [], CFG, TICK).skip == "BRUNI_NO_BARS"


def test_c_wick_gap_filter_off_by_default_and_skips_when_set():
    assert B.wick_gap(candles(), 1, 6) == D(1)  # lowest lows 97 and 98
    assert B.wick_gap(candles()[:1], 1, 0) is None
    assert B.wick_gap(candles(), -1, 6) == D(3)
    cfg = CFG.model_copy(update={"wick_gap_min_pts": D(2)})
    assert B.replay_day(hist(), [m1(1, 112, 112, 108, 110)], cfg, TICK).signals == []


def test_outcomes_time_exit_and_max_losses():
    today = [m1(1, 112, 112, 108, 110), m1(2, 110, 140, 110, 138)]
    assert B.replay_day(hist(), today, CFG, TICK).signals[0].outcome == "TP"
    today = [m1(1, 112, 112, 108, 110), m1(2, 110, 110, 90, 91), m1(3, 105, 105, 100, 101)]
    sigs = B.replay_day(hist(), today, CFG, TICK).signals
    assert sigs[0].outcome == "STOP" and sigs[0].lost and len(sigs) == 1  # the zone is used once
    cfg = CFG.model_copy(update={"time_exit": "09:32"})
    today = [m1(1, 112, 112, 108, 110), m1(2, 110, 111, 109, 110)]
    assert B.replay_day(hist(), today, cfg, TICK).signals[0].outcome == "TIME"
    late = CFG.model_copy(update={"last_entry": "09:30"})
    assert B.replay_day(hist(), [m1(1, 112, 112, 108, 110)], late, TICK).signals == []


def test_f6_regime_flip_only_when_the_table_says_so():
    cfg = CFG.model_copy(update={"regime_flip": True, "regime_table": {"CALM": "NORMAL"}})
    [s] = B.replay_day(hist(), [m1(1, 112, 112, 108, 110)], cfg, TICK).signals
    assert s.direction == Direction.LONG and s.regime is not None and not s.flipped
    flip = cfg.model_copy(update={"regime_table": dict.fromkeys(B.BUCKETS, "FLIP")})
    [s] = B.replay_day(hist(), [m1(1, 112, 112, 108, 110)], flip, TICK).signals
    assert s.flipped and s.direction == Direction.SHORT and s.stop == D("123.5") and s.take_profit == D(83)
    assert B.regime(candles()[:1], 0, cfg) is None
