"""CONTI ORB engine (D146): one test per rule id of docs/CONTI_RULES.md part B, on hand-built 1-minute bars."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

import pytest

from app.config import ContiOrbCfg
from app.engine import conti_orb as O

T0 = datetime(2026, 10, 13, 9, 30, tzinfo=O.ET)
TICK = D("0.25")
CFG = ContiOrbCfg()


def bar(minute, o, h, lo, c, v=100):
    return O.MBar(T0 + timedelta(minutes=minute), D(str(o)), D(str(h)), D(str(lo)), D(str(c)), D(v))


def day(after=()):
    rng = [bar(m, 100, 110 if m == 5 else 105, 90 if m == 20 else 95, 100) for m in range(1, 31)]  # 09:31–10:00
    return rng + [bar(31 + i, *x) for i, x in enumerate(after)]


def test_b1_range_is_0930_to_1000():
    rep = O.replay_day(day(), CFG, TICK)
    assert (rep.range_high, rep.range_low) == (D(110), D(90))
    assert O.replay_day(day()[1:], CFG, TICK).skip == "CORB_NO_RANGE"
    assert O.replay_day(day()[:-1], CFG, TICK).skip == "CORB_NO_RANGE"  # range not finished yet
    assert O.replay_day([], CFG, TICK).skip == "CORB_NO_BARS"


def test_b2_b3_long_only_on_a_close_above_the_high():
    rep = O.replay_day(day([(100, 112, 99, 109), (109, 111, 80, 85), (85, 112, 85, 111)]), CFG, TICK)
    [s] = rep.signals  # wick above (109 close) no; break of the LOW is never a short
    assert s.entry == D(111) and s.time == T0 + timedelta(minutes=33)


def test_b4_stop_range_low_and_b5_rr():
    [s] = O.replay_day(day([(100, 112, 99, 111)]), CFG, TICK).signals
    assert s.stop == D(90) and s.risk_pts == D(21) and s.take_profit == D(132) and s.rr == D(1)
    [s2] = O.replay_day(day([(100, 112, 99, 111)]), CFG.model_copy(update={"rr": D(2)}), TICK).signals
    assert s2.take_profit == D(153)
    with pytest.raises(ValueError):
        ContiOrbCfg(rr=D("1.5"))


def test_b6_time_exit_1530_and_outcomes():
    flat = [(111, 112, 110, 111)] * 400
    [s] = O.replay_day(day([(100, 112, 99, 111), *flat]), CFG, TICK).signals
    assert s.outcome == "TIME" and s.exit_time == T0 + timedelta(hours=6)
    [s] = O.replay_day(day([(100, 112, 99, 111), (111, 140, 111, 135)]), CFG, TICK).signals
    assert s.outcome == "TP"
    [s] = O.replay_day(day([(100, 112, 99, 111), (111, 111, 85, 86)]), CFG, TICK).signals
    assert s.outcome == "STOP"
    [s] = O.replay_day(day([(100, 112, 99, 111)]), CFG, TICK).signals
    assert s.outcome == "OPEN"


def test_one_trade_a_day_and_last_entry():
    seq = [(100, 112, 99, 111), (111, 111, 85, 86), (86, 115, 86, 114)]
    assert len(O.replay_day(day(seq), CFG, TICK).signals) == 1
    two = CFG.model_copy(update={"max_trades_per_day": 2})
    assert len(O.replay_day(day(seq), two, TICK).signals) == 2
    late = [(100, 105, 99, 100)] * 300 + [(100, 112, 99, 111)]  # 15:01 close above → after the last entry
    assert O.replay_day(day(late), CFG, TICK).signals == []


def test_b7_same_dollars_fewer_contracts_on_a_wide_range():
    from app.engine.lucid_fit import contracts_for

    assert contracts_for(D(300), D(20), TICK, D("0.5"), D("0.74"), 1) > contracts_for(D(300), D(60), TICK, D("0.5"),
                                                                                         D("0.74"), 1)  # fmt: skip
