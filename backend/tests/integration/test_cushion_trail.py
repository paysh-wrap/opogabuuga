"""D122: cushion level controls + dynamic trailing stop through the real controller / order manager / API."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

from app.config import CushionCfg, DynamicTrailCfg
from app.models import Account, AuditLog
from tests.integration.test_split_risk import AT, _ext, _qty, _setup, _sig


def _set_mll(st, aid, mll):
    with st.sessionmaker() as s:
        a = s.get(Account, aid)
        a.mll, a.mll_peak = D(mll), D(mll) + D(1000)
        s.commit()


def _run(st, mode, key, aid, features=None):
    sig = _sig(st, mode, key)
    if features is not None:
        from app.models import Signal

        with st.sessionmaker() as s:
            row = s.get(Signal, sig)
            row.features = {**(row.features or {}), **features}
            s.commit()
    return asyncio.run(st.controller.execute(sig, "automation", only=[aid]))[0]


def test_cushion_off_keeps_the_size(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], contracts=4, noise=True)
    _set_mll(st, aid, 24400)  # 60 % cushion — ignored while the toggle is OFF
    res = _run(st, "NOISE", "N1", aid)
    assert res.ok and _qty(st, _ext(st, aid)) == 4
    assert st.controller.om.trades[res.trade_ref].dyn_trail is None  # trail toggle OFF → NOISE keeps its own exits


def test_cushion_normal_level_keeps_the_size(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], contracts=4, noise=True, cushion=CushionCfg(noise=True))
    res = _run(st, "NOISE", "N1", aid)  # fresh account: cushion 1000 of 1000 = NORMAL
    assert res.ok and _qty(st, _ext(st, aid)) == 4


def test_cushion_reduce_level_takes_one_micro_off_and_tightens_the_trail(authed, clock):
    st, (aid,) = _setup(
        authed, clock, [("a", "25000")], contracts=4, noise=True,
        cushion=CushionCfg(noise=True), dynamic_trail=DynamicTrailCfg(noise=True),
    )  # fmt: skip
    _set_mll(st, aid, 24400)
    res = _run(st, "NOISE", "N1", aid)
    assert res.ok and _qty(st, _ext(st, aid)) == 3
    t = st.controller.om.trades[res.trade_ref]
    assert t.dyn_trail is not None and t.dyn_trail.k_minus == D("0.25") and t.dyn_trail.of_trail is None
    with st.sessionmaker() as s:
        row = s.query(AuditLog).filter_by(action="trade.cushion").one()
        assert row.payload["level"] == "REDUCE" and row.payload["contracts_after"] == 3


def test_cushion_minimal_level_one_micro_and_one_trade_a_day(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], contracts=4, ai_bias=True, cushion=CushionCfg(ai_bias=True))
    h = authed.app.state.rules
    h.rules = h.rules.model_copy(
        update={
            "strategy": h.rules.strategy.model_copy(
                update={"ai_bias_cfg": h.rules.strategy.ai_bias_cfg.model_copy(update={"contracts": 2})}
            )
        }
    )
    _set_mll(st, aid, 24650)  # 35 % → MINIMAL
    res = _run(st, "AI_BIAS", "A1", aid)
    assert res.ok, res
    assert _qty(st, _ext(st, aid)) == 1
    asyncio.run(st.controller.flatten(aid, "tester", "MANUAL_FLATTEN"))
    st.controller.om.trades.clear()
    res = _run(st, "AI_BIAS", "A2", aid)
    assert not res.ok and res.reason == "CUSHION_MAX_TRADES"


def test_cushion_stop_blocks_until_the_next_session(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], contracts=2, noise=True, cushion=CushionCfg(noise=True))
    _set_mll(st, aid, 24850)  # 15 % → STOP
    res = _run(st, "NOISE", "N1", aid)
    assert not res.ok and res.reason == "CUSHION_STOP"
    _set_mll(st, aid, 24000)  # cushion back to 100 % in the same session: still blocked
    res = _run(st, "NOISE", "N2", aid)
    assert not res.ok and res.reason == "CUSHION_STOP"
    with st.sessionmaker() as s:
        assert s.query(AuditLog).filter_by(action="risk.cushion_stop").count() == 1  # audited once
    clock.set(datetime(2026, 10, 14, 15, 0, tzinfo=UTC))  # next session
    authed.post("/api/attestation", json={"confirm": True})
    res = _run(st, "NOISE", "N3", aid)
    assert res.ok, res


def test_order_flow_ar_trade_gets_the_d101_trail_zone_trade_does_not(authed, clock):
    st, (aid,) = _setup(
        authed, clock, [("a", "25000")], order_flow=True, dynamic_trail=DynamicTrailCfg(order_flow=True)
    )
    res = _run(st, "ORDER_FLOW", "O1", aid)
    assert res.ok, res
    t = st.controller.om.trades[res.trade_ref]
    assert t.dyn_trail is not None and t.dyn_trail.of_trail == (5, D("1.0")) and t.dyn_trail.k_minus == 0
    asyncio.run(st.controller.flatten(aid, "tester", "MANUAL_FLATTEN"))
    st.controller.om.trades.clear()
    clock.set(AT.replace(hour=16))
    res = _run(st, "ORDER_FLOW", "O2", aid, features={"zone": {"signal": "POSITION"}})
    assert res.ok, res
    t = st.controller.om.trades[res.trade_ref]
    assert t.dyn_trail is not None and t.dyn_trail.of_trail is None


def test_controller_on_bar_feeds_the_bar_buffer_and_moves_the_stop(authed, clock):
    st, (aid,) = _setup(
        authed, clock, [("a", "25000")], contracts=1, noise=True, dynamic_trail=DynamicTrailCfg(noise=True)
    )
    res = _run(st, "NOISE", "N1", aid)
    assert res.ok, res
    ctl = st.controller
    t = ctl.om.trades[res.trade_ref]
    ms = int(AT.timestamp() * 1000)
    asyncio.run(ctl.on_bar("MNQ", D(20000), D(20025), D(19999), D(20024), AT, ms, "1"))
    asyncio.run(ctl.on_bar("MNQ", D(20000), D(20025), D(19999), D(20024), AT, ms + 60_000, "1H?"))  # bad tf: no bar
    assert len(ctl.om.bars["MNQ"]) == 1 and ctl.om.bars["MNQ"][0].close_ms == ms
    assert t.legs[0].stop > t.plan.entry  # +1.2R → breakeven + fee cover (protective move, no hold delay)


def test_dashboard_shows_the_cushion_level(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], noise=True, cushion=CushionCfg(noise=True))
    _set_mll(st, aid, 24400)
    row = next(a for a in authed.get("/api/dashboard").json()["accounts"] if a["id"] == aid)
    assert row["cushion"]["level"] == "REDUCE" and row["cushion"]["pct"] == "60.0"
    assert row["cushion"]["strategies"] == ["NOISE"] and row["cushion"]["unverified"] is True


def test_my_settings_toggles_are_versioned_and_validated(authed, clock):
    r = authed.put(
        "/api/risk/settings", json={"changes": {"strategy.cushion.noise": True, "strategy.dynamic_trail.ai_duo": True}}
    )
    assert r.status_code == 200, r.text
    s = r.json()["settings"]
    assert s["strategy.cushion.noise"] is True and s["strategy.dynamic_trail.ai_duo"] is True
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.cushion.reduce_min": "0.9"}})
    assert bad.status_code == 422
    bad = authed.put(
        "/api/risk/settings",
        json={"changes": {"strategy.dynamic_trail.steps": [{"until_r": "2", "k": "1"}, {"until_r": None, "k": "2"}]}},
    )
    assert bad.status_code == 422
