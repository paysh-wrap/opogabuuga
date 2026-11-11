"""D97: port guard — never serve the wrong (old) Paytience. All side effects injected; no real ports touched."""

import socket
import subprocess
from pathlib import Path

import pytest

from app import portguard
from app.portguard import PortBusy, ensure_port_free

NETSTAT = """
Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1000
  TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       4321
  TCP    127.0.0.1:8000         127.0.0.1:50000        ESTABLISHED     4321
  TCP    [::]:18000             [::]:0                 LISTENING       77
"""


class World:
    """A fake machine: a port that is free or held; a stale Paytience that may obey shutdown or need killing."""

    def __init__(self, health, pid=4321, name="Paytience.exe", obeys_shutdown=False, dies_on_kill=True, accepts=False):
        self.held = True
        self.health_ans, self.pid, self.name = health, pid, name
        self.obeys, self.dies, self.accepts = obeys_shutdown, dies_on_kill, accepts
        self.t = 0.0
        self.calls: list[str] = []

    def is_free(self, _p):
        return not self.held

    def health(self, _p):
        return self.health_ans

    def pid_of(self, _p):
        return self.pid

    def name_of(self, _p):
        return self.name

    def shutdown(self, _p, token):
        self.calls.append(f"shutdown:{token}")
        if self.obeys:
            self.held = False
        return self.obeys or self.accepts

    def kill(self, pid):
        self.calls.append(f"kill:{pid}")
        if self.dies:
            self.held = False

    def sleep(self, s):
        self.t += s

    def clock(self):
        return self.t

    def run(self, tmp_path, **kw):
        tok = tmp_path / "shutdown.token"
        if kw.pop("token", True):
            tok.write_text("secret\n")
        ensure_port_free(
            8000,
            tok,
            say=lambda m: self.calls.append("say"),
            is_free=self.is_free,
            health=self.health,
            shutdown=self.shutdown,
            pid_of=self.pid_of,
            name_of=self.name_of,
            kill=self.kill,
            sleep=self.sleep,
            clock=self.clock,
            self_pid=999,
            **kw,
        )


OLD = {"app": "paytience", "build": {"commit": "abcdef1234"}, "pid": 4321}
LEGACY = {"app": "paytience", "status": "ok"}  # pre-D97 build: no pid, no build


def test_free_port_is_a_noop(tmp_path):
    w = World(OLD)
    w.held = False
    w.run(tmp_path)
    assert w.calls == []


def test_old_paytience_closes_gracefully_without_kill(tmp_path):
    w = World(OLD, obeys_shutdown=True)
    w.run(tmp_path)
    assert w.calls == ["say", "shutdown:secret"]


def test_old_paytience_ignoring_shutdown_is_killed_by_verified_pid(tmp_path):
    w = World(OLD, accepts=True)  # says OK but never exits
    w.run(tmp_path)
    assert w.calls == ["say", "shutdown:secret", "say", "kill:4321"]
    assert 8.0 <= w.t <= 15.0  # waited the graceful window, then killed


def test_legacy_build_without_shutdown_endpoint_or_token_is_killed(tmp_path):
    w = World(LEGACY)
    w.run(tmp_path, token=False)
    assert w.calls == ["say", "say", "kill:4321"]  # no token file -> no shutdown call


def test_unkillable_old_paytience_reports_clear_message(tmp_path):
    w = World(OLD, dies_on_kill=False, accepts=True)
    with pytest.raises(PortBusy, match=r"Port 8000 is held by Paytience.exe \(PID 4321\) and could not be closed"):
        w.run(tmp_path)
    assert w.t >= 15.0


def test_foreign_process_is_never_touched(tmp_path):
    w = World(None, pid=555, name="nginx.exe")
    with pytest.raises(
        PortBusy, match=r"Port 8000 is held by nginx.exe \(PID 555\); close it and start Paytience again\."
    ):
        w.run(tmp_path)
    assert w.calls == []  # not even a shutdown request: only a verified Paytience is ever retired


