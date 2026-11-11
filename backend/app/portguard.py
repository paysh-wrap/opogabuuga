"""D97: never serve the wrong (old) Paytience. Before uvicorn binds the port, make sure nothing stale holds it.

Order: port free -> go. Port held by something that answers /api/health as "paytience" -> ask it to exit (local-only
authenticated endpoint), then, if it ignores that, terminate exactly that verified PID. Port held by anything else, or
not freed within the budget -> PortBusy with a clear message; the caller exits non-zero. Windows-safe: netstat/tasklist/
taskkill only (no psutil). Every side effect is injectable so the logic is unit-tested without touching real ports.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

SIGNATURE = "paytience"


class PortBusy(Exception):
    """The port could not be freed: the message is shown to the user verbatim."""


def _no_window() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def port_is_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name != "nt":  # POSIX: ignore TIME_WAIT; Windows: exclusive bind (SO_REUSEADDR there allows hijacking)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))  # noqa: S104 - same address the server binds
        return True
    except OSError:
        return False
    finally:
        s.close()


def fetch_health(port: int, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def is_paytience(health: dict[str, Any] | None) -> bool:
    return bool(health) and str((health or {}).get("app", "")).lower() == SIGNATURE


def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, creationflags=_no_window())  # noqa: S603
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_netstat(text: str, port: int) -> int | None:
    """PID of the LISTENING socket on `port` from `netstat -ano` output."""
    pat = re.compile(rf"^\s*TCP\s+\S+:{port}\s+\S+\s+LISTENING\s+(\d+)\s*$", re.IGNORECASE)
    for line in text.splitlines():
        m = pat.match(line)
        if m:
            return int(m.group(1))
    return None


def listener_pid(port: int) -> int | None:
    if os.name == "nt":
        return parse_netstat(_run(["netstat", "-ano", "-p", "TCP"]), port)
    out = _run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fp"])
    m = re.search(r"^p(\d+)$", out, re.MULTILINE)
    return int(m.group(1)) if m else None


def parse_tasklist(text: str) -> str | None:
    """Image name from `tasklist /FO CSV /NH` output."""
    m = re.match(r'\s*"([^"]+)"', text)
    return m.group(1) if m else None


def process_name(pid: int) -> str | None:
    if os.name == "nt":
        return parse_tasklist(_run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"]))
    out = _run(["ps", "-p", str(pid), "-o", "comm="]).strip()
    return Path(out).name if out else None


def kill_pid(pid: int) -> None:
    if os.name == "nt":
        _run(["taskkill", "/PID", str(pid), "/T", "/F"])
    else:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGTERM)


def request_shutdown(port: int, token: str) -> bool:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/system/shutdown", method="POST", headers={"X-Paytience-Shutdown": token}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310
            return bool(r.status == 200)
    except Exception:
        return False


def _holder(port: int, pid: int | None, name_of: Callable[[int], str | None]) -> str:
    if pid is None:
        return f"Port {port} is held by another program"
    return f"Port {port} is held by {name_of(pid) or 'another program'} (PID {pid})"


def ensure_port_free(
    port: int,
    token_file: Path | None = None,
    *,
    graceful_s: float = 8.0,
    budget_s: float = 15.0,
    self_pid: int | None = None,
    say: Callable[[str], None] = print,
    is_free: Callable[[int], bool] = port_is_free,
    health: Callable[[int], dict[str, Any] | None] = fetch_health,
    shutdown: Callable[[int, str], bool] = request_shutdown,
    pid_of: Callable[[int], int | None] = listener_pid,
    name_of: Callable[[int], str | None] = process_name,
    kill: Callable[[int], None] = kill_pid,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Return when `port` is free (after retiring a verified old Paytience) or raise PortBusy."""
    if is_free(port):
        return
    me = self_pid if self_pid is not None else os.getpid()
    h = health(port)
    pid = pid_of(port)
    if not is_paytience(h):
        raise PortBusy(f"{_holder(port, pid, name_of)}; close it and start Paytience again.")
    assert h is not None
    hp = h.get("pid")
    if pid is None and isinstance(hp, int):
        pid = hp
    if pid == me:
        raise PortBusy(f"Port {port} is held by this same Paytience process; close it and start Paytience again.")
    if pid is not None and isinstance(hp, int) and hp != pid:  # the listener is not the one that answered: do not guess
        raise PortBusy(f"{_holder(port, pid, name_of)}; close it and start Paytience again.")
    start = clock()
    old = (h.get("build") or {}).get("commit", "?") if isinstance(h.get("build"), dict) else "?"
    say(f"An older Paytience (build {str(old)[:7]}) is still running on port {port} — closing it…")

    def wait(until: float) -> bool:
        while clock() - start < until:
            if is_free(port):
                return True
            sleep(0.3)
        return is_free(port)

    token = ""
    if token_file is not None:
        with contextlib.suppress(OSError):
            token = token_file.read_text(encoding="utf-8").strip()
    if token and shutdown(port, token) and wait(graceful_s):
        return
    if pid is not None:
        say(f"It did not close by itself — ending Paytience PID {pid}…")
        kill(pid)
        if wait(budget_s):
            return
    raise PortBusy(f"{_holder(port, pid, name_of)} and could not be closed; close it and start Paytience again.")
