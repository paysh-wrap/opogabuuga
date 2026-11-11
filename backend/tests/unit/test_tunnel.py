import io
import os
import stat
import tarfile
import time

import pytest

from app import tunnel


class FakeProc:
    def __init__(self, lines):
        self.stdout = iter(lines)
        self.terminated = False

    def terminate(self):
        self.terminated = True


def test_clean_domain():
    assert tunnel.clean_domain(" https://My-Name.ngrok-free.app/x ") == "my-name.ngrok-free.app"
    for bad in ("evil.com", "ngrok-free.app", "a b.ngrok-free.app", "", "x.ngrok-free.app.evil.com"):
        with pytest.raises(ValueError):
            tunnel.clean_domain(bad)


def test_config_is_private_and_token_not_on_cmdline(tmp_path):
    cfg = tunnel.write_ngrok_config(tmp_path, "SECRETTOKEN")
    assert "SECRETTOKEN" in cfg.read_text()
    if os.name != "nt":
        assert stat.S_IMODE(cfg.stat().st_mode) == 0o600
    cmd = tunnel.ngrok_cmd(tmp_path / "ngrok", cfg, "a.ngrok-free.app", 8000)
    assert "SECRETTOKEN" not in " ".join(cmd) and "--url=a.ngrok-free.app" in cmd and "8000" in cmd
    assert tunnel.redact("authtoken SECRETTOKEN bad", "SECRETTOKEN") == "authtoken *** bad"


def test_ensure_ngrok_extracts_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(tunnel, "platform_key", lambda: ("linux", "amd64"))
    monkeypatch.setattr(tunnel, "MIN_NGROK_BYTES", 1)  # the fake agent here is tiny
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        data = b"#!/bin/sh\n"
        ti = tarfile.TarInfo("ngrok")
        ti.size = len(data)
        t.addfile(ti, io.BytesIO(data))
    calls = []
    exe = tunnel.ensure_ngrok(tmp_path, lambda u, sha: calls.append((u, sha)) or buf.getvalue())
    assert exe.read_bytes() == b"#!/bin/sh\n" and tunnel.NGROK_VERSION in calls[0][0]
    assert calls[0][1] == tunnel.NGROK_SHA["linux-amd64.tgz"]
    assert tunnel.ensure_ngrok(tmp_path, lambda u, s: pytest.fail("cached")) == exe


def test_fetch_rejects_bad_checksum(monkeypatch):
    class R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"x"

    monkeypatch.setattr(tunnel.urllib.request, "urlopen", lambda *a, **k: R())
    with pytest.raises(RuntimeError, match="checksum"):
        tunnel._fetch("https://x", "0" * 64)


def test_cloudflared_unix_and_platform(tmp_path, monkeypatch):
    orig = tunnel.platform_key
    monkeypatch.setattr(tunnel, "platform_key", lambda: ("linux", "arm64"))
    exe = tunnel.ensure_cloudflared(tmp_path, lambda u, s: b"bin")
    assert exe.read_bytes() == b"bin"
    monkeypatch.setattr(tunnel.platform, "system", lambda: "Plan9")
    with pytest.raises(RuntimeError):
        orig()
    monkeypatch.setattr(tunnel.platform, "system", lambda: "Linux")
    monkeypatch.setattr(tunnel.platform, "machine", lambda: "x86_64")
    assert orig() == ("linux", "amd64")


def test_explain():
    assert "domain" in tunnel.explain("ERR_NGROK_314", "")
    assert tunnel.explain(None, "plain") == "plain"


