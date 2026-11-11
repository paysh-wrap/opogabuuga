"""D110 AMT+ Order Flow button: ORDER_FLOW alert gated CONTEXT → LOCATION before the AR layers; level target."""

from __future__ import annotations

from decimal import Decimal as D

from app.models import AuditLog, Signal, TradePlanRow
from tests.integration.test_order_flow import _p, _run


def _rules(base, **amt):
    mnq = base.instruments["MNQ"].model_copy(update={"enabled": True, "windows": [("09:30", "16:00")]})
    of = base.strategy.order_flow_cfg
    of = of.model_copy(update={"instruments": ["MNQ"], "amt": of.amt.model_copy(update={"enabled": True, **amt})})
    st = base.strategy.model_copy(update={"order_flow": True, "order_flow_cfg": of})
    return base.model_copy(update={"strategy": st, "instruments": {**base.instruments, "MNQ": mnq}})


def _amt(p, **kw):
    p["order_flow"].update(kw)
    return p


def test_amt_gates_and_level_target(client, loaded_rules):
    r = _rules(loaded_rules.rules)
    ms = _p()["bar_time_ms"]
    with client.app.state.sessionmaker() as s:
        assert _run(s, r, _p()).updates == []  # old indicator: no context → OF_AMT_NO_CONTEXT (audited)
        assert _run(s, r, _amt(_p(ms=ms + 1), context="ACCEPT_BELOW", key_level_type="ETH_VWAP")).updates == []
        assert _run(s, r, _amt(_p(ms=ms + 2), context="ACCEPT_ABOVE")).updates == []  # no key level
        codes = [a.payload["code"] for a in s.query(AuditLog).filter_by(action="order_flow.skip").order_by(AuditLog.id)]
        assert codes == ["OF_AMT_NO_CONTEXT", "OF_AMT_COUNTER_CONTEXT", "OF_AMT_NO_LEVEL"]
        ok = _amt(_p(ms=ms + 3), context="ACCEPT_ABOVE", key_level_type="PRIOR_VAL", target_level="20036.1",
                  eth_vwap="20005", prev_rth_vah="20040", prev_rth_val="20008", ctx_session="LONDON")  # fmt: skip
        u = _run(s, r, ok).updates[0]
        assert u.status == "PASS"
        plan = s.query(TradePlanRow).filter_by(signal_id=u.signal_id).one()
        assert plan.take_profit == D("20036.00")  # next key level (≈ 2.54R) instead of 2R
        ar = s.get(Signal, u.signal_id).features["ar"]
        assert ar["context"] == "ACCEPT_ABOVE" and ar["key_level_type"] == "PRIOR_VAL" and ar["eth_vwap"] == "20005"


def test_amt_off_ignores_fields_and_balance_edges(client, loaded_rules):
    off = _rules(loaded_rules.rules, enabled=False)
    ms = _p()["bar_time_ms"]
    with client.app.state.sessionmaker() as s:
        u = _run(s, off, _amt(_p(), context="ACCEPT_BELOW", target_level="20036")).updates[0]
        assert u.status == "PASS"  # button OFF: AMT+ fields are ignored, normal 2R
        assert s.query(TradePlanRow).filter_by(signal_id=u.signal_id).one().take_profit == D("20030.50")
        s.get(Signal, u.signal_id).features = {**s.get(Signal, u.signal_id).features, "state": "CLOSED"}
        s.commit()
        edges = _rules(loaded_rules.rules, balance_mode="edges")
        assert _run(s, edges, _amt(_p(ms=ms + 60000), context="BALANCE", key_level_type="ETH_VWAP")).updates == []
        u = _run(s, edges, _amt(_p(ms=ms + 120000), context="BALANCE", key_level_type="PRIOR_VAL")).updates[0]
        assert u.status == "PASS"


def test_button_card_gates_and_settings(authed):
    st = authed.get("/api/strategies").json()["strategies"]
    card = next(x for x in st if x["key"] == "order_flow_amt")
    assert card["enabled"] is False and card["setting"] == "strategy.order_flow_cfg.amt.enabled"
    assert card["also"] == ["strategy.order_flow"] and [x["key"] for x in card["amt_layers"]][:2] == [
        "CONTEXT",
        "LOCATION",
    ]
    r = authed.put(
        "/api/risk/settings",
        json={"changes": {"strategy.order_flow_cfg.amt.enabled": True, "strategy.order_flow": True}, "note": "AMT+"},
    )
    assert r.status_code == 200, r.text
    card = next(x for x in authed.get("/api/strategies").json()["strategies"] if x["key"] == "order_flow_amt")
    assert card["enabled"] is True
    from app.api.strategy_gates import describe

    rows = {c["key"]: c for c in describe(authed.app.state.rules.rules)}
    ids = [g["id"] for g in rows["order_flow"]["gates"]]
    assert ids[:2] == ["AMT_CONTEXT", "AMT_LOCATION"]
    of = authed.get("/api/orderflow?symbol=MNQ").json()["ar"]
    assert of["amt_enabled"] is True and of["amt"][0]["on"] is True
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.order_flow_cfg.amt.balance_mode": "maybe"}})
    assert bad.status_code >= 400
