"""D53: Vibe-Trading second opinion — parse, blend (can only unblock), env, subprocess runner."""

import asyncio
import os
import stat

import pytest

from app.bias import vibe_trading as vt


def test_parse_takes_last_valid_line_and_rejects_garbage():
    out = (
        'thinking...\nVT_OUTLOOK {"direction": "short", "confidence": 40}\nmore\n'
        'VT_OUTLOOK {"direction": "LONG", "confidence": 72, "reason": "CPI beat"}\n'
    )
    assert vt.parse(out) == vt.Outlook("LONG", 72, "CPI beat")
    assert vt.parse("no line here") is None
    assert vt.parse('VT_OUTLOOK {"direction": "UP", "confidence": 50}') is None
    assert vt.parse('VT_OUTLOOK {"direction": "LONG", "confidence": 150}') is None
    assert vt.parse('VT_OUTLOOK {"direction": "LONG", "confidence": "x"}') is None
    assert vt.parse("VT_OUTLOOK {not json}") is None


@pytest.mark.parametrize(
    ("ta", "outlook", "final"),
    [
        ("NO_TRADE", vt.Outlook("LONG", 99, ""), "NO_TRADE"),  # TradingAgents is the backbone
        ("LONG_ONLY", None, "LONG_ONLY"),  # Vibe-Trading missing → TradingAgents alone
        ("LONG_ONLY", vt.Outlook("SHORT", 80, ""), "NEUTRAL"),  # strong disagreement → both sides
        ("SHORT_ONLY", vt.Outlook("LONG", 60, ""), "NEUTRAL"),
        ("LONG_ONLY", vt.Outlook("SHORT", 59, ""), "LONG_ONLY"),  # weak disagreement → TradingAgents decides
        ("LONG_ONLY", vt.Outlook("NEUTRAL", 90, ""), "LONG_ONLY"),
        ("LONG_ONLY", vt.Outlook("LONG", 90, ""), "LONG_ONLY"),
        ("NEUTRAL", vt.Outlook("SHORT", 99, ""), "NEUTRAL"),  # never blocks a side on its own
    ],
)
def test_blend_can_only_unblock(ta, outlook, final):
    assert vt.blend(ta, outlook)[0] == final


def test_env_for_providers():
    e = vt.env_for({"llm_provider": "anthropic", "api_key": "k"})
    assert (
        e["LANGCHAIN_PROVIDER"] == "anthropic" and e["ANTHROPIC_API_KEY"] == "k" and e["LANGCHAIN_TEMPERATURE"] == "1"
    )
    q = vt.env_for({"llm_provider": "qwen", "api_key": "q", "model": "qwen-max"})
    assert (
        q["LANGCHAIN_PROVIDER"] == "dashscope"
        and q["DASHSCOPE_API_KEY"] == "q"
        and q["LANGCHAIN_MODEL_NAME"] == "qwen-max"
    )
    with pytest.raises(ValueError):
        vt.env_for({"llm_provider": "anthropic", "api_key": ""})
    with pytest.raises(ValueError):
        vt.env_for({"llm_provider": "nope", "api_key": "k"})
    assert "GLD" in vt.prompt("GLD", "Micro Gold", "2026-11-06", {"last": 1}) and "VT_OUTLOOK" in vt.prompt(
        "QQQ", "x", "d", None
    )


def _fake_exe(tmp_path, body):
    exe = tmp_path / ".venv-vt" / ("Scripts/vibe-trading.exe" if os.name == "nt" else "bin/vibe-trading")
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\n" + body)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return exe


def test_run_reads_outlook_and_handles_failures(tmp_path):
    exe = _fake_exe(
        tmp_path,
        'echo "Status: SUCCESS"\necho \'VT_OUTLOOK {"direction": "SHORT", "confidence": 77, "reason": "r"}\'\n',
    )
    o, status = asyncio.run(vt.run(exe, {"X": "1"}, "q", tmp_path / "home"))
    assert o == vt.Outlook("SHORT", 77, "r") and status == "ok"
    bad = tmp_path / "b"
    bad.mkdir()
    exe2 = _fake_exe(bad, 'echo "Reason: provider error 401"\nexit 1\n')
    o, status = asyncio.run(vt.run(exe2, {}, "q", tmp_path / "home"))
    assert o is None and "401" in status
    assert asyncio.run(vt.run(tmp_path / "missing", {}, "q", tmp_path))[1] == "not installed"
    slow = tmp_path / "s"
    slow.mkdir()
    exe3 = _fake_exe(slow, "sleep 5\n")
    assert asyncio.run(vt.run(exe3, {}, "q", tmp_path / "home", timeout_s=1)) == (None, "timeout")
