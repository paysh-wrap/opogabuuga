"""CONTI VWAP engine (D147): one test per rule id of docs/CONTI_RULES.md part C, on hand-built 1-minute bars."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

from app.config import ContiVwapCfg
from app.engine import conti_vwap as V
from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction

T0 = datetime(2026, 10, 13, 9, 30, tzinfo=V.ET)
TICK = D("0.25")
CFG = ContiVwapCfg()


def bar(minute, c, v=100, spread=1):
    c = D(str(c))
    return MBar(T0 + timedelta(minutes=minute), c, c + spread, c - spread, c, D(v))


def test_c1_vwap_is_volume_weighted_typical_price_from_the_open():
    bars = [MBar(T0 + timedelta(minutes=1), D(10), D(12), D(9), D(9), D(100)), bar(2, 20, 300, 0)]
    assert V.vwap_series(bars) == [D(10), (D(10) * 100 + D(20) * 300) / 400]
    assert V.vwap_series([bar(1, 10, 0)]) == [None]  # no volume yet


def test_c2_c3_close_above_vwap_is_long():
    [s] = V.replay_day([bar(1, 100, spread=0), bar(2, 102, spread=0)], CFG, TICK)
    assert s.direction == Direction.LONG and s.entry == D(102) and s.time == T0 + timedelta(minutes=2)


def test_c4_close_below_vwap_is_short_and_stop_is_the_emergency_stop():
    [s] = V.replay_day([bar(1, 100, spread=0), bar(2, 98, spread=0)], CFG, TICK)
    assert s.direction == Direction.SHORT and s.stop == D(123) and s.take_profit == D(98) - 200


def test_c5_close_back_through_vwap_exits_and_reverses():
    bars = [bar(1, 100, spread=0), bar(2, 102, spread=0), bar(3, 103, spread=0), bar(4, 99, spread=0)]
    a, b = V.replay_day(bars, CFG, TICK)
    assert (a.outcome, a.exit_time, a.exit_price) == ("CROSS", T0 + timedelta(minutes=4), D(99))
    assert b.direction == Direction.SHORT and b.time == a.exit_time and b.outcome == "OPEN"


def test_emergency_stop_then_wait_for_the_other_side():
    bars = [bar(1, 100, spread=0), bar(2, 102, spread=0), MBar(T0 + timedelta(minutes=3), D(102), D(102), D(70), D(101),
            D(1)), bar(4, 102, spread=0)]  # fmt: skip
    [s] = V.replay_day(bars, CFG, TICK)
    assert s.outcome == "STOP" and s.exit_price == D(77)  # still above VWAP after the stop → no new long


def test_window_flat_at_1530_and_no_entry_after():
    bars = [bar(1, 100, spread=0), bar(2, 102, spread=0)] + [bar(m, 102, spread=0) for m in range(3, 362)]
    [s] = V.replay_day(bars, CFG, TICK)
    assert s.outcome == "TIME" and s.exit_time == T0 + timedelta(hours=6)
    assert V.replay_day([], CFG, TICK) == []


def test_far_target_and_max_losses_per_day():
    bars = [bar(1, 100, spread=0), bar(2, 102, spread=0), bar(3, 400, spread=0)]
    [s] = V.replay_day(bars, CFG, TICK)
    assert s.outcome == "TP"
    zig = [bar(1, 100, spread=0)] + [bar(m, 101 if m % 2 else 99, 1_000_000, 0) for m in range(2, 20)]
    sigs = V.replay_day(zig, CFG.model_copy(update={"max_losses_per_day": 2}), TICK)
    lost = [x for x in sigs if x.exit_price is not None and (x.exit_price - x.entry) * x.direction.sign < 0]
    assert len(lost) == 2 and sigs[-1] is lost[-1]  # no entry after the 2nd loss
