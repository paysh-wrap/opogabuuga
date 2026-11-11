"""D94: Trading-R1 research card — pure helpers (no venv, no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.research import trading_r1 as tr1


def _install(root: Path) -> None:
    exe = tr1.executable(root)
    exe.parent.mkdir(parents=True)
    exe.write_text("")


def test_status_not_configured_without_venv_or_key(tmp_path: Path) -> None:
    ok, msg = tr1.status(tmp_path, "sk")
    assert not ok and "not installed" in msg
    _install(tmp_path)
    ok, msg = tr1.status(tmp_path, None)
    assert not ok and "not configured" in msg
    assert tr1.status(tmp_path, "sk") == (True, "ready")


def test_child_env_is_built_from_scratch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAURIC_API_KEY", "leak")
    monkeypatch.setenv("OPENAI_API_KEY", "leak")
    monkeypatch.setenv("PATH", "/bin")
    env = tr1.child_env("sk-ant-x", tmp_path, 4321, "tok")
    assert env["ANTHROPIC_API_KEY"] == "sk-ant-x"
    assert env["TR1_HOME"] == str(tmp_path) == env["HOME"]
    assert env["TR1_PORT"] == "4321" and env["TR1_API_TOKEN"] == "tok"
    assert "TAURIC_API_KEY" not in env and "OPENAI_API_KEY" not in env  # no sync / other providers
    assert env["PATH"] == "/bin"
    assert tr1.home(tmp_path) == tmp_path / "data" / "tr1"


def test_body_validates_question() -> None:
    b = tr1.body("  What   drives gold\ntoday? ")
    assert b == {"question": "What drives gold today?", "mode": "research", "profile": "anthropic", "stream": False}
    with pytest.raises(ValueError):
        tr1.body("   ")
    with pytest.raises(ValueError):
        tr1.body("x" * (tr1.MAX_QUESTION + 1))


def test_parse_ok_error_and_malformed() -> None:
    r = tr1.parse({"text": "Gold is driven by real yields.", "termination": "final", "rounds": 3, "error": None})
    assert r == tr1.Result(True, "Gold is driven by real yields.", "final", "", 3)
    assert tr1.parse({"text": "", "error": "401 invalid key"}).error == "401 invalid key"
    e = tr1.parse({"text": "  ", "rounds": "x"})
    assert not e.ok and e.error == "empty answer" and e.rounds == 0
    assert tr1.parse(["nope"]) == tr1.Result(False, "", "", "malformed response", 0)
    assert len(tr1.parse({"text": "y" * 20000}).text) == tr1.MAX_TEXT
