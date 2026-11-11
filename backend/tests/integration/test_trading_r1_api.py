"""D94: Trading-R1 card API with a fake runner. Information only: never touches bias / gates / signals."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, ClassVar

import httpx
import pytest
from fastapi.testclient import TestClient

from app.research import trading_r1 as tr1


@pytest.fixture(autouse=True)
def _github(mock_http: dict[str, Any]) -> None:
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)


class FakeRunner:
    asked: ClassVar[list[str]] = []

    def __init__(self, root: Path, key: str) -> None:
        self.key = key

    async def research(self, question: str) -> tr1.Result:
        FakeRunner.asked.append(question)
        return tr1.Result(True, f"answer to {question}", "final", "", 2)


def _setup(c: TestClient, root: Path, install: bool = True, key: bool = True) -> None:
    st: Any = c.app.state  # type: ignore[attr-defined]
    st.settings.tr1_root = root
    st.tr1_runner_factory = FakeRunner
    if install:
        exe = tr1.executable(root)
        exe.parent.mkdir(parents=True)
        exe.write_text("")
    if key:
        assert c.put("/api/connections/tradingr1", json={"values": {"api_key": "sk-ant-secret123"}}).status_code == 200


def test_not_configured_without_venv(authed: TestClient, tmp_path: Path) -> None:
    _setup(authed, tmp_path, install=False)
    v = authed.get("/api/research/trading-r1").json()
    assert v["configured"] is False and "not installed" in v["message"] and v["last"] is None
    assert "never triggers or gates a trade" in v["label"]
    assert authed.post("/api/research/trading-r1", json={"question": "gold?"}).status_code == 409


def test_not_configured_without_key(authed: TestClient, tmp_path: Path) -> None:
    _setup(authed, tmp_path, key=False)
    v = authed.get("/api/research/trading-r1").json()
    assert v["configured"] is False and "API Keys" in v["message"]


def test_ask_runs_fake_runner_and_shows_answer(authed: TestClient, tmp_path: Path) -> None:
    _setup(authed, tmp_path)
    assert authed.get("/api/research/trading-r1").json()["configured"] is True
    r = authed.post("/api/research/trading-r1", json={"question": "What moves gold today?"})
    assert r.status_code == 202
    last = None
    for _ in range(50):
        last = authed.get("/api/research/trading-r1").json()["last"]
        if last:
            break
        time.sleep(0.02)
    assert last is not None and last["ok"] and last["text"] == "answer to What moves gold today?"
    assert "sk-ant-secret123" not in authed.get("/api/research/trading-r1").text
    assert authed.post("/api/research/trading-r1", json={"question": "   "}).status_code == 422


def test_requires_login(client: TestClient) -> None:
    assert client.get("/api/research/trading-r1").status_code == 401
