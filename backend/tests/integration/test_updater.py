"""D88: desktop auto-update — version compare, token secrecy, blocks, checksum, no-token path, .bat text."""

import hashlib
import io
import json
import zipfile

import httpx
import pytest

from app import updater
from app.models import Account
from app.updater import UpdateError, Version

OLD = Version("a" * 40, "2026-11-01T00:00:00Z")
TOKEN = "github_pat_SECRET_never_returned_123"


def _zip() -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("Paytience/Paytience.exe", "exe")
        z.writestr("Paytience/_internal/x.txt", "x")
    return b.getvalue()


def _release(data: bytes, digest: str | None = None, sha: str = "b" * 40) -> dict:
    return {
        "body": f"commit: {sha}\nDownload...",
        "updated_at": "2026-11-10T00:00:00Z",
        "assets": [
            {
                "name": updater.ASSET,
                "url": "https://api.github.com/repos/paysh-wrap/opogabuuga/releases/assets/1",
                "size": len(data),
                "digest": digest or "sha256:" + hashlib.sha256(data).hexdigest(),
                "updated_at": "2026-11-10T00:00:00Z",
            }
        ],
    }


def test_version_compare():
    assert updater.is_newer(OLD, "b" * 40, "2026-11-10T00:00:00Z")
    assert not updater.is_newer(OLD, "a" * 7, "2026-11-10T00:00:00Z")  # same commit (short sha)
    assert not updater.is_newer(OLD, "b" * 40, "2026-10-01T00:00:00Z")  # older release
    assert not updater.is_newer(Version("dev", ""), "b" * 40, "2026-11-10T00:00:00Z")
    assert not updater.is_newer(OLD, None, "")
    assert updater.is_newer(Version("a" * 40, ""), "b" * 40, "")
    assert updater.release_commit({"body": "commit: ABCDEF1"}) == "abcdef1"
    assert updater.release_commit({"target_commitish": "c" * 40}) == "c" * 40
    assert updater.release_commit({"target_commitish": "main"}) is None


def test_load_version(tmp_path):
    p = tmp_path / "version.json"
    assert updater.load_version(p).commit == "dev"
    p.write_text(json.dumps({"commit": "abc", "built_at": "2026-11-10T00:00:00Z"}))
    assert updater.load_version(p) == Version("abc", "2026-11-10T00:00:00Z")


def test_block_reason():
    assert updater.block_reason(0, 0, "OFF") is None
    assert "open position" in updater.block_reason(1, 0, "OFF")
    assert "armed" in updater.block_reason(0, 2, "OFF")
    assert "SEMI" in updater.block_reason(0, 0, "SEMI")


async def test_no_token_never_calls_github():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: pytest.fail("no call"))) as http:
        assert (await updater.check(http, None, OLD))["reason"] == "no_token"


@pytest.mark.parametrize("code", [401, 404, 500])
async def test_check_errors(code):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(code))) as http:
        with pytest.raises(UpdateError):
            await updater.check(http, TOKEN, OLD)


async def test_checksum_mismatch_aborts(tmp_path):
    data = _zip()
    rel = _release(data, digest="sha256:" + "0" * 64)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=data))) as http:
        with pytest.raises(UpdateError, match="Checksum"):
            await updater.download(http, TOKEN, rel["assets"][0], tmp_path)
        assert not (tmp_path / updater.ASSET).exists()
        bad_size = {**rel["assets"][0], "size": 1}
        with pytest.raises(UpdateError, match="Size"):
            await updater.download(http, TOKEN, bad_size, tmp_path)


async def test_download_and_extract_ok(tmp_path):
    data = _zip()
    seen = {}

    def h(r):
        seen.update(r.headers)
        return httpx.Response(200, content=data)

    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as http:
        z = await updater.download(http, TOKEN, _release(data)["assets"][0], tmp_path)
    assert seen["accept"] == "application/octet-stream"
    new = updater.extract(z, tmp_path / "staging")
    assert (new / "Paytience.exe").is_file()


