"""D84 TradingAgents MGC research inside the AI Duo button: research job (mocked subprocesses), setup → plan path,
Vibe-Trading agreement, reason codes, key-not-connected fallback, API block."""

import asyncio
import json
import os
import stat
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app.bias import ta_mgc_research as TR
from app.bias.tradingagents_adapter import RunnerResult
from app.clock import FixedClock
from app.models import AuditLog, BiasDecision, Signal, TradePlanRow
from app.signals import strategy_service as SS
from tests.integration.test_ai_duo import _bars, _london, _noise_signal
from tests.integration.test_bias_job import save_creds
from tests.integration.test_strategy_service import _rules, _sessions

SETUP = {"side": "LONG", "confidence": 72, "entry_low": 2700, "entry_high": 2702, "invalidation": 2690,
         "target": 2730, "valid_until": "09:00", "reasons": ["DXY falling"]}  # fmt: skip
VT_LONG = {"direction": "LONG", "confidence": 80, "reason": "r"}


@pytest.fixture
def db(client):
    return client.app.state.sessionmaker


def _research(s, today, setup=SETUP, vt=VT_LONG, error="", note=""):
    s.add(BiasDecision(session_date=date(today.year, today.month, today.day), proxy="GLD.RS", raw_rating="x",
                       mapped="NEUTRAL", version="t", reasoning=json.dumps(
                           {"setup": setup, "vt": vt, "vt_note": note, "error": error, "report": "rep"})))  # fmt: skip
    s.commit()


def _go(s, rules, today, minutes=5):
    start = _london(today)
    return SS.run(s, rules=rules, clock=FixedClock(start), calendar=lambda _d: [], symbol="MGC", tf="1",
                  at=start + timedelta(minutes=minutes))  # fmt: skip


def _day(s, base=D(2701)):
    today = _sessions(2)[-1]
    _bars(s, "MGC", _london(today), {}, base, n=400)
    return today