@pytest.mark.asyncio
async def test_verify_ngrok_ok_and_errors(tmp_path):
    ok_proc = FakeProc(["lvl=info msg=x", 'msg="started tunnel" url=https://a'])
    r = await tunnel.verify_ngrok(
        tmp_path, "TOK", "a.ngrok-free.app", spawn_fn=lambda c: ok_proc, ensure=lambda t: tmp_path / "ngrok"
    )
    assert r[0] and ok_proc.terminated
    bad = FakeProc(["lvl=eror err=ERR_NGROK_105 TOK"])
    r = await tunnel.verify_ngrok(
        tmp_path, "TOK", "a.ngrok-free.app", spawn_fn=lambda c: bad, ensure=lambda t: tmp_path / "n"
    )
    assert not r[0] and "authtoken" in r[1] and "TOK" not in r[1]
    gen = FakeProc(["lvl=eror boom"])
    r = await tunnel.verify_ngrok(
        tmp_path, "TOK", "a.ngrok-free.app", spawn_fn=lambda c: gen, ensure=lambda t: tmp_path / "n"
    )
    assert not r[0]
    slow = FakeProc(["nothing useful"])
    r = await tunnel.verify_ngrok(
        tmp_path, "T", "a.ngrok-free.app", spawn_fn=lambda c: slow, ensure=lambda t: tmp_path / "n", wait_s=-1
    )
    assert not r[0] and "in time" in r[1]


def test_state_dict():
    assert tunnel.TunnelState("ngrok", "a.ngrok-free.app").as_dict()["permanent"] is True
    assert (
        tunnel.TunnelState("cloudflare", quick_url="https://q.trycloudflare.com")
        .public_url()
        .endswith("trycloudflare.com")
    )
    assert tunnel.TunnelState().public_url() == ""


def _mgr(tmp_path, creds, spawn_fn, notes, **kw):
    return tunnel.TunnelManager(
        tmp_path,
        creds,
        lambda *a: notes.append(a),
        spawn_fn=spawn_fn,
        ensure_ngrok_fn=lambda t: tmp_path / "ngrok",
        ensure_cf_fn=lambda t: tmp_path / "cf",
        **kw,
    )


def _wait(cond, t=5.0):
    end = time.time() + t
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_ngrok_active_and_poke(tmp_path):
    notes = []
    mgr = _mgr(tmp_path, lambda: {"authtoken": "T", "domain": "a.ngrok-free.app"}, None, notes)

    class Blocking(FakeProc):
        def __init__(self):
            self.ev = __import__("threading").Event()
            self.terminated = False
            self.stdout = self._gen()

        def _gen(self):
            yield 'msg="started tunnel"'
            self.ev.wait(5)

        def terminate(self):
            self.terminated = True
            self.ev.set()

    procs = []
    mgr.spawn_fn = lambda cmd: procs.append(Blocking()) or procs[-1]
    mgr.start()
    assert _wait(lambda: mgr.state.mode == "ngrok")
    assert mgr.state.public_url() == "https://a.ngrok-free.app"
    mgr.poke()
    assert _wait(lambda: len(procs) == 2)  # restarted, no failure notice
    mgr.stop()
    assert procs[0].terminated and not notes


def test_fallback_to_cloudflare_with_notice(tmp_path):
    notes = []
    state = {"n": 0}

    def sp(cmd):
        if "tunnel" in cmd:
            return FakeProc(["INF https://abc-def.trycloudflare.com ok"] + [])
        state["n"] += 1
        return FakeProc(["lvl=eror err=ERR_NGROK_105"])

    mgr = _mgr(
        tmp_path, lambda: {"authtoken": "T", "domain": "a.ngrok-free.app"}, sp, notes, retry_ngrok_s=0, stable_s=60
    )
    mgr.start()
    assert _wait(lambda: any("temporary" in n[1] for n in notes))
    assert _wait(lambda: mgr.state.error != "" or mgr.state.mode == "cloudflare")
    mgr.stop()
    assert state["n"] >= 3
    assert sum("temporary" in n[1] for n in notes) == 1  # not re-notified on every retry


def test_not_configured_uses_cloudflare_quietly(tmp_path):
    notes = []
    mgr = _mgr(tmp_path, lambda: None, lambda cmd: FakeProc(["https://zzz.trycloudflare.com"]), notes)
    mgr.start()
    assert _wait(lambda: any("No public" in n[1] for n in notes))  # process ended -> visible error
    mgr.stop()
    assert not any("temporary" in n[1] for n in notes)