def test_extract_rejects_bad_zip(tmp_path):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("../evil.exe", "x")
    (tmp_path / "u.zip").write_bytes(b.getvalue())
    with pytest.raises(UpdateError, match="Unsafe"):
        updater.extract(tmp_path / "u.zip", tmp_path / "s")
    (tmp_path / "c.zip").write_bytes(b"not a zip")
    with pytest.raises(UpdateError, match="corrupt"):
        updater.extract(tmp_path / "c.zip", tmp_path / "s")


def test_bat_script_text(tmp_path):
    app, data = tmp_path / "Paytience", tmp_path / "Paytience" / "paytience-data"
    up = data / "updates"
    s = updater.updater_script(app, up / "staging" / "Paytience", up / "old-1", up, 4242)
    assert s.startswith("@echo off") and "\r\n" in s
    assert "PID eq 4242" in s
    assert "taskkill /PID 4242 /T /F" in s and s.index("taskkill /PID 4242") < s.index(":exited")
    assert "if %w% geq 45" in s and ":exited" in s
    assert f'move "{app}\\_internal" "{up / "old-1"}\\"' in s
    assert f'start "" "{app}\\Paytience.exe"' in s
    assert "healthy.flag" in s and ":restore" in s and "update-failed.txt" in s
    # the swap only ever moves Paytience.exe and _internal — paytience-data is never moved or deleted
    for line in s.splitlines():
        if line.startswith(("move", "rmdir", "del")) or "rmdir" in line:
            assert "paytience-data\\" not in line.split('"')[1] + "\\" or "updates" in line
    assert 'rmdir /s /q "' + str(data) + '"' not in s
    assert s.index("goto ok") < s.index(":stopnew")


def test_on_healthy_start(tmp_path):
    assert updater.on_healthy_start(tmp_path / "missing") is None
    (tmp_path / "old-1").mkdir()
    assert updater.on_healthy_start(tmp_path) is None
    assert (tmp_path / "healthy.flag").exists() and not (tmp_path / "old-1").exists()
    (tmp_path / "update-failed.txt").write_text("Update failed")
    assert updater.on_healthy_start(tmp_path) == "Update failed"


# ---------- API ----------
def _gh(mock_http) -> dict:
    """One GitHub router: longest matching prefix wins (the repo URL is a prefix of the release/asset URLs)."""
    routes: dict = {
        "https://api.github.com/": lambda r: httpx.Response(200, json=[{"name": "v0.7.1"}]),
        "https://api.github.com/repos/paysh-wrap/opogabuuga": lambda r: httpx.Response(200, json={}),
    }

    def h(r):
        u = str(r.url)
        return routes[max((k for k in routes if u.startswith(k)), key=len)](r)

    mock_http["https://api.github.com/"] = h
    return routes


def _save_token(authed, mock_http):
    routes = _gh(mock_http)
    r = authed.put("/api/connections/github_updates", json={"values": {"token": TOKEN}})
    assert r.status_code == 200, r.text
    assert TOKEN not in r.text
    return routes


def test_token_saved_encrypted_never_returned(authed, mock_http, caplog):
    _save_token(authed, mock_http)
    assert TOKEN not in authed.get("/api/connections").text
    v = next(x for x in authed.get("/api/connections").json()["connections"] if x["id"] == "github_updates")
    assert v["status"] == "connected" and v["category"] == "updates"
    for path in ("/api/connections", "/api/updates"):
        assert TOKEN not in authed.get(path).text
    assert TOKEN not in caplog.text
    st = authed.get("/api/updates").json()
    assert st["token_set"] and st["version"]["commit"] == "dev" and st["desktop"] is False


def test_check_without_token(authed):
    assert authed.get("/api/updates").json()["token_set"] is False
    r = authed.post("/api/updates/check")
    assert r.status_code == 200 and r.json()["available"] is False and r.json()["reason"] == "no_token"


