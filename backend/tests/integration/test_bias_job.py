from datetime import UTC, datetime

from app.bias import service as bias
from app.bias.tradingagents_adapter import RunnerResult
from app.signals.service import today_bias
from tests.integration.test_signals_flow import AT


def save_creds(c):
    from app.crypto import Vault
    from app.models import ApiCredential

    v = Vault(c.app.state.settings.master_key.get_secret_value())
    with c.app.state.sessionmaker() as s:
        s.add(ApiCredential(provider="tradingagents", ciphertext=v.seal({"llm_provider": "openai", "api_key": "sk-x"})))
        s.commit()


class FakeTA:
    def __init__(self, results):
        self.results, self.calls = results, []

    async def run(self, ticker, today, env):
        self.calls.append(ticker)
        return self.results.get(ticker, RunnerResult(False, {"error": "timeout"}))


def test_due():
    thu = datetime(2026, 11, 5, 11, 15, tzinfo=UTC)  # 06:15 ET
    assert bias.due(thu, "06:10", None, thu.date())
    assert not bias.due(thu, "06:10", "2026-11-05", thu.date())
    assert not bias.due(datetime(2026, 11, 5, 11, 0, tzinfo=UTC), "06:10", None, thu.date())  # 06:00
    assert not bias.due(datetime(2026, 11, 7, 12, 0, tzinfo=UTC), "06:10", None, thu.date())  # Saturday


def test_bias_not_configured_is_no_trade(authed):
    ta = FakeTA({})
    authed.app.state.ta = ta
    r = authed.post("/api/bias/run").json()["ran"]
    assert r == {"QQQ": "NO_TRADE"} and ta.calls == []
    d = authed.get("/api/bias").json()["decisions"]
    assert d[0]["raw"] == "NOT_CONFIGURED"
    assert authed.app.state.controller.notices[-1]["title"].startswith("Bias QQQ")


def test_bias_run_maps_and_does_not_rerun_success(authed):
    save_creds(authed)
    ta = FakeTA({"QQQ": RunnerResult(True, {"rating": "Overweight", "decision": "x", "version": "0.7.1"})})
    authed.app.state.ta = ta
    assert authed.post("/api/bias/run").json()["ran"] == {"QQQ": "LONG_ONLY"}
    assert authed.post("/api/bias/run").json()["ran"] == {}  # success is final for the session
    assert ta.calls == ["QQQ"]
    with authed.app.state.sessionmaker() as s:
        assert today_bias(s, AT.date(), "QQQ") == "LONG_ONLY"


def test_failed_bias_can_retry(authed):
    save_creds(authed)
    ta = FakeTA({})
    authed.app.state.ta = ta
    assert authed.post("/api/bias/run").json()["ran"] == {"QQQ": "NO_TRADE"}
    ta.results["QQQ"] = RunnerResult(True, {"rating": "Sell"})
    assert authed.post("/api/bias/run").json()["ran"] == {"QQQ": "SHORT_ONLY"}


def test_vibe_trading_blend_unblocks_strong_disagreement(authed, tmp_path):
    """D53: TradingAgents says long-only, Vibe-Trading strongly says SHORT → NEUTRAL (both sides), stored with notes."""
    import os
    import stat

    from app.crypto import Vault
    from app.models import ApiCredential, BiasDecision

    save_creds(authed)
    st = authed.app.state
    with st.sessionmaker() as s:
        v = Vault(st.settings.master_key.get_secret_value())
        s.add(ApiCredential(provider="vibetrading", ciphertext=v.seal({"llm_provider": "qwen", "api_key": "q"})))
        s.commit()
    exe = tmp_path / ".venv-vt" / ("Scripts/vibe-trading.exe" if os.name == "nt" else "bin/vibe-trading")
    exe.parent.mkdir(parents=True)
    exe.write_text('#!/bin/sh\necho \'VT_OUTLOOK {"direction": "SHORT", "confidence": 85, "reason": "risk-off"}\'\n')
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    st.settings.vt_root = tmp_path
    st.ta = FakeTA({"QQQ": RunnerResult(True, {"rating": "Overweight", "decision": "x", "version": "0.7.1"})})
    assert authed.post("/api/bias/run").json()["ran"] == {"QQQ": "NEUTRAL"}
    with st.sessionmaker() as s:
        row = s.query(BiasDecision).one()
        assert row.raw_rating.startswith("Overweight·VT SHORT 85") and "Vibe-Trading disagrees" in row.reasoning
    assert (tmp_path / "data" / "vibe-trading").is_dir()  # its runtime files stay inside the app's data folder
