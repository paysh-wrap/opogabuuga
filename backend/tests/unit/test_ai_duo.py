"""D83 AI Duo pure engine: side from both AIs, VWAP pullback trigger, capped structure stop, 2R target."""

from decimal import Decimal as D

import pytest

from app.config import AiDuoCfg
from app.engine import ai_duo as DU
from app.engine.trade_plan import Direction

T = D("0.25")


@pytest.mark.parametrize(
    ("ta", "vd", "vc", "want", "code"),
    [
        ("BUY", "LONG", 85, Direction.LONG, "AI_AGREE"),
        ("SELL", "SHORT", 60, Direction.SHORT, "AI_AGREE"),
        ("", "LONG", 85, None, "AI_TA_MISSING"),
        ("BUY", None, None, None, "AI_VT_MISSING"),
        ("HOLD", "LONG", 85, None, "AI_NEUTRAL"),
        ("BUY", "NEUTRAL", 70, None, "AI_NEUTRAL"),
        ("BUY", "SHORT", 85, None, "AI_DISAGREE"),
        ("OVERWEIGHT", "LONG", 85, None, "AI_NOT_STRONG"),
        ("BUY", "LONG", 59, None, "AI_NOT_STRONG"),
        ("BUY", "LONG", None, None, "AI_NOT_STRONG"),
    ],
)
def test_ai_side(ta, vd, vc, want, code):
    assert DU.ai_side(ta, vd, vc, 60) == (want, code)


def b(o, h, lo, c):
    return DU.Bar5(D(o), D(h), D(lo), D(c))


def test_aggregate_and_trigger():
    bar = DU.aggregate([(D(10), D(12), D(9), D(11)), (D(11), D(15), D(10), D(14))])
    assert bar == DU.Bar5(D(10), D(15), D(9), D(14))
    assert DU.pullback_trigger(Direction.LONG, b(100, 106, 98, 105), D(100))
    assert not DU.pullback_trigger(Direction.LONG, b(100, 106, 101, 105), D(100))  # never touched VWAP
    assert not DU.pullback_trigger(Direction.LONG, b(105, 106, 98, 99), D(100))  # closed below VWAP / down bar
    assert not DU.pullback_trigger(Direction.LONG, b(106, 107, 98, 105), D(100))  # closed against the direction
    assert DU.pullback_trigger(Direction.SHORT, b(100, 102, 94, 95), D(100))
    assert not DU.pullback_trigger(Direction.SHORT, b(100, 99, 94, 95), D(100))
    assert not DU.pullback_trigger(Direction.SHORT, b(95, 102, 94, 101), D(100))
    assert not DU.pullback_trigger(Direction.LONG, b(100, 106, 98, 105), None)


KW = {"tick": T, "buffer_ticks": 2, "min_stop_ticks": 4, "cap_pts": D(124), "rr_target": D(2), "rr_min": D("1.5")}


def test_plan_long_structure_stop_and_two_r():
    p = DU.plan(Direction.LONG, D(20005), b(20000, 20006, 19989, 20005), b(20000, 20001, 19999, 20000), **KW)
    assert (p.stop, p.risk_pts, p.take_profit, p.rr, p.stop_capped) == (
        D("19988.5"),
        D("16.5"),
        D(20038),
        D("2.00"),
        False,
    )


def test_plan_short_without_previous_bar():
    p = DU.plan(Direction.SHORT, D(20000), b(19995, 20010, 19990, 20000), None, **KW)
    assert (p.stop, p.take_profit, p.rr) == (D("20010.5"), D("19979.0"), D("2.00"))


def test_plan_caps_the_stop_at_the_noise_dollar_stop():
    p = DU.plan(Direction.LONG, D(20005), b(20000, 20006, 19700, 20005), None, **KW)
    assert p.stop_capped and p.risk_pts == D(124) and p.stop == D(19881) and p.take_profit == D(20253)


def test_plan_skips():
    assert DU.plan(Direction.LONG, D(20005), b(20000, 20006, 20010, 20005), None, **KW) == "STOP_INVALID"
    assert DU.plan(Direction.LONG, D("20000.25"), b(20000, 20001, 20000, 20000), None, **KW) == "STOP_TOO_TIGHT"
    # target rounding toward entry can never leave the floor: a 1.4R target config is refused by the floor
    kw = {**KW, "rr_target": D("1.4"), "rr_min": D("1.0")}
    assert DU.plan(Direction.LONG, D(20005), b(20000, 20006, 19989, 20005), None, **kw) == "RR_BELOW_MIN"


def test_config_refuses_low_rr_and_live():
    assert AiDuoCfg().paper_only is True and AiDuoCfg().rr_min == D("1.5")
    with pytest.raises(ValueError, match="rr_min"):
        AiDuoCfg(rr_min=D("1.4"))
    with pytest.raises(ValueError, match="rr_min"):
        AiDuoCfg(rr_target=D("1.2"))
    with pytest.raises(ValueError, match="bar_minutes"):
        AiDuoCfg(contracts=0)
    with pytest.raises(ValueError):
        AiDuoCfg(paper_only=False)