def test_check_failure_is_reported(authed, mock_http):
    routes = _save_token(authed, mock_http)
    routes[updater.RELEASE_URL] = lambda r: httpx.Response(401)
    r = authed.post("/api/updates/check")
    assert r.status_code == 502 and "rejected" in r.json()["detail"]
    assert authed.get("/api/updates").json()["last_check"]["error"]


def test_install_requires_desktop(authed):
    assert authed.post("/api/updates/install").status_code == 409


def test_install_blocked_when_armed(authed, mock_http, monkeypatch, tmp_path):
    monkeypatch.setenv("PAYTIENCE_APP_DIR", str(tmp_path))
    monkeypatch.setenv("PAYTIENCE_UPDATES_DIR", str(tmp_path / "updates"))
    monkeypatch.setenv("PAYTIENCE_UPDATE_DRY_RUN", "1")
    app = authed.app
    with app.state.sessionmaker() as s:
        s.add(Account(broker_account_id="X1", stage="EVAL", drawdown_type="eod", armed=True))
        s.commit()
    r = authed.post("/api/updates/install")
    assert r.status_code == 409 and "armed" in r.json()["detail"]
    assert "armed" in authed.get("/api/updates").json()["blocked"]


def test_install_blocked_when_position_open(authed, monkeypatch, tmp_path):
    monkeypatch.setenv("PAYTIENCE_APP_DIR", str(tmp_path))
    monkeypatch.setenv("PAYTIENCE_UPDATES_DIR", str(tmp_path / "updates"))
    monkeypatch.setenv("PAYTIENCE_UPDATE_DRY_RUN", "1")

    async def one(_s):
        return [object()]

    monkeypatch.setattr(authed.app.state.controller, "open_positions", one)
    r = authed.post("/api/updates/install")
    assert r.status_code == 409 and "open position" in r.json()["detail"]


def test_install_dry_run_writes_script(authed, mock_http, monkeypatch, tmp_path):
    up = tmp_path / "updates"
    monkeypatch.setenv("PAYTIENCE_APP_DIR", str(tmp_path))
    monkeypatch.setenv("PAYTIENCE_UPDATES_DIR", str(up))
    monkeypatch.setenv("PAYTIENCE_UPDATE_DRY_RUN", "1")
    vf = tmp_path / "version.json"
    vf.write_text(json.dumps({"commit": OLD.commit, "built_at": OLD.built_at}))
    monkeypatch.setenv("PAYTIENCE_VERSION_FILE", str(vf))
    routes = _save_token(authed, mock_http)
    data = _zip()
    routes[updater.RELEASE_URL] = lambda r: httpx.Response(200, json=_release(data))
    routes["https://api.github.com/repos/paysh-wrap/opogabuuga/releases/assets/"] = lambda r: httpx.Response(
        200, content=data
    )
    assert authed.post("/api/updates/check").json()["available"] is True
    r = authed.post("/api/updates/install")
    assert r.status_code == 200, r.text
    assert (up / "apply-update.bat").exists() and (up / "staging" / "Paytience" / "Paytience.exe").exists()
    assert (up / updater.EXPECTED_FILE).read_text() == "b" * 40  # D97: the new app must report exactly this commit
    assert 'findstr /R /C:"commit.:.bbbbbbb"' in (up / "apply-update.bat").read_text()
    # checksum mismatch → aborted, banner/notify, no script
    (up / "apply-update.bat").unlink()
    routes[updater.RELEASE_URL] = lambda r: httpx.Response(200, json=_release(data, "sha256:" + "1" * 64))
    r = authed.post("/api/updates/install")
    assert r.status_code == 502 and "Checksum" in r.json()["detail"]
    assert not (up / "apply-update.bat").exists()
    (up / "update-failed.txt").write_text("Update failed")
    assert authed.get("/api/updates").json()["failed_update"] == "Update failed"
    authed.post("/api/updates/dismiss-failure")
    assert authed.get("/api/updates").json()["failed_update"] is None
