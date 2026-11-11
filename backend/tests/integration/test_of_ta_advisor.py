"""D109: TradingAgents as an ADVISOR for Order Flow (toggle, scheduling, annotation, OF_TA_DISAGREES skip)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.bias import of_advisor as OFA
from app.bias.tradingagents_adapter import RunnerResult
from app.clock import FixedClock
from app.models import AuditLog, BiasDecision, Signal
from tests.integration.test_bias_job import FakeTA, save_creds
from tests.integration.test_order_flow import AT, _p, _run

RUN_AT = datetime(2026, 10, 12, 12, 31, tzinfo=UTC)  # Monday 08:31 ET = 1 h before the 09:30 window start


def _rules(base, **cfg):
    mnq = base.instruments["MNQ"].model_copy(update={"enabled": True, "windows": [("09:30", "16:00")]})
    of = base.strategy.order_flow_cfg.model_copy(update={"instruments": ["MNQ"], "ta_advisor": True, **cfg})
    st = base.strategy.model_copy(update={"order_flow": True, "order_flow_cfg": of})
    return base.model_copy(update={"strategy": st, "instruments": {**base.instruments, "MNQ": mnq}})


def test_advisor_time_and_due(loaded_rules):
    r = _rules(loaded_rules.rules)
    assert OFA.advisor_at(r) == "08:30" and OFA.proxies(r) == ["QQQ"]
    assert OFA.advisor_at(_rules(loaded_rules.rules, ta_advisor_lead_min=240)) == "05:30"
    early = r.instruments["MNQ"].model_copy(update={"windows": [("00:30", "16:00")]})
    assert OFA.advisor_at(r.model_copy(update={"instruments": {**r.instruments, "MNQ": early}})) == "00:00"
    assert OFA.due(RUN_AT, r, None, RUN_AT.date())
    assert not OFA.due(RUN_AT, r, "2026-10-12", RUN_AT.date())  # once per session
    assert not OFA.due(datetime(2026, 10, 12, 12, 29, tzinfo=UTC), r, None, RUN_AT.date())  # 08:29 ET
    assert not OFA.due(RUN_AT, _rules(loaded_rules.rules, ta_advisor=False), None, RUN_AT.date())  # default OFF
    off = r.model_copy(update={"strategy": r.strategy.model_copy(update={"order_flow": False})})
    assert not OFA.enabled(off)


def test_scheduler_reuses_bias_job_and_stores_advice(authed, clock):
    from app.main import _of_ta_advisor

    st = authed.app.state
    clock.set(RUN_AT)
    ta = FakeTA({"QQQ": RunnerResult(True, {"rating": "Sell", "decision": "x", "version": "0.7.1"})})
    st.ta = ta
    with st.sessionmaker() as s:
        asyncio.run(_of_ta_advisor(authed.app, s, clock.now()))  # toggle OFF (default) → nothing
        assert ta.calls == [] and s.query(AuditLog).filter_by(action=OFA.ACTION).count() == 0
    save_creds(authed)
    st.rules.rules = _rules(st.rules.rules)
    with st.sessionmaker() as s:
        asyncio.run(_of_ta_advisor(authed.app, s, clock.now()))
        asyncio.run(_of_ta_advisor(authed.app, s, clock.now()))  # done this session: no second run
        assert ta.calls == ["QQQ"] and s.query(BiasDecision).count() == 1
        adv = OFA.advice(s, "MNQ", RUN_AT.date())
        assert adv is not None and adv["code"] == "OF_TA_ADVICE" and adv["side"] == "SHORT" and adv["confidence"]
    d = authed.get("/api/orderflow?symbol=MNQ").json()["ta_advisor"]
    assert d["enabled"] is True and d["advisory"] is True and d["at"] == "08:30" and d["advice"]["side"] == "SHORT"
    assert d["setting"] == "strategy.order_flow_cfg.ta_advisor" and d["blocks"] is False


def test_failure_is_no_advice_never_a_block(authed, clock, monkeypatch):
    from app.bias import service as bias
    from app.main import _of_ta_advisor

    st = authed.app.state
    clock.set(RUN_AT)
    st.rules.rules = _rules(st.rules.rules)

    async def boom(*_a, **_k):
        raise RuntimeError("runner crashed")

    monkeypatch.setattr(bias, "run_bias", boom)
    with st.sessionmaker() as s:
        asyncio.run(_of_ta_advisor(authed.app, s, clock.now()))
        assert OFA.advice(s, "MNQ", RUN_AT.date())["side"] is None
        u = _run(s, _rules(st.rules.rules), _p()).updates[0]
        assert u.status == "PASS"
        assert s.get(Signal, u.signal_id).features["ta_advice"] == {"side": None, "agrees": None, "advisory": True}
    assert st.controller.notices[-1]["title"].startswith("Order Flow AI advisor")


def test_opposite_signal_annotated_skipped_only_with_blocks_and_proven_ledger(client, loaded_rules, monkeypatch):
    r = _rules(loaded_rules.rules)
    with client.app.state.sessionmaker() as s:
        s.add(
            BiasDecision(
                session_date=AT.date(), proxy="QQQ", raw_rating="SELL", mapped="SHORT_ONLY", reasoning="", version=""
            )
        )
        s.commit()
        OFA.record(s, r, FixedClock(AT), AT.date())
        u = _run(s, r, _p()).updates[0]  # LONG vs SHORT advice, blocks OFF → annotate + warn only
        assert u.status == "PASS"
        sig = s.get(Signal, u.signal_id)
        assert sig.features["ta_advice"]["agrees"] is False and sig.features["ta_advice"]["advisory"] is True
        assert s.query(AuditLog).filter_by(action="order_flow.ta_disagrees").count() == 1
        sig.features = {**sig.features, "state": "CLOSED"}
        s.commit()
        blocks = _rules(loaded_rules.rules, ta_advisor_blocks=True)
        u = _run(s, blocks, _p(ms=_p()["bar_time_ms"] + 60000)).updates[0]  # ledger not proven → still advisory
        assert u.status == "PASS"
        s.get(Signal, u.signal_id).features = {**s.get(Signal, u.signal_id).features, "state": "CLOSED"}
        s.commit()
        monkeypatch.setattr(OFA.L, "proven", lambda *_a: True)
        u = _run(s, blocks, _p(ms=_p()["bar_time_ms"] + 120000)).updates[0]
        assert (u.status, u.reason) == ("SKIP", "OF_TA_DISAGREES")
        same = _run(s, blocks, _p(ms=_p()["bar_time_ms"] + 180000, direction="SHORT"))  # agrees → no skip code
        assert all(x.reason != "OF_TA_DISAGREES" for x in same.updates)


def test_toggle_via_settings_and_pine_download(authed):
    r = authed.put(
        "/api/risk/settings", json={"changes": {"strategy.order_flow_cfg.ta_advisor": True}, "note": "D109 toggle"}
    )
    assert r.status_code == 200, r.text
    assert authed.app.state.rules.rules.strategy.order_flow_cfg.ta_advisor is True
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.order_flow_cfg.ta_advisor_blocks": True}})
    assert bad.status_code >= 400  # the block flag stays a plan-file decision
    p = authed.get("/api/pine/orderflow")
    assert p.status_code == 200 and "Paytience Order Flow" in p.text
