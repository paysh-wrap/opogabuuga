from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.auth import create_user
from app.clock import FixedClock
from app.config import LoadedRules, load_rules
from app.crypto import new_master_key
from app.main import create_app
from app.settings import REPO_ROOT, Settings

RULES_PATH = REPO_ROOT / "config" / "rules" / "lucid_daily_25k.yaml"
PASSWORD = "correct-horse-battery"
WEBHOOK_SECRET = "wh-secret-0123456789abcdef"


@pytest.fixture(scope="session")
def loaded_rules() -> LoadedRules:
    return load_rules(RULES_PATH)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(datetime(2026, 11, 5, 15, 0, tzinfo=UTC))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        master_key=SecretStr(new_master_key()),
        webhook_secret=SecretStr(WEBHOOK_SECRET),
        rules_path=RULES_PATH,
        web_dist=tmp_path / "no-dist",
        ta_python=str(tmp_path / "missing-python"),
        scheduler_enabled=False,
    )


Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
def mock_http() -> dict[str, Handler]:
    """Map URL prefix → handler. Unmatched requests fail loudly (no real network in unit tests)."""
    return {}


@pytest.fixture
def client(settings: Settings, clock: FixedClock, mock_http: dict[str, Handler]) -> Iterator[TestClient]:
    app = create_app(settings, clock)

    def route(req: httpx.Request) -> httpx.Response:
        for prefix, h in mock_http.items():
            if str(req.url).startswith(prefix):
                return h(req)
        raise AssertionError(f"unexpected outbound request {req.url}")

    with TestClient(app) as c:
        app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(route))
        with app.state.sessionmaker() as s:
            create_user(s, "admin", PASSWORD)
            s.commit()
        yield c


@pytest.fixture
def authed(client: TestClient) -> TestClient:
    r = client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    assert r.status_code == 200, r.text
    client.headers["x-csrf-token"] = r.json()["csrf"]
    return client