def test_setup_in_zone_with_vibe_agreement_becomes_a_paper_plan(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _day(s)
        _research(s, today)
        out = _go(s, rules, today)
        assert [u.status for u in out.updates] == ["PASS"]
        sig = s.get(Signal, out.updates[0].signal_id)
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert sig.symbol == "MGC" and sig.direction == "LONG" and sig.features["mode"] == "RESEARCH"
        assert plan.mode == "AI_DUO" and plan.entry == D(2701) and plan.stop == D("2689.6")
        assert D("1.5") <= plan.rr <= D("3.0") and sig.features["paper_only"] is True
        assert sig.features["reasons"] == ["DXY falling"] and sig.features["zone"] == ["2700", "2702"]
        assert _go(s, rules, today, 6).updates == []  # one decision per day
        assert s.query(AuditLog).filter_by(action="ai_duo.decision").one().payload["code"] == "TAKEN"


def test_between_1_5r_and_2r_is_allowed_and_tagged(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _day(s)
        _research(s, today, {**SETUP, "target": 2721})  # 20 pts over 11.4 risk = 1.75R
        out = _go(s, rules, today)
        sig = s.get(Signal, out.updates[0].signal_id)
        assert out.updates[0].status == "PASS" and sig.features["below_preferred_2r"] is True
    with db() as s:  # and the API/ledger list shows the tag
        from app.bias.ledger import duo_decisions

        assert duo_decisions(s, ["MGC"])[0]["below_preferred_2r"] is True


@pytest.mark.parametrize(
    ("kw", "code"),
    [
        ({"vt": {"direction": "SHORT", "confidence": 85, "reason": "r"}}, "AI_DISAGREE"),
        ({"vt": {"direction": "NEUTRAL", "confidence": 85, "reason": "r"}}, "AI_NEUTRAL"),
        ({"vt": {"direction": "LONG", "confidence": 40, "reason": "r"}}, "AI_NOT_STRONG"),
        ({"vt": None, "note": "timeout"}, "AI_VT_MISSING"),
        ({"setup": {**SETUP, "side": "NONE"}}, "RESEARCH_NO_TRADE"),
        ({"setup": {**SETUP, "confidence": 30}}, "SETUP_CONF_LOW"),
        ({"setup": {**SETUP, "target": 2716}}, "RR_BELOW_MIN"),
        ({"setup": {**SETUP, "invalidation": 2701.5}}, "SETUP_LEVELS_INVALID"),
        ({"setup": None}, "SETUP_MALFORMED"),
        ({"setup": {**SETUP, "valid_until": "03:02"}}, "SETUP_EXPIRED"),
        ({"setup": {**SETUP, "valid_until": "never"}}, "SETUP_MALFORMED"),
    ],
)
def test_every_refusal_is_one_logged_skip_with_a_reason_code(db, loaded_rules, kw, code):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _day(s)
        _research(s, today, **kw)
        out = _go(s, rules, today)
        assert [(u.status, u.reason) for u in out.updates] == [("SKIP", code)]
        assert s.query(TradePlanRow).count() == 0  # a skip carries no plan
        assert s.query(AuditLog).filter_by(action="ai_duo.decision").one().payload["code"] == code


def test_stop_too_wide_vs_the_noise_dollar_stop(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _day(s)
        _research(s, today, {**SETUP, "invalidation": 2650, "target": 2850})  # 51 pts risk > the 24.6 pt cap
        assert _go(s, rules, today).updates[0].reason == "STOP_TOO_WIDE"


def test_price_already_through_the_invalidation(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _day(s, D(2685))  # already below the invalidation
        _research(s, today)
        assert _go(s, rules, today).updates[0].reason == "SETUP_INVALIDATED"


def test_price_above_the_zone_waits_then_skips_at_window_end(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _sessions(2)[-1]
        _bars(s, "MGC", _london(today), {}, D(2715), n=600)  # above the zone
        _research(s, today, {**SETUP, "valid_until": "11:30"})
        assert _go(s, rules, today, 5).updates == []  # keeps waiting
        assert _go(s, rules, today, 8 * 60 + 30).updates[0].reason == "NO_ENTRY_IN_ZONE"  # 11:30 ET


def test_failed_research_waits_for_the_retry_then_skips_at_window_end(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _day(s)
        _research(s, today, setup=None, vt=None, error="timeout")
        assert _go(s, rules, today).updates == []  # the job retries every 30 min; no decision yet
        out = _go(s, rules, today, 8 * 60 + 30)  # 11:30 ET
        assert out.updates[0].reason == "RESEARCH_FAILED"


def test_without_research_the_normal_duo_path_is_unchanged(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _day(s)  # no research row (key not connected): nothing from the research path
        assert _go(s, rules, today).updates[0].reason == "AI_MISSING"  # the daily-call path asks for its AI call


def test_vibe_gate_never_opens_against_an_open_noise_for_mgc_and_excluded_minutes(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _sessions(2)[-1]  # 09:30 ET
        _bars(s, "MGC", today - timedelta(minutes=30), {}, D(2701), n=60)
        _research(s, today)
        # bar closing 09:31..09:35 touches the excluded 09:30–09:35 minutes: never a trigger
        for mins in (1, 3, 5):
            assert SS.run(s, rules=rules, clock=FixedClock(today), calendar=lambda _d: [], symbol="MGC", tf="1",
                          at=today + timedelta(minutes=mins)).updates == []  # fmt: skip
        _noise_signal(s, today, "SHORT")  # NOISE is MNQ only: no clash on MGC (METALS)
        assert SS.run(s, rules=rules, clock=FixedClock(today), calendar=lambda _d: [], symbol="MGC", tf="1",
                      at=today + timedelta(minutes=6)).updates[0].status in ("PASS", "SKIP")  # fmt: skip


# ---------- research job (subprocesses mocked) ----------
class FakeTA:
    def __init__(self, res):
        self.res, self.calls = res, []

    async def research(self, ticker, today, env, market, context):
        self.calls.append((ticker, market, context))
        return self.res


def _vt_exe(tmp_path, line):
    exe = tmp_path / ".venv-vt" / ("Scripts/vibe-trading.exe" if os.name == "nt" else "bin/vibe-trading")
    exe.parent.mkdir(parents=True)
    exe.write_text(f"#!/bin/sh\necho '{line}'\n")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return tmp_path


def _run_job(authed, ta, vt_root=None):
    from app.crypto import Vault

    st = authed.app.state
    rules = _rules(st.rules.rules if False else authed.app.state.rules.rules and _loaded(authed), ai_duo=True)
    with st.sessionmaker() as s:
        return asyncio.run(
            TR.run_research(s, ta, Vault(st.settings.master_key.get_secret_value()), rules, st.clock,
                            date(2026, 11, 10), st.controller.notify, vt_root=vt_root,
                            context={"openbb": {"last": 2700}}, calendar=["08:30 CPI"])
        )  # fmt: skip


def _loaded(authed):
    class L:
        rules = authed.app.state.rules.rules

    return L


def test_no_key_does_nothing_and_the_page_says_so(authed):
    ta = FakeTA(RunnerResult(True, {"setup": SETUP}))
    assert _run_job(authed, ta) == "NOT_CONNECTED" and ta.calls == []
    with authed.app.state.sessionmaker() as s:
        assert s.query(BiasDecision).count() == 0
    d = authed.get("/api/strategies").json()["ta_mgc"]
    assert d["connected"] is False and d["message"] == "AI key not connected" and d["research"] is None


def test_research_is_stored_with_vibe_opinion_and_shown(authed, tmp_path):
    save_creds(authed)
    vt = _vt_exe(tmp_path, 'VT_OUTLOOK {"direction": "LONG", "confidence": 80, "reason": "gold bid"}')
    from app.crypto import Vault
    from app.models import ApiCredential

    st = authed.app.state
    with st.sessionmaker() as s:
        v = Vault(st.settings.master_key.get_secret_value())
        s.add(ApiCredential(provider="vibetrading", ciphertext=v.seal({"llm_provider": "qwen", "api_key": "q"})))
        s.commit()
    ta = FakeTA(RunnerResult(True, {"setup": SETUP, "report": "full report", "version": "0.7.1"}))
    assert _run_job(authed, ta, vt) == "STORED"
    assert ta.calls[0][0:2] == ("GLD", "MGC") and ta.calls[0][2]["calendar"] == ["08:30 CPI"]
    with st.sessionmaker() as s:
        row = s.query(BiasDecision).one()
        assert row.proxy == "GLD.RS" and row.raw_rating == "LONG 72·VT LONG 80" and row.version == "0.7.1"
        assert json.loads(row.reasoning)["vt"]["reason"] == "gold bid"
        assert s.query(AuditLog).filter_by(action="ta_mgc.research").count() == 1
    assert TR.latest.__name__ == "latest"
    # the live accuracy ledger never sees the research rows (proxy GLD.RS, like backfill QQQ.BF)
    with st.sessionmaker() as s:
        from app.bias import ledger

        assert ledger._calls(s, "GLD", date(2026, 1, 1), date(2026, 12, 31)) == []


def test_runner_failure_is_stored_and_notified_not_raised(authed):
    save_creds(authed)
    ta = FakeTA(RunnerResult(False, {"error": "timeout"}))
    assert _run_job(authed, ta) == "ERROR"
    with authed.app.state.sessionmaker() as s:
        row = s.query(BiasDecision).one()
        assert json.loads(row.reasoning)["error"] == "timeout" and row.mapped == "NO_TRADE"
    assert any("research failed" in n["title"] for n in authed.app.state.controller.notices)


def test_missing_vibe_connection_is_noted(authed):
    save_creds(authed)
    assert _run_job(authed, FakeTA(RunnerResult(True, {"setup": SETUP}))) == "STORED"
    with authed.app.state.sessionmaker() as s:
        assert json.loads(s.query(BiasDecision).one().reasoning)["vt_note"] == "Vibe-Trading not connected"


def test_scheduler_step_is_a_noop_when_off_or_without_key(authed, clock):
    from datetime import UTC, datetime

    from app.main import _ta_mgc_research

    st = authed.app.state
    clock.set(datetime(2026, 11, 10, 7, 50, tzinfo=UTC))  # 02:50 ET, Tuesday
    ta = FakeTA(RunnerResult(True, {"setup": SETUP}))
    st.ta = ta
    with st.sessionmaker() as s:
        asyncio.run(_ta_mgc_research(authed.app, s, clock.now()))  # AI Duo off → nothing
        h = st.rules
        h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"ai_duo": True})})
        asyncio.run(_ta_mgc_research(authed.app, s, clock.now()))  # on, but no key → nothing, no crash
        assert ta.calls == [] and s.query(BiasDecision).count() == 0
    save_creds(authed)
    with st.sessionmaker() as s:
        asyncio.run(_ta_mgc_research(authed.app, s, clock.now()))
        assert len(ta.calls) == 1 and s.query(BiasDecision).count() == 1
        asyncio.run(_ta_mgc_research(authed.app, s, clock.now()))  # done today: no second run
        assert len(ta.calls) == 1


def test_api_block_shows_latest_research_and_decision(authed):
    with authed.app.state.sessionmaker() as s:
        _research(s, _sessions(2)[-1])
    d = authed.get("/api/strategies").json()["ta_mgc"]
    assert (
        d["research"]["setup"]["side"] == "LONG"
        and d["research"]["vt"]["direction"] == "LONG"
        and d["decision"] is None
    )
