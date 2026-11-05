import pytest

from app.bias.tradingagents_adapter import TradingAgentsAdapter, map_rating

RMAP = {
    "BUY": "LONG_ONLY",
    "OVERWEIGHT": "LONG_ONLY",
    "HOLD": "NEUTRAL",
    "UNDERWEIGHT": "SHORT_ONLY",
    "SELL": "SHORT_ONLY",
}


@pytest.mark.parametrize(
    "raw,mapped,alert",
    [
        ("Buy", "LONG_ONLY", False),
        ("Overweight", "LONG_ONLY", False),
        ("OVERWEIGHT", "LONG_ONLY", False),
        ("Hold", "NEUTRAL", False),
        ("Underweight", "SHORT_ONLY", False),
        ("Sell", "SHORT_ONLY", False),
        ("REVIEW", "NO_TRADE", True),
        ("strong buy!!", "NO_TRADE", True),
        ("", "NO_TRADE", True),
        (None, "NO_TRADE", True),
    ],
)
def test_five_tier_map(raw, mapped, alert):
    assert map_rating(raw, RMAP) == (mapped, alert)


def test_env_uses_best_models_then_catalog_defaults():
    cat = {
        "anthropic": {"quick": ["claude-sonnet-5"], "deep": ["claude-opus-x"]},
        "google": {"quick": ["g1"], "deep": ["g2"]},
    }
    env = TradingAgentsAdapter.env_for({"llm_provider": "anthropic", "api_key": "k"}, cat)
    assert env == {
        "ANTHROPIC_API_KEY": "k",
        "TRADINGAGENTS_LLM_PROVIDER": "anthropic",
        "TRADINGAGENTS_QUICK_THINK_LLM": "claude-sonnet-5",
        "TRADINGAGENTS_DEEP_THINK_LLM": "claude-opus-5-5",
    }
    k = TradingAgentsAdapter.env_for({"llm_provider": "kimi", "api_key": "k"}, None)
    assert k["MOONSHOT_API_KEY"] == "k" and k["TRADINGAGENTS_DEEP_THINK_LLM"] == "kimi-k3"
    q = TradingAgentsAdapter.env_for({"llm_provider": "qwen", "api_key": "k"}, None)
    assert q["DASHSCOPE_API_KEY"] == "k" and q["TRADINGAGENTS_QUICK_THINK_LLM"] == "qwen3.8-flash"
    g = TradingAgentsAdapter.env_for({"llm_provider": "google", "api_key": "k"}, cat)
    assert g["TRADINGAGENTS_DEEP_THINK_LLM"] == "g2"  # no best-model entry → catalog default
    env = TradingAgentsAdapter.env_for({"llm_provider": "openai", "api_key": "k", "quick_think_llm": "m1"}, cat)
    assert env["TRADINGAGENTS_QUICK_THINK_LLM"] == "m1" and "TRADINGAGENTS_DEEP_THINK_LLM" not in env


async def test_timeout_and_missing_install(tmp_path):
    a = TradingAgentsAdapter(str(tmp_path / "nope"), "0.7.1", timeout_s=1)
    assert not (await a.version()).ok
    hang = tmp_path / "hang"
    hang.write_text("#!/bin/sh\nsleep 30\n")
    hang.chmod(0o755)
    a = TradingAgentsAdapter(str(hang), "0.7.1", timeout_s=0.5)
    r = await a._call({"cmd": "run"}, timeout_s=0.5)
    assert not r.ok and r.data["error"] == "timeout"


async def test_parent_api_keys_not_leaked_to_runner(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "parent-secret")
    dump = tmp_path / "envdump"
    dump.write_text('#!/bin/sh\ncat >/dev/null\nprintf \'{"ok": true, "k": "%s"}\' "$OPENAI_API_KEY"\n')
    dump.chmod(0o755)
    r = await TradingAgentsAdapter(str(dump), "0.7.1", 5)._call({"cmd": "version"})
    assert r.data["k"] == ""
