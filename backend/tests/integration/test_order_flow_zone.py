"""D111 ATR-zone Order Flow type: ZONE alerts → signal / skip, opposing-event exit, trail, card + gates."""

from __future__ import annotations

from decimal import Decimal as D

from app.models import AuditLog, Signal, TradePlanRow
from tests.integration.test_order_flow import _p, _run


def _rules(base, **z):
    mnq = base.instruments["MNQ"].model_copy(update={"enabled": True, "windows": [("09:30", "16:00")]})
    of = base.strategy.order_flow_cfg
    zc = of.zone_atr.model_copy(update={"enabled": True, **z})
    of = of.model_copy(update={"instruments": ["MNQ"], "zone_atr": zc})
    st = base.strategy.model_copy(update={"order_flow": True, "order_flow_cfg": of})
    return base.model_copy(update={"strategy": st, "instruments": {**base.instruments, "MNQ": mnq}})


def _z(ms, sig="POSITION", direction="LONG", entry="20021.5", **kw):
    p = _p(ms=ms, direction=direction, entry=entry, defended="20000")
    p["order_flow"].update({"kind": "ZONE", "zone_signal": sig, "event_zone_hi": "20010", "event_zone_lo": "20000",
                            "event_size": "200", "atr5": "10", "rvol": "2", "range5_atr": "0.8", **kw})  # fmt: skip
    return p


def test_zone_position_trail_and_opposing_exit(client, loaded_rules):
    r = _rules(loaded_rules.rules)
    ms = _p()["bar_time_ms"]
    with client.app.state.sessionmaker() as s:
        assert _run(s, _rules(loaded_rules.rules, enabled=False), _z(ms)).updates == []  # type off: ignored
        u = _run(s, r, _z(ms)).updates[0]
        assert u.status == "PASS"
        plan = s.query(TradePlanRow).filter_by(signal_id=u.signal_id).one()
        assert (plan.stop, plan.take_profit) == (D("19988.50"), D("20087.50"))
        assert s.get(Signal, u.signal_id).features["zone"]["proxy"] == "iceberg PROXY (no MBO data)"
        ev = _z(ms + 60000, "EVENT", entry="20035", event_zone_hi="20040", event_zone_lo="20030")
        assert _run(s, r, ev).exits == []
        assert s.get(Signal, u.signal_id).features["zone_trail_stop"] == "20018.50"
        assert s.query(AuditLog).filter_by(action="order_flow.zone_trail").count() == 1
        opp = _run(s, r, _z(ms + 120000, "EVENT", direction="SHORT", entry="20030"))
        assert opp.exits == [(u.signal_id, "OF_ZONE_OPPOSING_EVENT")]
        assert _run(s, r, _z(ms + 180000, entry="20015")).updates == []  # not proven → audited skip
        codes = [a.payload["code"] for a in s.query(AuditLog).filter_by(action="order_flow.skip")]
        assert "OF_ZONE_NOT_PROVEN" in codes


def test_trail_exit_on_bar_and_exclusive(client, loaded_rules):
    from datetime import timedelta

    from app.clock import FixedClock
    from app.models import Bar
    from app.signals import strategy_service as SS
    from tests.integration.test_order_flow import AT

    r = _rules(loaded_rules.rules, exclusive=True)
    ms = _p()["bar_time_ms"]
    with client.app.state.sessionmaker() as s:
        assert _run(s, r, _p(ms=ms + 5)).updates == []  # AR alert while exclusive → OF_ZONE_EXCLUSIVE
        u = _run(s, r, _z(ms)).updates[0]
        sig = s.get(Signal, u.signal_id)
        sig.features = {**sig.features, "zone_trail_stop": "20018.50"}
        at = AT + timedelta(minutes=3)
        s.add(
            Bar(
                symbol="MNQ",
                tf="1",
                close_time=at,
                o=D(20020),
                h=D(20021),
                l=D(20017),
                c=D(20018),
                v=D(10),
                source="tv",
            )
        )
        s.commit()
        out = SS.run(s, rules=r, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)
        assert (u.signal_id, "OF_ZONE_TRAIL") in out.exits


def test_card_layers_gates(authed):
    card = next(x for x in authed.get("/api/strategies").json()["strategies"] if x["key"] == "order_flow_zone")
    assert card["setting"] == "strategy.order_flow_cfg.zone_atr.enabled" and card["zone_layers"][0]["key"] == "EVENT"
    ch = {
        "strategy.order_flow_cfg.zone_atr.enabled": True,
        "strategy.order_flow_cfg.zone_atr.modes": ["POSITION", "REVERSION"],
        "strategy.order_flow": True,
    }
    r = authed.put("/api/risk/settings", json={"changes": ch})
    assert r.status_code == 200, r.text
    from app.api.strategy_gates import describe

    ids = [g["id"] for g in {c["key"]: c for c in describe(authed.app.state.rules.rules)}["order_flow"]["gates"]]
    assert {"ZONE_EVENT", "ZONE_TIME", "ZONE_SETUP"} <= set(ids)
    of = authed.get("/api/orderflow?symbol=MNQ").json()["ar"]
    assert of["zone_enabled"] is True and of["zone_modes"] == ["POSITION", "REVERSION"]
