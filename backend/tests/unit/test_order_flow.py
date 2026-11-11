"""D95 ORDER_FLOW engine (pure): plan rebuilt from entry + defended level; skip reason codes."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.config import OrderFlowCfg
from app.engine import order_flow as OF
from app.engine.trade_plan import Direction

T = D("0.25")


def _b(**kw):
    a = dict(
        kind="ABSORPTION", direction=Direction.LONG, entry=D("20010"), defended=D("20000"), tick=T, buffer_ticks=1,
        rr=D("2"), rr_min=D("1.5"), min_risk_ticks=8, max_risk_ticks=120,
    )  # fmt: skip
    a.update(kw)
    return OF.build_plan(**a)


def test_long_plan_stop_beyond_level_and_2r():
    p = _b()
    assert isinstance(p, OF.OrderFlowPlan)
    assert p.stop == D("19999.75") and p.risk_pts == D("10.25") and p.take_profit == D("20030.50") and p.rr == 2


def test_short_plan_and_entry_snapped():
    p = _b(direction=Direction.SHORT, entry=D("19990.1"), defended=D("20000"), alert_stop=D("20000.25"))
    assert isinstance(p, OF.OrderFlowPlan)
    assert p.entry == D("19990.00") and p.stop == D("20000.25") and p.take_profit < p.entry and p.rr == 2


@pytest.mark.parametrize(
    ("kw", "code"),
    [
        ({"kind": "MAGIC"}, "OF_UNKNOWN_SIGNAL"),
        ({"entry": D(0)}, "OF_BAD_PRICE"),
        ({"defended": D("20020")}, "OF_LEVEL_WRONG_SIDE"),
        ({"alert_stop": D("20001")}, "STOP_INVALID"),
        ({"entry": D("20001")}, "STOP_TOO_TIGHT"),
        ({"entry": D("20100")}, "STOP_TOO_WIDE"),
        ({"rr": D("1.5"), "rr_min": D("1.6")}, "RR_BELOW_MIN"),
    ],
)
def test_skips(kw, code):
    r = _b(**kw)
    assert isinstance(r, OF.OrderFlowSkip) and r.code == code


def test_config_forces_paper_only_and_floor():
    assert OrderFlowCfg().paper_only and OrderFlowCfg().contracts == 1
    for bad in ({"paper_only": False}, {"contracts": 2}, {"rr_min": D("1.4")}, {"rr": D("1.5"), "rr_min": D("1.6")},
                {"min_risk_ticks": 50, "max_risk_ticks": 10}, {"instruments": []}, {"instruments": ["MNQ", "MNQ"]},
                {"instruments": ["MES"]}, {"flat_at": "4pm"}):  # fmt: skip
        with pytest.raises(ValueError):
            OrderFlowCfg(**bad)


# ---------- D101 AR Model: ENVIRONMENT → LOCATION → PATH → CONFIRMATION ----------

from app.config import ArModelCfg  # noqa: E402

BAR = 1_760_000_000_000
GOOD = OF.ArFields(
    env="EXPANSION", fib=D("0.79"), value_side="BELOW_VAL", path_zone="AVR", path_side="BELOW",
    delta_source="real", confirm_time_ms=BAR - 60_000,
)  # fmt: skip


def _rules(**kw):
    c = ArModelCfg(**kw)
    return OF.ArRules(
        required=c.required, allowed_envs=tuple(c.allowed_envs), location_filter=c.location_filter, fib_min=c.fib_min,
        fib_max=c.fib_max, value_side=c.value_side, path_filter=c.path_filter, path_block_zone=c.path_block_zone,
        confirm_max_age_min=c.confirm_max_age_min, require_real_delta=c.require_real_delta,
    )  # fmt: skip


def _ar(d=Direction.LONG, rules=None, **kw):
    return OF.check_ar(d, BAR, OF.ArFields(**{**GOOD.__dict__, **kw}), rules or _rules())


def test_ar_all_layers_agree():
    assert _ar() is None
    assert _ar(Direction.SHORT, value_side="ABOVE_VAH", path_side="ABOVE") is None  # fade above Asia (not MAX)
    assert _ar(Direction.SHORT, value_side="ABOVE_VAH", path_side="ABOVE", path_zone="MAX") is None  # fade the MAX
    assert _ar(path_zone="MAX", path_side="BELOW") is None  # LONG reversal from below Asia MAX is not "with the move"
    assert _ar(path_zone="MAX", path_side="INSIDE") is None


@pytest.mark.parametrize(
    ("d", "kw", "code", "layer"),
    [
        (Direction.LONG, {"env": None}, "OF_NO_CONFIRM", "CONFIRMATION"),  # legacy alert, AR required
        (Direction.LONG, {"env": "COMPRESSION"}, "OF_COMPRESSION", "ENVIRONMENT"),
        (Direction.LONG, {"fib": None}, "OF_LOCATION", "LOCATION"),
        (Direction.LONG, {"fib": D("0.70")}, "OF_LOCATION", "LOCATION"),
        (Direction.LONG, {"fib": D("0.90")}, "OF_LOCATION", "LOCATION"),  # close beyond 0.886 = invalid
        (Direction.LONG, {"value_side": "IN_VALUE"}, "OF_LOCATION", "LOCATION"),
        (Direction.SHORT, {"path_side": "ABOVE"}, "OF_LOCATION", "LOCATION"),  # SHORT below VAL
        (Direction.LONG, {"path_zone": None}, "OF_PATH_UNKNOWN", "PATH"),
        (Direction.LONG, {"path_side": "LEFT"}, "OF_PATH_UNKNOWN", "PATH"),
        (Direction.LONG, {"path_zone": "MAX", "path_side": "ABOVE"}, "OF_PATH_EXHAUSTED", "PATH"),
        (Direction.SHORT, {"value_side": "ABOVE_VAH", "path_zone": "MAX"}, "OF_PATH_EXHAUSTED", "PATH"),
        (Direction.LONG, {"confirm_time_ms": BAR}, "OF_NO_CONFIRM", "CONFIRMATION"),  # must precede the entry bar
        (Direction.LONG, {"confirm_time_ms": BAR - 4 * 60_000}, "OF_NO_CONFIRM", "CONFIRMATION"),  # too old
    ],
)
def test_ar_skips(d, kw, code, layer):
    r = _ar(d, **kw)
    assert r is not None and (r.code, r.layer) == (code, layer), r


def test_ar_switches_and_options():
    assert _ar(rules=_rules(required=False), env=None, confirm_time_ms=None) is None  # legacy alerts allowed
    assert _ar(rules=_rules(allowed_envs=["EXPANSION"]), env="ROTATION").code == "OF_ENVIRONMENT"
    assert _ar(rules=_rules(location_filter=False), fib=None, value_side=None) is None  # switch off
    assert _ar(rules=_rules(path_filter=False), path_zone=None) is None
    nop = _rules(value_side="NOT_OPPOSITE")
    assert (
        _ar(rules=nop, value_side="IN_VALUE") is None and _ar(rules=nop, value_side="ABOVE_VAH").code == "OF_LOCATION"
    )
    assert _ar(rules=nop, value_side=None).code == "OF_LOCATION"
    tight = _rules(path_block_zone="AVR")
    assert _ar(rules=tight, path_zone="AVR", path_side="ABOVE").code == "OF_PATH_EXHAUSTED"
    assert _ar(rules=tight, path_zone="L1", path_side="ABOVE") is None
    real = _rules(require_real_delta=True)
    assert _ar(rules=real) is None and _ar(rules=real, delta_source="est").code == "OF_DELTA_ESTIMATED"


def test_stop_anchored_beyond_absorption_zone():
    p = _b(absorption=(D("19998"), D("20003")))  # absorption below the defended level → stop beyond it
    assert isinstance(p, OF.OrderFlowPlan) and p.defended == D("19998") and p.stop == D("19997.75")
    p = _b(absorption=(D("20001"), D("20004")))  # defended already beyond the zone → unchanged
    assert isinstance(p, OF.OrderFlowPlan) and p.stop == D("19999.75")
    s = _b(direction=Direction.SHORT, entry=D("19990"), defended=D("20000"), absorption=(D("19995"), D("20002")))
    assert isinstance(s, OF.OrderFlowPlan) and s.stop == D("20002.25")
    for zone, code in (((D(0), D(1)), "OF_BAD_PRICE"), ((D("20005"), D("20004")), "OF_BAD_PRICE"),
                       ((D("20011"), D("20012")), "OF_LEVEL_WRONG_SIDE")):  # fmt: skip
        r = _b(absorption=zone)
        assert isinstance(r, OF.OrderFlowSkip) and r.code == code


def test_trail_be_then_candle_ratchet_only():
    def t(best, candle, cur=D("19990"), last=None, d=Direction.LONG):
        return OF.trail_stop(d, D("20000"), D("10"), cur, best, candle, D("1"), 1, T, last)

    assert t(D("20009"), (D("20009"), D("20004"))) == D("19990")  # < 1R follow-through: nothing moves
    assert t(D("20010"), None) == D("20000.25")  # BE (entry + fee cover)
    assert t(D("20015"), (D("20015"), D("20008"))) == D("20007.75")  # behind the last 5m candle low
    assert t(D("20015"), (D("20015"), D("19995"))) == D("20000.25")  # candle below BE → BE wins
    assert t(D("20015"), (D("20015"), D("20008")), cur=D("20009")) == D("20009")  # ratchet: never loosens
    assert t(D("20015"), (D("20015"), D("20008")), last=D("20007")) == D("20000.25")  # never through the market
    sh = OF.trail_stop(Direction.SHORT, D("20000"), D("10"), D("20010"), D("19985"), (D("19992"), D("19985")),
                       D("1"), 1, T)  # fmt: skip
    assert sh == D("19992.25")


def test_ar_config_validation():
    assert ArModelCfg().fib_min == D("0.705") and ArModelCfg().path_block_zone == "MAX"
    for bad in ({"allowed_envs": []}, {"allowed_envs": ["COMPRESSION"]}, {"allowed_envs": ["ROTATION", "ROTATION"]},
                {"fib_max": D("0.9")}, {"fib_min": D("0.4")}, {"fib_min": D("0.8"), "fib_max": D("0.75")},
                {"path_block_zone": "BEYOND"}, {"confirm_max_age_min": 0}, {"confirm_max_age_min": 30},
                {"be_after_r": D("0.1")}, {"be_after_r": D("5")}, {"trail_candle_min": 1}):  # fmt: skip
        with pytest.raises(ValueError):
            ArModelCfg(**bad)
    with pytest.raises(ValueError):
        OrderFlowCfg(ar={"fib_max": "0.95"})
