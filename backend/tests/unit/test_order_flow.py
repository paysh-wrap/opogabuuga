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
