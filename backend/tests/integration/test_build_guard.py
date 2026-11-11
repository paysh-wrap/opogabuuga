"""D97: build identity in /api/health, local-only shutdown, no-store index.html, updater commit verification."""

import json

from fastapi.testclient import TestClient

from app import buildinfo, updater
from app.main import create_app
from app.settings import Settings


def _local(client: TestClient) -> TestClient:
    return TestClient(client.app, client=("127.0.0.1", 50000))


def test_health_reports_build_and_hides_pid_remotely(client, tmp_path, monkeypatch):
    v = tmp_path / "version.json"
    v.write_text(json.dumps({"commit": "abcdef1234567", "built_at": "2026-11-11T08:00:00Z"}))
    monkeypatch.setenv("PAYTIENCE_VERSION_FILE", str(v))
    d = client.get("/api/health").json()  # TestClient peer is "testclient": not local
    assert d["app"] == "paytience"
    assert d["build"] == {"commit": "abcdef1234567", "built_at": "2026-11-11T08:00:00Z"}
    assert d["started_at"] and d["executable"]
    assert "pid" not in d and "executable_path" not in d  # remote callers never see pid / full path
    loc = _local(client).get("/api/health").json()
    assert loc["pid"] > 0 and loc["executable_path"].endswith(d["executable"])
    # a tunnel reaches us from 127.0.0.1 too, but adds forwarding headers -> treated as remote
    tun = _local(client).get("/api/health", headers={"X-Forwarded-For": "203.0.113.9"}).json()
    assert "pid" not in tun


def test_shutdown_needs_local_and_token_and_hook(client, monkeypatch):
    loc = _local(client)
    ok = {"X-Paytience-Shutdown": "tok"}
    assert loc.post("/api/system/shutdown", headers=ok).status_code == 403  # no token configured: endpoint inert
    monkeypatch.setenv(buildinfo.SHUTDOWN_TOKEN_ENV, "tok")
    assert client.post("/api/system/shutdown", headers=ok).status_code == 403  # remote peer
    assert loc.post("/api/system/shutdown", headers={**ok, "X-Forwarded-For": "1.2.3.4"}).status_code == 403  # tunnel
    assert loc.post("/api/system/shutdown", headers={"X-Paytience-Shutdown": "bad"}).status_code == 403
    assert loc.post("/api/system/shutdown").status_code == 403
    assert loc.post("/api/system/shutdown", headers=ok).status_code == 409  # no hook (not the desktop launcher)
    called = []
    client.app.state.request_shutdown = lambda: called.append(1)
    assert loc.post("/api/system/shutdown", headers=ok).json() == {"ok": True}
    assert called == [1]


def test_shutdown_survives_notify_failure(client, monkeypatch):
    monkeypatch.setenv(buildinfo.SHUTDOWN_TOKEN_ENV, "tok")
    called = []
    client.app.state.request_shutdown = lambda: called.append(1)
    client.app.state.controller.notify = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
    assert _local(client).post("/api/system/shutdown", headers={"X-Paytience-Shutdown": "tok"}).status_code == 200
    assert called == [1]


def test_index_is_no_store_and_assets_immutable(settings: Settings, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>ui</html>")
    (dist / "assets" / "app-abc123.js").write_text("1")
    (dist / "sw.js").write_text("//sw")
    s = settings.model_copy(update={"web_dist": dist})
    with TestClient(create_app(s)) as c:
        assert c.get("/").headers["cache-control"] == "no-store"
        assert c.get("/dashboard").headers["cache-control"] == "no-store"  # SPA fallback
        assert c.get("/sw.js").headers["cache-control"] == "no-cache"
        a = c.get("/assets/app-abc123.js")
        assert a.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert c.get("/assets/missing.js").status_code == 404
        assert c.get("/api/nope").status_code == 404


# ---------- updater: the new app must run the NEW commit ----------
def test_commits_match():
    assert updater.commits_match("abcdef1234", "abcdef1")
    assert updater.commits_match("abcdef1", "ABCDEF1234")
    assert not updater.commits_match("abcdef1", "1234567")
    assert not updater.commits_match("dev", "dev") and not updater.commits_match("", "abc")


def test_healthy_start_confirms_only_the_expected_commit(tmp_path):
    (tmp_path / updater.EXPECTED_FILE).write_text("1234567890abcdef")
    msg = updater.on_healthy_start(tmp_path, "aaaaaaa1")  # still the OLD build answering
    assert msg and "aaaaaaa" in msg and "123456" in msg
    assert (tmp_path / updater.UNHEALTHY_FLAG).exists() and not (tmp_path / updater.HEALTHY_FLAG).exists()
    (tmp_path / updater.UNHEALTHY_FLAG).unlink()
    assert updater.on_healthy_start(tmp_path, "1234567890abcdef") is None
    assert (tmp_path / updater.HEALTHY_FLAG).exists() and not (tmp_path / updater.EXPECTED_FILE).exists()
    assert not (tmp_path / updater.UNHEALTHY_FLAG).exists()


def test_healthy_start_without_expected_file_is_unchanged(tmp_path):
    assert updater.on_healthy_start(tmp_path, "whatever") is None  # normal start, no update pending
    assert (tmp_path / updater.HEALTHY_FLAG).exists()


def test_bat_verifies_health_commit_before_ok(tmp_path):
    up = tmp_path / "u"
    s = updater.updater_script(
        tmp_path / "A", up / "n", up / "old", up, 1, expected_commit="1234567890abcdef; rm -rf /"
    )
    assert 'if exist "' + str(up / "unhealthy.flag") + '" goto stopnew' in s
    assert f'if exist "{up / "healthy.flag"}" goto verify' in s
    assert ":verify" in s and 'findstr /R /C:"commit.:.1234567"' in s and "/api/health" in s
    assert "rm -rf" not in s  # only hex survives into the batch file
    i = s.index(":verify")
    assert i < s.index(":ok") and s.index("goto stopnew", i) < s.index(":ok")
    assert s.index("where curl") < s.index("curl -s")  # no curl -> skip the extra check, never a false rollback
    plain = updater.updater_script(tmp_path / "A", up / "n", up / "old", up, 1)
    assert ":verify" not in plain
