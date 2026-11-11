"""D111 ATR-zone Order Flow type (iceberg PROXY): gates, plan, trail, config, Pine contract."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.config import OrderFlowCfg, ZoneAtrCfg
from app.engine import zone_atr as ZA
from app.engine.order_flow import OrderFlowPlan
from app.engine.trade_plan import Direction
from tests.unit.test_pine_order_flow import SRC

L, S = Direction.LONG, Direction.SHORT
T = D("0.25")
R = ZA.ZoneRules(modes=frozenset({"POSITION", "REVERSION"}))
TEN = 10 * 60  # 10:00 ET


def _f(sig="POSITION", **kw):
    a = dict(signal=sig, zone_hi=D("20010"), zone_lo=D("20000"), event_size=D("200"), atr5=D("10"), rvol=D("2"),
             range5_atr=D("0.8"))  # fmt: skip
    a.update(kw)
    return ZA.ZoneFields(**a)


def _plan(d, entry, f, r=R):
    return ZA.plan_zone(d, entry, f, r, tick=T, rr=D("2"), rr_min=D("1.5"), min_risk_ticks=8, max_risk_ticks=400)


def test_position_long_gate_plan_and_trail():
    assert ZA.check_zone(L, D("20021.5"), TEN, _f(), R) is None  # 20010 + 1.15 × 10
    p = _plan(L, D("20021.5"), _f())
    assert isinstance(p, OrderFlowPlan) and p.stop == D("19988.50") and p.take_profit == D("20087.50") and p.rr == 2
    assert p.kind == "ZONE_POSITION"
    assert ZA.zone_trail(L, p.stop, D("20040"), D("20030"), D("10"), D("1.15"), T) == D("20018.50")
    assert ZA.zone_trail(L, D("20020"), D("20040"), D("20030"), D("10"), D("1.15"), T) is None  # ratchet only
    assert ZA.trail_hit(L, D("20018.5"), D("20018")) and not ZA.trail_hit(L, D("20018.5"), D("20019"))
    sp = _plan(S, D("19988.5"), _f())
    assert isinstance(sp, OrderFlowPlan) and sp.stop == D("20021.50")


def test_reversion_targets_zone_with_rr_floor():
    f = _f("REVERSION", rev_level=2)
    assert ZA.check_zone(L, D("19980"), TEN, f, R) is None
    p = _plan(L, D("19980"), f)  # stop 19970 (3 ATR), target 20000 → 2R
    assert isinstance(p, OrderFlowPlan) and (p.stop, p.take_profit, p.rr) == (D("19970.00"), D("20000.00"), 2)
    one = _plan(L, D("19990"), _f("REVERSION", rev_level=1))  # 1 ATR: 1R < 1.5 floor
    assert one.code == "RR_BELOW_MIN"  # type: ignore[union-attr]
    three = _plan(S, D("20040"), _f("REVERSION", rev_level=3))
    assert isinstance(three, OrderFlowPlan) and three.rr == 3


@pytest.mark.parametrize(
    ("d", "entry", "minute", "f", "rules", "code"),
    [
        (L, D("20021.5"), TEN, _f("EVENT"), R, "OF_ZONE_NOT_ENTRY"),
        (L, D("19980"), TEN, _f("REVERSION", rev_level=2), ZA.ZoneRules(), "OF_ZONE_MODE_OFF"),
        (L, D("20021.5"), TEN, _f(atr5=None), R, "OF_ZONE_NO_EVENT"),
        (L, D("20021.5"), TEN, _f(event_size=D("100")), R, "OF_ZONE_EVENT_SMALL"),
        (L, D("20021.5"), 15 * 60 + 55, _f(), R, "OF_ZONE_LAST_MINUTES"),
        (L, D("20021.5"), 12 * 60, _f(rvol=D("1.2")), R, "OF_ZONE_DEAD_ZONE"),
        (L, D("20015"), TEN, _f(), R, "OF_ZONE_NOT_PROVEN"),
        (L, D("19995"), TEN, _f("REVERSION", rev_level=2), R, "OF_ZONE_REV_LEVEL"),
        (L, D("19980"), TEN, _f("REVERSION", rev_level=2, range5_atr=D("0.5")), R, "OF_ZONE_NO_PRICE_CHANGE"),
        (L, D("19980"), TEN, _f("REVERSION", rev_level=2, tick=-1200), R, "OF_ZONE_PROGRAM_DAY"),
        (L, D("19980"), TEN, _f("REVERSION", rev_level=2),
         ZA.ZoneRules(modes=frozenset({"REVERSION"}), a_plus_only=True), "OF_ZONE_NOT_A_PLUS"),
    ],
)  # fmt: skip
def test_skips(d, entry, minute, f, rules, code):
    sk = ZA.check_zone(d, entry, minute, f, rules)
    assert sk is not None and sk.code == code


def test_filters_pass_paths_and_a_plus():
    assert ZA.check_zone(L, D("20021.5"), 12 * 60, _f(rvol=D("1.6")), R) is None  # dead zone with volume
    assert ZA.check_zone(L, D("19980"), TEN, _f("REVERSION", rev_level=2, tick=1200), R) is None  # TICK with fade
    ap = ZA.ZoneRules(modes=frozenset({"REVERSION"}), a_plus_only=True)
    f = _f("REVERSION", rev_level=2, prior_hi=D("19982"), prior_lo=D("19975"))
    assert ZA.check_zone(L, D("19980"), TEN, f, ap) is None
    p = _plan(L, D("19980"), f, ap)
    assert isinstance(p, OrderFlowPlan) and p.stop == D("19970.00")
    wide = ZA.plan_zone(L, D("20021.5"), _f(atr5=D("100")), R, tick=T, rr=D("2"), rr_min=D("1.5"),
                        min_risk_ticks=8, max_risk_ticks=400)  # fmt: skip
    assert wide.code == "STOP_TOO_WIDE"  # type: ignore[union-attr]


def test_config():
    c = OrderFlowCfg()
    assert c.zone_atr.enabled is False and c.zone_atr.modes == ["POSITION"] and c.zone_atr.min_event_size["MNQ"] == 150
    for bad in ({"modes": []}, {"entry_atr_pct": D("0.5")}, {"reversion_levels": [4]}, {"min_event_size": {"MNQ": 0}},
                {"dead_zone": ("13:30", "11:15")}, {"dead_zone_min_rvol": D("5")}):  # fmt: skip
        with pytest.raises(ValueError):
            ZoneAtrCfg(**bad)


def test_pine_zone_alert():
    from app.webhook.schemas import OrderFlowFields

    for f in ("zone_signal", "event_zone_hi", "event_zone_lo", "event_kind", "event_time", "event_size", "atr5",
              "rev_level", "prior_event_hi", "prior_event_lo", "rvol", "range5_atr", "tick"):  # fmt: skip
        assert f'"{f}":' in SRC, f
        assert f in OrderFlowFields.model_fields, f
    assert "iceberg PROXY" in SRC and '"kind":"ZONE"' in SRC and "1.15 * zAtr5" in SRC
