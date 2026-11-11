"""D122 dynamic trailing stop (pure) — every branch."""

from decimal import Decimal as D

from app.engine.trade_plan import Direction
from app.indicators.bars import Bar
from app.management.dynamic_trail import (
    TrailParams,
    atr_values,
    closed_bars,
    dynamic_stop,
    k_for,
    low_volatility,
)

T = D("0.25")
L, S = Direction.LONG, Direction.SHORT
STEPS = ((D(2), D(2)), (D(3), D("1.5")), (None, D(1)))


def bar(i: int, h: str, lo: str, tf: int = 1) -> Bar:
    o = (D(h) + D(lo)) / 2
    return Bar(i * tf * 60_000, (i + 1) * tf * 60_000, o, D(h), D(lo), o)


def params(**kw: object) -> TrailParams:
    base: dict[str, object] = {
        "activate_r": D(1),
        "min_distance_ticks": 8,
        "atr_tf_min": 1,
        "atr_period": 3,
        "swing_tf_min": 1,
        "steps": STEPS,
        "low_vol_percentile": D("0.25"),
        "low_vol_mult": D("0.75"),
        "low_vol_lookback": 50,
        "k_floor": D("0.5"),
        "fee_cover_ticks": 2,
    }
    base.update(kw)
    return TrailParams(**base)  # type: ignore[arg-type]


def flat(n: int, h: str = "20040", lo: str = "20036") -> list[Bar]:
    return [bar(i, h, lo) for i in range(n)]  # range 4 → ATR 4


def test_closed_bars_builds_5m_and_drops_the_unfinished_candle():
    one = [bar(i, str(20000 + i), str(19990 + i)) for i in range(12)]
    five = closed_bars(one, 5)
    assert [(b.open_ms, b.h, b.l) for b in five] == [(0, D(20004), D(19990)), (300_000, D(20009), D(19995))]
    assert closed_bars(one, 1) == one


def test_atr_values_need_a_full_period():
    assert atr_values(flat(2), 3) == []
    assert atr_values(flat(4), 3)[-1] == D(4)


def test_k_steps_tighten_with_profit():
    assert [k_for(D(x), STEPS) for x in ("1", "2.5", "9")] == [D(2), D("1.5"), D(1)]
    assert k_for(D(9), ((D(2), D(2)),)) == D(2)  # no open-ended step: the last k


def test_low_volatility_needs_history_and_a_low_rank():
    assert not low_volatility([D(1)] * 3, 5, D("0.25"))
    assert low_volatility([D(5), D(4), D(6), D(5), D(1)], 5, D("0.25"))
    assert not low_volatility([D(1), D(2), D(3), D(4), D(5)], 5, D("0.25"))


def test_not_active_below_activate_r():
    assert dynamic_stop(L, D(20000), D(20), D(20010), D(19980), flat(10), params(), T, D(20010)) is None
    assert dynamic_stop(L, D(20000), D(0), D(20010), D(19980), [], params(), T) is None  # no risk → nothing


def test_breakeven_only_without_bars():
    mv = dynamic_stop(L, D(20000), D(20), D(20020), D(19980), [], params(), T, D(20018))
    assert mv is not None and (mv.stop, mv.rule) == (D("20000.50"), "BREAKEVEN")


def test_atr_trail_k2_until_2r():
    # best 20040 = 2R → k 1.5, ATR 4 → 20040 − 6 = 20034 (swing low 20036 − 1 tick is only 4.25 away)
    mv = dynamic_stop(L, D(20000), D(20), D(20040), D(19980), flat(10), params(), T, D(20039))
    assert mv is not None and (mv.stop, mv.rule) == (D(20034), "ATR")
    mv = dynamic_stop(L, D(20000), D(20), D(20030), D(19980), flat(10, "20030", "20026"), params(), T, D(20030))
    assert mv is not None and (mv.stop, mv.rule) == (D(20022), "ATR")  # 1.5R → k 2 × 4 = 8
    mv = dynamic_stop(L, D(20000), D(20), D(20040), D(19980), flat(10), params(), T, D(20035))
    assert mv is not None and (mv.stop, mv.rule) == (D(20033), "ATR+MIN_DIST")  # never closer than 8 ticks


def test_swing_wider_than_atr_wins():
    bars = [*flat(9), bar(9, "20060", "20030")]  # last bar low 20030 → level 20029.75; ATR small vs that
    mv = dynamic_stop(L, D(20000), D(20), D(20070), D(19980), bars, params(min_distance_ticks=2), T, D(20069))
    assert mv is not None and mv.rule == "SWING" and mv.stop == D("20029.75")


def test_low_volatility_tightens_k():
    bars = [bar(i, "20050", "20030") for i in range(8)] + flat(4, "20050", "20049")  # ATR falls → low rank
    p = params(low_vol_lookback=5, min_distance_ticks=2)
    mv = dynamic_stop(L, D(20000), D(20), D(20050), D(19980), bars, p, T, D(20050))
    assert mv is not None and mv.rule.startswith("ATR_LOWVOL")


def test_cushion_k_minus_and_floor():
    p = params(k_minus=D(5), min_distance_ticks=2)  # k − 5 → floored at 0.5 × ATR 4 = 2 → 20038 (swing 4.25 wider)
    mv = dynamic_stop(L, D(20000), D(20), D(20040), D(19980), flat(10), p, T, D(20040))
    assert mv is not None and (mv.stop, mv.rule) == (D("20035.75"), "SWING")
    mv = dynamic_stop(L, D(20000), D(20), D(20040), D(19980), flat(10, "20040", "20039"), p, T, D(20040))
    assert mv is not None and (mv.stop, mv.rule) == (D("20038.75"), "SWING")  # floor 0.5 × ATR 1 < swing 1.25
    mv = dynamic_stop(L, D(20000), D(20), D(20040), D(19980), flat(10, "20040", "20039"), p, T, D(20039))
    assert mv is not None and (mv.stop, mv.rule) == (D("20038.50"), "SWING+MIN_DIST")


def test_short_mirror_and_last_none():
    bars = flat(10, "19964", "19960")
    mv = dynamic_stop(S, D(20000), D(20), D(19960), D(20020), bars, params(), T)
    assert mv is not None and mv.stop == D(19966) and mv.rule.startswith("ATR")  # 19960 + 1.5 × 4


def test_ratchet_never_loosens():
    assert dynamic_stop(L, D(20000), D(20), D(20040), D(20035), flat(10), params(), T, D(20039)) is None


def test_swing_above_best_gives_no_room_breakeven_only():
    bars = [bar(0, "20100", "20090")]  # a pre-entry bar above the best price → no swing room, no ATR yet
    mv = dynamic_stop(L, D(20000), D(20), D(20020), D(19980), bars, params(), T, D(20019))
    assert mv is not None and mv.rule == "BREAKEVEN"


def test_order_flow_ar_trail_before_dynamic_activation():
    p = params(activate_r=D(2), of_trail=(1, D("0.5")))
    bars = flat(3, "20012", "20008")
    mv = dynamic_stop(L, D(20000), D(20), D(20012), D(19980), bars, p, T, D(20011))
    assert mv is not None and (mv.stop, mv.rule) == (D("20007.75"), "OF_AR_TRAIL")
    assert dynamic_stop(L, D(20000), D(20), D(20005), D(19980), [], p, T, D(20005)) is None  # below be_after_r
