"""Uses the REAL installed TauricResearch/TradingAgents (make tradingagents). No LLM calls."""

from pathlib import Path

import pytest

from app.bias.tradingagents_adapter import TradingAgentsAdapter
from app.settings import REPO_ROOT

TA_PY = REPO_ROOT / ".venv-ta" / "bin" / "python"
pytestmark = pytest.mark.skipif(not Path(TA_PY).exists(), reason="run `make tradingagents` first")


async def test_installed_version_matches_pin(loaded_rules):
    a = TradingAgentsAdapter(str(TA_PY), loaded_rules.rules.bias.pinned_version, 120)
    r = await a.version()
    assert r.ok, r.data
    assert r.data["version"] == loaded_rules.rules.bias.pinned_version == "0.7.1"


async def test_catalog_lists_supported_providers():
    r = await TradingAgentsAdapter(str(TA_PY), "0.7.1", 120).catalog()
    assert r.ok, r.data
    for p in ("openai", "anthropic", "google"):
        assert r.data["catalog"][p]["quick"], p


async def test_run_without_key_fails_cleanly_not_silently():
    r = await TradingAgentsAdapter(str(TA_PY), "0.7.1", 120).run(
        "QQQ", __import__("datetime").date(2026, 11, 5), {"TRADINGAGENTS_LLM_PROVIDER": "openai", "OPENAI_API_KEY": ""}
    )
    assert not r.ok and r.data.get("error")
