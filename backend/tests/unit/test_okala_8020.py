"""OKALA 8020 engine (D145): one test per rule id of docs/OKALA_8020_RULES.md that is built, on hand-built bars."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

from app.config import Okala8020Cfg
from app.engine import okala_8020 as K
from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction

T0 = datetime(2026, 10, 13, 9, 30, tzinfo=K.ET)
TICK = D("0.25")
CFG = Okala8020Cfg()


def three(k, o, h, lo, c):
    """One 3-minute candle (index k from 09:30) as three 1-minute bars."""
    o, h, lo, c = (D(str(x)) for x in (o, h, lo, c))
    st = T0 + timedelta(minutes=3 * k)
    return [  # low first, then high, then the close
        MBar(st + timedelta(minutes=1), o, o, lo, o, D(10)),
        MBar(st + timedelta(minutes=2), o, h, o, c, D(10)),
        MBar(st + timedelta(minutes=3), c, c, c, c, D(10)),
    ]


def seq(*cs):
    out: list[MBar] = []
    for k, c in enumerate(cs):
        out += three(k, *c)
    return out


def C(o, h, lo, c, k=0, minutes=3):
    st = T0 + timedelta(minutes=minutes * k)
    return K.Candle(st, st + timedelta(minutes=minutes), D(str(o)), D(str(h)), D(str(lo)), D(str(c)))


def test_a1_levels_end_in_20_and_80():
    lv = K.levels_near(D(25650), D(100))
    assert lv == [D(25580), D(25620), D(25680), D(25720)] and K.is_level(D(25620)) and not K.is_level(D(25650))
    assert K.nearest_level(D(25676)) == D(25680)


def test_a2_a3_a4_level_reaction_either_way_and_near_touch():
    assert K.level_reaction(C(25630, 25632, 25620, 25628), CFG) == (1, D(25620))  # tapped 20, reacted up (A2: 20 long)
    assert K.level_reaction(C(25630, 25632, 25620.25, 25628), CFG) == (1, D(25620))  # A4 stopped a tick short
    assert K.level_reaction(C(25630, 25632, 25617, 25628), CFG) == (1, D(25620))  # A4 passed by 3
    assert K.level_reaction(C(25630, 25632, 25615, 25628), CFG) is None  # through by 5 → not respected
    assert K.level_reaction(C(25670, 25680, 25668, 25672), CFG) == (-1, D(25680))  # 80 short
    assert K.level_reaction(C(25630, 25632, 25620, 25622), CFG) is None  # no reaction


def test_b1_ten_minute_and_three_minute_candles_built_from_one_minute():
    bars = seq(*[(100, 101, 99, 100)] * 4)  # 12 minutes
    c10 = K.build(bars, 10)
    assert len(c10) == 1 and c10[0].end == T0 + timedelta(minutes=10)
    assert len(K.build(bars, 3)) == 4


def test_b3_window_and_c1_c2_c3_stop_tp1_breakeven():
    cfg = CFG.model_copy(update={"setups": ["LEVEL"]})
    day = seq((25630, 25632, 25620, 25628), (25628, 25645, 25627, 25644), (25644, 25645, 25628, 25630))
    [s] = K.replay_day(day, cfg, TICK).signals
    assert s.direction == Direction.LONG and s.entry == D(25628) and s.stop == D(25618) and s.tp1 == D(25643)
    assert s.tp1_time is not None and s.outcome == "BE"  # C3: after TP1 the stop is entry + 1
    late = cfg.model_copy(update={"windows": ["10:00-11:30"]})
    assert K.replay_day(day, late, TICK).signals == []


def test_c4_runner_to_target_and_time_exit():
    cfg = CFG.model_copy(update={"setups": ["LEVEL"], "max_hold_minutes": 10})
    day = seq((25630, 25632, 25620, 25628), (25628, 25700, 25627, 25690))
    [s] = K.replay_day(day, cfg, TICK).signals
    assert s.outcome == "RUNNER" and s.runner_target == D(25658)
    day = seq((25630, 25632, 25620, 25628), *[(25628, 25630, 25626, 25628)] * 6)
    [s] = K.replay_day(day, cfg, TICK).signals
    assert s.outcome == "TIME"


def test_d1_fork_long_after_a_strong_move_down():
    c = [C(25800, 25801, 25700, 25702, 0), C(25702, 25705, 25680, 25700, 1), C(25700, 25710, 25690, 25708, 2)]
    assert K.fork(c, 2, D(25800), CFG) == 1  # initiation: long lower wick, small body; next holds the low, higher high
    assert K.fork(c, 2, D(25750), CFG) is None  # not a strong move
    broke = [*c[:2], C(25700, 25710, 25670, 25708, 2)]
    assert K.fork(broke, 2, D(25800), CFG) is None
    assert K.fork(c, 0, D(25800), CFG) is None


def test_d2_reverse_fork_short_after_a_strong_move_up():
    c = [C(25600, 25700, 25599, 25698, 0), C(25698, 25720, 25695, 25700, 1), C(25700, 25710, 25690, 25692, 2)]
    assert K.fork(c, 2, D(25600), CFG) == -1


def test_d4_cross_section_tap_and_reject():
    c = [C(25700, 25701, 25680, 25681, 0), C(25681, 25682, 25660, 25661, 1), C(25661, 25670, 25655, 25665, 2),
         C(25675, 25682, 25664, 25670, 3)]  # fmt: skip
    assert K.cross_entry(c, 3, CFG) == (-1, D(25681))  # taps the 25681 cross, closes red below it
    assert K.cross_entry(c[:3], 2, CFG) is None  # tap must come ≥ 2 candles after the pair


def test_d3_h_pattern_on_ten_minute_candles():
    c10 = [
        C(25700, 25701, 25670, 25672, 0, 10),
        C(25672, 25681, 25650, 25678, 1, 10),
        C(25678, 25679, 25640, 25645, 2, 10),
    ]
    assert K.h_pattern(c10, CFG) == -1
    up = [C(-x.o, -x.l, -x.h, -x.c, i, 10) for i, x in enumerate(c10)]
    assert K.h_pattern(up, CFG) == 1
    assert K.h_pattern(c10[:2], CFG) is None


def test_d5_repair_candle_is_a_magnet_until_touched():
    c10 = [C(25700, 25700, 25660, 25665, 0, 10)]  # red, opened at its high (no top wick)
    later = [MBar(T0 + timedelta(minutes=11), D(25665), D(25680), D(25660), D(25670))]
    assert K.repair_magnets(c10, later, TICK, CFG) == [D(25700)]
    touched = [*later, MBar(T0 + timedelta(minutes=12), D(25670), D(25701), D(25669), D(25690))]
    assert K.repair_magnets(c10, touched, TICK, CFG) == []


def test_d6_adds_same_side_after_tp1_only_and_max_adds():
    cfg = CFG.model_copy(update={"setups": ["LEVEL"], "max_adds": 1, "runner_target_pts": D(200)})
    day = seq(
        (25630, 25632, 25620, 25628),  # LONG off 20
        (25628, 25690, 25640, 25688),  # TP1 → stop at break even
        (25688, 25692, 25680, 25686),  # long reaction off 80 → ADD 1
        (25686, 25692, 25680, 25686),  # again → refused (max_adds 1)
        (25686, 25688, 25640, 25645),  # a short-side move never adds
    )
    sigs = K.replay_day(day, cfg, TICK).signals
    assert [s.add_no for s in sigs] == [0, 1]
    no_add = K.replay_day(day, cfg.model_copy(update={"add_after_tp1": False}), TICK).signals
    assert all(s.add_no == 0 for s in no_add)


def test_e1_no_trade_cap_but_max_losses_a_day():
    cfg = CFG.model_copy(update={"setups": ["LEVEL"], "max_losses_per_day": 1})
    loss = [(25630, 25632, 25620, 25628), (25628, 25629, 25600, 25601)]
    sigs = K.replay_day(seq(*loss, *loss), cfg, TICK).signals
    assert [s.outcome for s in sigs] == ["STOP"]
    assert K.replay_day([], cfg, TICK).signals == []
    assert K.replay_day(seq(*loss)[1:], cfg, TICK).signals == []  # no 09:31 bar
