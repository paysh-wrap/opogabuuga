"""D110 AMT+ Order Flow: CONTEXT → LOCATION gates, level target, config + Pine contract."""

from __future__ import annotations

import re
from decimal import Decimal as D

import pytest

from app.config import AmtCfg, OrderFlowCfg
from app.engine import order_flow as OF
from app.engine.trade_plan import Direction
from tests.unit.test_order_flow import _b
from tests.unit.test_pine_order_flow import SRC

L, S = Direction.LONG, Direction.SHORT
R = OF.AmtRules()


def _f(ctx="ACCEPT_ABOVE", lvl="ETH_VWAP", tgt=None):
    return OF.AmtFields(context=ctx, key_level_type=lvl, target_level=tgt)


def test_context_with_level_passes():
    assert OF.check_amt(L, _f(), R) is None
    assert OF.check_amt(S, _f("ACCEPT_BELOW", "PRIOR_VAH"), R) is None


@pytest.mark.parametrize(
    ("d", "f", "rules", "code", "layer"),
    [
        (L, _f(None), R, "OF_AMT_NO_CONTEXT", "CONTEXT"),
        (S, _f("ACCEPT_ABOVE"), R, "OF_AMT_COUNTER_CONTEXT", "CONTEXT"),
        (L, _f("ACCEPT_BELOW"), R, "OF_AMT_COUNTER_CONTEXT", "CONTEXT"),
        (L, _f("BALANCE", "PRIOR_VAL"), R, "OF_AMT_BALANCE", "CONTEXT"),  # default skip
        (L, _f("BALANCE", "PRIOR_VAH"), OF.AmtRules(balance_mode="edges"), "OF_AMT_BALANCE", "CONTEXT"),
        (L, _f(lvl=None), R, "OF_AMT_NO_LEVEL", "LOCATION"),
        (L, _f(lvl="LVN"), OF.AmtRules(levels=frozenset({"ETH_VWAP"})), "OF_AMT_NO_LEVEL", "LOCATION"),
    ],
)
def test_skips(d, f, rules, code, layer):
    sk = OF.check_amt(d, f, rules)
    assert sk is not None and (sk.code, sk.layer) == (code, layer)


def test_balance_edges_and_level_switch():
    e = OF.AmtRules(balance_mode="edges")
    assert OF.check_amt(L, _f("BALANCE", "PRIOR_VAL"), e) is None
    assert OF.check_amt(S, _f("BALANCE", "PRIOR_VAH"), e) is None
    assert OF.check_amt(L, _f(lvl=None), OF.AmtRules(level_filter=False)) is None


def test_level_target_only_inside_rr_window():
    p = _b()  # LONG entry 20010, stop 19999.75, risk 10.25, TP 2R 20030.50
    assert isinstance(p, OF.OrderFlowPlan)
    kw = {"tick": D("0.25"), "rr_min": D("1.5"), "max_rr": D("3")}
    t = OF.amt_target(p, D("20036.1"), **kw)  # 2.54R, rounded toward entry
    assert t.take_profit == D("20036.00") and D("2.5") < t.rr < D("2.6") and t.stop == p.stop
    assert OF.amt_target(p, D("20020"), **kw) is p  # < 1.5R → normal 2R
    assert OF.amt_target(p, D("20050"), **kw) is p  # > 3R → normal 2R
    assert OF.amt_target(p, D("20000"), **kw) is p  # wrong side
    assert OF.amt_target(p, None, **kw) is p
    assert OF.amt_target(p, D("20010.1"), **kw) is p  # rounds onto the entry


def test_config_defaults_and_validation():
    c = OrderFlowCfg()
    assert c.amt.enabled is False and c.amt.balance_mode == "skip" and c.amt.target_max_rr == D("3.0")
    for bad in ({"levels": []}, {"levels": ["LVN", "LVN"]}, {"target_max_rr": D("3.5")}, {"target_max_rr": D("1.4")},
                {"balance_mode": "maybe"}):  # fmt: skip
        with pytest.raises(ValueError):
            AmtCfg(**bad)
    with pytest.raises(ValueError):
        OrderFlowCfg(rr_min=D("2.0"), rr=D("2.0"), amt=AmtCfg(target_max_rr=D("1.8")))


def test_pine_sends_amt_fields():
    from app.webhook.schemas import OrderFlowFields

    for f in ("prev_rth_vah", "prev_rth_val", "prev_rth_poc", "eth_vwap", "context", "ctx_session", "key_level_type",
              "target_level"):  # fmt: skip
        assert f'"{f}":' in SRC, f
        assert f in OrderFlowFields.model_fields, f
    assert set(re.findall(r'"(ACCEPT_ABOVE|ACCEPT_BELOW|BALANCE)"', SRC)) == {"ACCEPT_ABOVE", "ACCEPT_BELOW", "BALANCE"}
    assert {x for x in re.findall(r't := "([A-Z_]+)"', SRC)} == OF.LEVELS
    assert 'ta.vwap(hlc3, timeframe.change("D"))' in SRC and '"0300-0930", "America/New_York"' in SRC