def test_other_web_app_answering_json_is_not_paytience(tmp_path):
    w = World({"app": "something-else"}, pid=None)
    with pytest.raises(PortBusy, match="held by another program; close it"):
        w.run(tmp_path)
    assert w.calls == []


def test_never_kills_itself_or_a_different_listener(tmp_path):
    w = World(OLD, pid=999)
    with pytest.raises(PortBusy, match="this same Paytience process"):
        w.run(tmp_path)
    w2 = World({**OLD, "pid": 1}, pid=2)  # the answering process is not the listening one: do not guess
    with pytest.raises(PortBusy, match="close it and start Paytience again"):
        w2.run(tmp_path)
    assert w.calls == [] and w2.calls == []


def test_listener_unknown_but_health_pid_is_used(tmp_path):
    w = World(OLD, pid=None)
    w.run(tmp_path)
    assert "kill:4321" in w.calls


def test_parsers():
    assert portguard.parse_netstat(NETSTAT, 8000) == 4321
    assert portguard.parse_netstat(NETSTAT, 80) is None  # 18000 / 8000 are not 80
    assert portguard.parse_netstat(NETSTAT, 18000) == 77
    assert portguard.parse_tasklist('"Paytience.exe","4321","Console","1","80,000 K"\r\n') == "Paytience.exe"
    assert portguard.parse_tasklist("INFO: No tasks are running which match the specified criteria.") is None


def test_is_paytience():
    assert portguard.is_paytience({"app": "Paytience"})
    assert not portguard.is_paytience({"app": "x"}) and not portguard.is_paytience(None)


def test_real_socket_free_and_busy_and_health():
    s = socket.socket()
    s.bind(("0.0.0.0", 0))
    s.listen()
    port = s.getsockname()[1]
    try:
        assert portguard.port_is_free(port) is False
        assert portguard.fetch_health(port, timeout=0.3) is None  # a raw socket is not Paytience
    finally:
        s.close()
    assert portguard.port_is_free(port) is True


def test_request_shutdown_failure_is_false():
    assert portguard.request_shutdown(1, "t") is False  # nothing listens on port 1


def test_process_helpers_use_the_right_commands(monkeypatch):
    seen = []

    def run(cmd, **kw):
        seen.append(cmd[0])
        return subprocess.CompletedProcess(cmd, 0, stdout="p77\n" if cmd[0] == "lsof" else "python3\n")

    monkeypatch.setattr(portguard.subprocess, "run", run)
    monkeypatch.setattr(portguard.os, "name", "posix")
    assert portguard.listener_pid(8000) == 77
    assert portguard.process_name(77) == "python3"
    monkeypatch.setattr(portguard.os, "name", "nt")
    portguard.listener_pid(8000)
    portguard.process_name(77)
    portguard.kill_pid(77)
    assert seen == ["lsof", "ps", "netstat", "tasklist", "taskkill"]


def test_run_swallows_missing_tools(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(portguard.subprocess, "run", boom)
    assert portguard._run(["nope"]) == ""


def test_kill_pid_posix_signals(monkeypatch):
    sent = []
    monkeypatch.setattr(portguard.os, "name", "posix")
    monkeypatch.setattr(portguard.os, "kill", lambda pid, sig: sent.append((pid, sig)))
    portguard.kill_pid(5)
    assert sent == [(5, portguard.signal.SIGTERM)]


def test_token_file_unreadable_is_tolerated(tmp_path: Path):
    w = World(OLD)
    ensure_port_free(
        8000,
        tmp_path / "absent",
        is_free=w.is_free,
        health=w.health,
        shutdown=w.shutdown,
        pid_of=w.pid_of,
        name_of=w.name_of,
        kill=w.kill,
        sleep=w.sleep,
        clock=w.clock,
        say=lambda m: None,
        self_pid=999,
    )
    assert w.calls == ["kill:4321"]