def test_exception_is_reported(tmp_path):
    notes = []

    def boom(cmd):
        raise OSError("no exec")

    mgr = _mgr(tmp_path, lambda: {"authtoken": "T", "domain": "a.ngrok-free.app"}, boom, notes)
    mgr.start()
    assert _wait(lambda: any(n[1] == "Tunnel error" for n in notes))
    mgr.stop()
    assert mgr.state.mode == "none" and "OSError" in mgr.state.error


def test_cloudflare_retry_timer_returns_to_ngrok(tmp_path):
    notes = []
    mgr = _mgr(
        tmp_path,
        lambda: {"authtoken": "T", "domain": "a.ngrok-free.app"},
        lambda cmd: FakeProc(["x"]),
        notes,
        retry_ngrok_s=0.05,
    )
    assert mgr.run_cloudflare_until(time.time() - 1, True) == ""


def test_ensure_ngrok_falls_back_to_users_own_ngrok(tmp_path, monkeypatch):
    """D114: download blocked (OSError) → the user's own ngrok is used; none installed → the error is kept."""
    monkeypatch.setattr(tunnel.shutil, "which", lambda n: "/usr/local/bin/ngrok")

    def blocked(url, sha):
        raise OSError("blocked by firewall")

    assert str(tunnel.ensure_ngrok(tmp_path, fetch=blocked)) == "/usr/local/bin/ngrok"
    monkeypatch.setattr(tunnel.shutil, "which", lambda n: None)
    with pytest.raises(OSError, match="blocked"):
        tunnel.ensure_ngrok(tmp_path, fetch=blocked)


def test_spawn_retries_with_users_ngrok_when_downloaded_exe_is_blocked(monkeypatch):
    calls = []

    class P:
        pass

    def popen(cmd, **k):
        calls.append(cmd[0])
        if cmd[0] == "/blocked/ngrok":
            raise PermissionError("access denied")
        return P()

    monkeypatch.setattr(tunnel.subprocess, "Popen", popen)
    monkeypatch.setattr(tunnel.shutil, "which", lambda n: "/mine/ngrok")
    assert isinstance(tunnel.spawn(["/blocked/ngrok", "http", "8000"]), P)
    assert calls == ["/blocked/ngrok", "/mine/ngrok"]
    monkeypatch.setattr(tunnel.shutil, "which", lambda n: None)
    with pytest.raises(PermissionError):
        tunnel.spawn(["/blocked/ngrok", "http", "8000"])


def test_ensure_ngrok_redownloads_a_damaged_cached_exe(tmp_path):
    """D114: a tiny/half-written ngrok.exe (WinError 193) is deleted and fetched again, written atomically."""
    exe = tmp_path / "ngrok" / tunnel.NGROK_VERSION / tunnel._exe_name("ngrok")
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"MZ")  # damaged
    tunnel._write_exe(exe.with_name("other.exe"), b"x" * 10)
    assert not exe.with_name("other.exe.part").exists()
    seen = []

    def fake_fetch(url, sha):
        seen.append(url)
        raise OSError("offline")

    with pytest.raises(OSError, match="offline"):
        tunnel.ensure_ngrok(tmp_path, fetch=fake_fetch)
    assert seen and not exe.exists()


def test_spawn_winerror_193_deletes_exe_and_explains(tmp_path, monkeypatch):
    exe = tmp_path / "ngrok.exe"
    exe.write_bytes(b"MZ")

    def popen(cmd, **k):
        err = OSError("[WinError 193] %1 is not a valid Win32 application")
        err.winerror = 193
        raise err

    monkeypatch.setattr(tunnel.subprocess, "Popen", popen)
    monkeypatch.setattr(tunnel.shutil, "which", lambda n: None)
    with pytest.raises(RuntimeError, match="WinError 193"):
        tunnel.spawn([str(exe), "http", "8000"])
    assert not exe.exists()
