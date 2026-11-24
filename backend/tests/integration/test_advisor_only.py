"""D176: TradingAgents is advice only for EVERY strategy: a DISAGREE / strongly-against call never changes a decision,
a failing / slow / no-key run never blocks entries, runs are timed from the 09:30 ET open (05:30 / 08:30 / 09:00)."""

import asyncio
from decimal import Decimal as D

import pytest

from app.bias import ar_pre_session as ARP
from app.bias.policy import Call
from app.clock import FixedClock
from app.config import ADVISED_MODES
from app.engine.trade_plan import Direction
from app.models import BiasDecision
from app.signals import strategy_service as SS
from tests.integration.test_ar_side_by_side import _et
from tests.integration.trade_helpers import AT, _setup, _sig


def test_runs_are_timed_from_the_0930_open(loaded_rules):
    assert ARP.run_times(loaded_rules.rules) == [(240, "05:30"), (60, "08:30"), (30, "09:00")]
    assert ARP.enabled(loaded_rules.rules) and "never blocks" in ARP.ADVICE_LABEL


def test_advice_text_per_strategy_and_no_call():
    assert "No call" in ARP.advice_text(None, None)["all"]
    a = ARP.advice_text("SHORT", 0.3)
    assert "NOISE + CANDACE trade unchanged" in a["main"] and "both sides" in a["order_flow"] and "70%" in a["all"]
    assert "mean-reversion" in ARP.advice_text("NEUTRAL", 0.5)["main"]


@pytest.mark.parametrize("mode", [*ADVISED_MODES, "NOISE"])
def test_strongly_against_advice_does_not_change_the_decision(client, loaded_rules, mode):
    """Every strategy path: a strong SELL call against a LONG signal leaves the gate result PASS."""
    with client.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating="SELL·VT SHORT 90", mapped="SHORT_ONLY", reasoning="", version=""))
        s.commit()
        sig = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=f"k-{mode}", direction=Direction.LONG, at=AT, gate=(True, "OK", ""),
            features={}, plan=(mode, D(100), D(99), D(102), D(1), D(2)), rules=loaded_rules.rules,
        )  # fmt: skip
        assert sig.status == "PASS" and sig.skip_reason is None


def test_confluence_g2_bias_never_blocks():
    from app.engine.confluence import _bias_ok

    for bias in ("NO_TRADE", "LONG_ONLY", "SHORT_ONLY", "NEUTRAL"):
        for d in Direction:
            assert _bias_ok(bias, d) == (True, "OK", False)


def test_no_call_without_key_never_blocks_an_entry(authed, clock):
    st, (a,) = _setup(authed, clock, [("a", "25000")], noise=True)
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[a]))[0].ok


def test_slow_run_is_cut_off_and_shown_as_advice_status(authed, clock, monkeypatch):
    from app.bias import service as bias
    from app.main import _ar_pre_session
    from app.models import AuditLog

    st = authed.app.state

    async def slow(*_a, **_k):
        await asyncio.sleep(5)

    monkeypatch.setattr(bias, "run_bias", slow)
    monkeypatch.setattr(ARP, "RUN_TIMEOUT_S", 0.05)
    clock.set(_et(8, 30))
    with st.sessionmaker() as s:
        asyncio.run(_ar_pre_session(authed.app, s, clock.now()))
        p = s.query(AuditLog).filter_by(action=ARP.ACTION).first().payload
        assert p["status"] == "NO_CALL" and "run failed" in p["reason"] and p["advice_only"] == ARP.ADVICE_LABEL
    d = authed.get("/api/dashboard").json()["ai_advice"]
    assert d["label"] == ARP.ADVICE_LABEL and [r["minutes_before"] for r in d["runs"]] == [240, 60, 30]
    assert authed.get("/api/strategies").json()["ai_advice"]["runs"][1]["results"][0]["status"] == "NO_CALL"


def test_old_saved_gate_mode_loads_as_advisory(authed):
    r = authed.put("/api/risk/settings", json={"changes": {"strategy.advisor.mode": "GATE"}, "note": "old"})
    assert r.status_code == 200
    assert authed.app.state.rules.rules.strategy.advisor.mode == "ADVISORY"
    assert Call(-1, 0.1, True)  # a strongly-against call exists; nothing above consumes it as a gate


# ---------- news handling is untouched by the combined option and by advice (D175 / D176) ----------


def test_combined_mode_flattens_both_accounts_at_news_and_advice_changes_nothing(authed, clock):
    from datetime import timedelta

    from app.engine.filters import NewsEvent
    from tests.integration.test_strategy_combined import _combined_rules

    st, (a, b) = _setup(authed, clock, [("a", "25000"), ("b", "25000")], noise=True)
    _combined_rules(st)
    with st.sessionmaker() as s:  # a strongly-against advice row exists: it must not change news handling
        s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating="SELL·VT SHORT 90", mapped="SHORT_ONLY", reasoning="", version=""))
        s.commit()
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[a]))[0].ok
    assert asyncio.run(st.controller.execute(_sig(st, "ORDER_FLOW", "O1"), "automation", only=[a, b]))[0].ok
    ev = NewsEvent(at=clock.now() + timedelta(minutes=2), title="CPI")  # event 2 min ahead: flatten before the release
    assert asyncio.run(st.controller.news_check([ev])) == "NEWS"
    assert all(x["positions"] == [] for x in authed.get("/api/positions").json()["accounts"])


def test_entries_inside_the_news_window_and_without_a_calendar_are_blocked_for_every_choice(loaded_rules):
    from datetime import timedelta

    from app.engine.filters import NewsEvent
    from app.signals.strategy_service import _gate

    r = loaded_rules.rules
    day_event = NewsEvent(at=AT, title="CPI")
    for delta in (-r.internal.no_entry_before_news_min, 0, 1):  # from the config margins, never a literal time
        ok, code, _ = _gate(r, "MNQ", AT + timedelta(minutes=delta), lambda _d: [day_event], True)
        assert not ok and code == "NEWS_BLACKOUT"
    ok, code, _ = _gate(r, "MNQ", AT, lambda _d: None, True)  # calendar failure = no trading, never blind
    assert not ok and code == "CALENDAR_MISSING"
