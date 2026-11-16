"""CANDACE ICT SCALP engine (D149): one test per rule id of docs/CANDACE_ICT_RULES.md that is built."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

from app.config import CandaceIctCfg
from app.engine import candace_ict as K
from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction

TICK = D("0.25")
T9 = datetime(2026, 10, 13, 9, 0, tzinfo=K.ET)
CFG = CandaceIctCfg(premium_pct=D("0.2"))
SETUP = [
    (100, 101, 99, 100), (100, 103, 100, 102), (102, 105, 101, 104), (104, 104, 101, 102), (102, 103, 100, 101),
    (101, 102, 99, 100), (100, 101, 99, 100),
    (100, 102, 100, 102), (102, 106, 102, 106), (106, 108, 104, 107),  # bullish FVG 102–104 on the run up
    (107, 109, 104.5, 104.5),  # sweeps the 108 session high, closes back below
    (104.5, 104.5, 100, 100.5),  # displacement body closes through the FVG → IFVG
    (100.5, 102.5, 100.25, 101.5),  # retrace into it → SHORT
]  # fmt: skip


def bars(rows=SETUP, t0=T9):
    return [MBar(t0 + timedelta(minutes=i + 1), *(D(str(x)) for x in r), D(10)) for i, r in enumerate(rows)]


def test_c1_fvg_and_a1_hourly_candles():
    f = K.fvgs(bars())
    assert any((x.color, x.lo, x.hi) == (1, D(102), D(104)) for x in f)
    assert any(x.color == -1 for x in K.fvgs(bars([(110, 111, 109, 110), (110, 110, 100, 101), (101, 105, 99, 100)])))
    hr = K.hourly(bars([(100, 101, 99, 100)] * 61))
    assert len(hr) == 1 and hr[0].close_time == T9 + timedelta(hours=1)


def test_a3_pools_equal_swing_prev_day_session_fvg():
    flat = (100, 101, 99, 100)
    eq = bars([flat, flat, (100, 105, 100, 101), (101, 102, 99, 100), flat, (100, 105.25, 99, 101), (101, 102, 99, 100),
               flat, flat])  # fmt: skip
    pl = K.pools(bars([(90, 120, 80, 100)]), eq, [], CFG, TICK)
    kinds = {(p.kind, p.side) for p in pl}
    assert {("PDH", 1), ("PDL", -1), ("SESSION", 1), ("SESSION", -1), ("EQUAL", 1)} <= kinds
    h1 = bars([(100, 101, 99, 100), (101, 103, 101, 103), (104, 106, 104, 105)])
    assert any(p.kind == "FVG1H" for p in K.pools([], [], h1, CFG, TICK))


def test_a4_c2_c3_c5_sweep_ifvg_retrace_short():
    [s] = K.replay_day([], bars(), CFG, TICK).signals
    assert s.direction == Direction.SHORT and s.entry == D("101.5") and s.swept.kind == "SESSION"
    assert s.time == T9 + timedelta(minutes=13) and s.session == "NY"


def test_c5_no_displacement_no_ifvg():
    weak = [*SETUP[:11], (104.5, 104.5, 102.25, 102.5), *SETUP[12:]]  # closes inside the FVG
    assert K.replay_day([], bars(weak), CFG, TICK).signals == []
    slow = CFG.model_copy(update={"displacement_mult": D(10)})
    assert K.replay_day([], bars(), slow, TICK).signals == []


def test_a2_premium_discount():
    assert K.replay_day([], bars(), CandaceIctCfg(), TICK).signals == []  # default 50%: 101.5 is in discount


def test_d1_d2_stop_beyond_the_sweep_and_max_stop():
    [s] = K.replay_day([], bars(), CFG, TICK).signals
    assert s.stop == D("109.5")
    tight = CFG.model_copy(update={"ny_max_stop_pts": D(5)})
    assert K.replay_day([], bars(), tight, TICK).signals == []  # never widen: skip


def test_d3_target_at_least_2r_or_the_nearest_pool_beyond():
    [s] = K.replay_day([], bars(), CFG, TICK).signals
    assert s.take_profit == D("85.5")  # 2R, no pool further away
    prev = bars([(90, 95, 80, 90)], T9 - timedelta(days=1))  # PDL 80 is beyond 2R → extend there
    [s] = K.replay_day(prev, bars(), CFG, TICK).signals
    assert s.take_profit == D(80)


def test_c8_rth_gap_levels():
    assert K.rth_gap_levels(D(100), D(120)) == [D(100), D(105), D(110), D(115), D(120)]
    assert K.rth_gap_levels(None, D(1)) == [] and K.rth_gap_levels(D(1), D(1)) == []


def test_e3_grades():
    assert [K.grade(n, CFG) for n in (5, 4, 3, 2)] == ["A+", "A+", "B", "C"]
    [s] = K.replay_day([], bars(), CFG, TICK).signals
    assert s.grade == "C" and s.size_mult == D("0.5") and s.confluences == ["DISPLACEMENT"]


def test_b1_london_off_by_default_b4_max_hold_and_outcomes():
    t2 = datetime(2026, 10, 13, 2, 0, tzinfo=K.ET)
    assert K.replay_day([], bars(SETUP, t2), CFG, TICK).signals == []
    on = CFG.model_copy(update={"london": True, "london_max_stop_pts": D(10)})
    assert K.replay_day([], bars(SETUP, t2), on, TICK).signals[0].session == "LONDON"
    after = [*SETUP, *[(101.5, 102, 101, 101.5)] * 16]
    [s] = K.replay_day([], bars(after), CFG, TICK).signals
    assert s.outcome == "TIME" and s.exit_time == s.time + timedelta(minutes=15)
    [s] = K.replay_day([], bars([*SETUP, (101.5, 110, 101, 109)]), CFG, TICK).signals
    assert s.outcome == "STOP"
    [s] = K.replay_day([], bars([*SETUP, (101.5, 102, 80, 82)]), CFG, TICK).signals
    assert s.outcome == "TP"
    assert K.replay_day([], [], CFG, TICK).signals == []
