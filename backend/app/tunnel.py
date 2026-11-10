"""Permanent webhook URL (D79): runs the ngrok agent with the user's free static domain; falls back to a
cloudflared quick tunnel (temporary URL) with a notification, never silently.

I/O lives here on purpose (it is not a pure module). The authtoken is written only to a 0600 config file in the
tools folder and is never put on a command line or in a log line (every output line is redacted)."""

from __future__ import annotations

import contextlib
import hashlib
import io
import os
import platform
import re
import stat
import subprocess
import tarfile
import threading
import time
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()

NGROK_VERSION = "3.18.4"
CLOUDFLARED_VERSION = "2025.9.1"
NGROK_URL = "https://bin.ngrok.com/c/bNyj1mQVY4c/ngrok-v3-{v}-{plat}"
CF_URL = "https://github.com/cloudflare/cloudflared/releases/download/{v}/cloudflared-{plat}"
# sha256 of the pinned archives (checked after download; mismatch = refuse to run)
NGROK_SHA = {
    "windows-amd64.zip": "438bad3dbefd7e244be9dfae3889dcf99073b515845b66ab5617e4887bc24636",
    "darwin-amd64.zip": "b0ec8786315fd41e4da490aa88cf7868f554ef7ea2873b435ce971d02961c1a9",
    "darwin-arm64.zip": "514967480546b968e87e9ec47efd513ce5012e11000957f9696a05c73b05b908",
    "linux-amd64.tgz": "233e0647849913e6404150c1e9c5e4f31c1368aefee330958d038d7afecb8f2e",
    "linux-arm64.tgz": "fb41ee8f251969f6e399ef03122f791ae537155dfd9ac4c0baf108aca95c17d7",
}
CF_SHA = {
    "linux-amd64": "3dc1dc4252eae3c691861f926e2b8640063a2ce534b07b7a3f4ec2de439ecfe3",
    "linux-arm64": "449baa3eb07f1ed7541f7a6e8a25bf7822ac1fdb60fbb2ebe9c344b2df20951a",
    "windows-amd64.exe": "871c63a23f167ec1a4fc5e2c3de9e91e4f0742af708fb8b86055ddd6da82ea8e",
    "darwin-amd64.tgz": "a678196af2e0f870a9ab95b5696af38f74586c2db642884e14ea29adc424bec5",
    "darwin-arm64.tgz": "106e375d6e0f8ee77eab9ba5abc8aef93962c066bd0bf240ab8a8b21a1b58c9f",
}
DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")
NGROK_HOSTS = (".ngrok-free.app", ".ngrok-free.dev", ".ngrok.app", ".ngrok.dev", ".ngrok.io", ".ngrok.pizza")
QUICK_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
ERR_RE = re.compile(r"ERR_NGROK_\d+")
WEBHOOK_PATH = "/api/webhook/tradingview"


def clean_domain(raw: str) -> str:
    """Accepts 'name.ngrok-free.app' (also pasted with https:// or a path); raises ValueError otherwise."""
    d = raw.strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0]
    if not DOMAIN_RE.match(d) or not d.endswith(NGROK_HOSTS):
        raise ValueError(
            "Static domain must look like your-name.ngrok-free.app (copy it from ngrok Dashboard → Domains)"
        )
    return d


def platform_key() -> tuple[str, str]:
    sysname = {"Windows": "windows", "Darwin": "darwin", "Linux": "linux"}.get(platform.system(), "")
    m = platform.machine().lower()
    arch = "arm64" if m in ("arm64", "aarch64") else "amd64" if m in ("x86_64", "amd64") else ""
    if not sysname or not arch:
        raise RuntimeError(f"Unsupported platform {platform.system()} {platform.machine()}")
    return sysname, arch


def redact(line: str, secret: str) -> str:
    return line.replace(secret, "***")[:300] if secret else line[:300]


def _fetch(url: str, sha: str) -> bytes:
    with urllib.request.urlopen(url, timeout=180) as r:  # noqa: S310 - https, pinned
        data: bytes = r.read()
    if hashlib.sha256(data).hexdigest() != sha:
        raise RuntimeError("Download checksum mismatch — refusing to run it")
    return data


def _exe_name(name: str) -> str:
    return name + (".exe" if os.name == "nt" else "")


def ensure_ngrok(tools: Path, fetch: Callable[[str, str], bytes] = _fetch) -> Path:
    exe = tools / "ngrok" / NGROK_VERSION / _exe_name("ngrok")
    if exe.exists():
        return exe
    sysname, arch = platform_key()
    ext = "zip" if sysname in ("windows", "darwin") else "tgz"
    key = f"{sysname}-{arch}.{ext}"
    data = fetch(NGROK_URL.format(v=NGROK_VERSION, plat=key), NGROK_SHA[key])
    exe.parent.mkdir(parents=True, exist_ok=True)
    if ext == "zip":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            exe.write_bytes(z.read(_exe_name("ngrok")))
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
            f = t.extractfile("ngrok")
            if f is None:
                raise RuntimeError("ngrok archive is missing the ngrok binary")
            exe.write_bytes(f.read())
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return exe


def ensure_cloudflared(tools: Path, fetch: Callable[[str, str], bytes] = _fetch) -> Path:
    exe = tools / "cloudflared" / CLOUDFLARED_VERSION / _exe_name("cloudflared")
    if exe.exists():
        return exe
    sysname, arch = platform_key()
    key = f"{sysname}-{arch}" + (".exe" if sysname == "windows" else ".tgz" if sysname == "darwin" else "")
    data = fetch(CF_URL.format(v=CLOUDFLARED_VERSION, plat=key), CF_SHA[key])
    exe.parent.mkdir(parents=True, exist_ok=True)
    if key.endswith(".tgz"):
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
            f = t.extractfile("cloudflared")
            if f is None:
                raise RuntimeError("cloudflared archive is missing the binary")
            data = f.read()
    exe.write_bytes(data)
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return exe


def write_ngrok_config(tools: Path, token: str) -> Path:
    """Config file with the authtoken, readable by the current user only (never on the command line)."""
    cfg = tools / "ngrok" / "ngrok.yml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(cfg, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f'version: "3"\nagent:\n  authtoken: "{token}"\n  console_ui: false\n')
    with contextlib.suppress(OSError):
        cfg.chmod(0o600)
    return cfg


def ngrok_cmd(exe: Path, cfg: Path, domain: str, port: int) -> list[str]:
    return [str(exe), "http", f"--url={domain}", str(port), "--config", str(cfg), "--log=stdout", "--log-format=logfmt"]


def spawn(cmd: list[str]) -> subprocess.Popen[str]:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0  # type: ignore[attr-defined,unused-ignore]
    return subprocess.Popen(  # noqa: S603
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=flags, bufsize=1
    )


def explain(err_code: str | None, line: str) -> str:
    return {
        "ERR_NGROK_105": "authtoken rejected by ngrok (copy it again from Dashboard → Your Authtoken)",
        "ERR_NGROK_107": "authtoken rejected by ngrok (copy it again from Dashboard → Your Authtoken)",
        "ERR_NGROK_314": "that domain is not on your ngrok account (Dashboard → Domains)",
        "ERR_NGROK_334": "that domain is already online somewhere else (close the other ngrok)",
    }.get(err_code or "", f"ngrok reported {err_code}" if err_code else line[:160])


async def verify_ngrok(
    tools: Path,
    token: str,
    domain: str,
    port: int = 8000,
    spawn_fn: Callable[[list[str]], Any] = spawn,
    ensure: Callable[[Path], Path] = ensure_ngrok,
    wait_s: float = 20.0,
) -> tuple[bool, str]:
    """One-off start of the agent to prove token + domain work; stops it right away. No secret is returned."""
    import asyncio

    def run() -> tuple[bool, str]:
        exe = ensure(tools)
        cfg = write_ngrok_config(tools, token)
        proc = spawn_fn(ngrok_cmd(exe, cfg, domain, port))
        t0 = time.time()
        try:
            for raw in proc.stdout:
                line = redact(raw.strip(), token)
                if "started tunnel" in line:
                    return True, f"Token accepted · {domain} is yours and can be served"
                m = ERR_RE.search(line)
                if m or "lvl=eror" in line:
                    return False, explain(m.group(0) if m else None, line)
                if time.time() - t0 > wait_s:
                    break
            return False, "ngrok did not start a tunnel in time"
        finally:
            with contextlib.suppress(Exception):
                proc.terminate()

    return await asyncio.to_thread(run)


@dataclass
class TunnelState:
    mode: str = "none"  # ngrok | cloudflare | none
    domain: str = ""
    quick_url: str = ""
    error: str = ""

    def public_url(self) -> str:
        if self.mode == "ngrok" and self.domain:
            return f"https://{self.domain}"
        return self.quick_url if self.mode == "cloudflare" else ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "ngrok_domain": self.domain if self.mode == "ngrok" else "",
            "public_url": self.public_url(),
            "permanent": self.mode == "ngrok",
            "error": self.error,
        }


ACTIVE: TunnelManager | None = None  # set by the app lifespan (desktop); the Connections tester reuses it


class TunnelManager:
    """Keeps exactly one tunnel alive. ngrok when configured; cloudflared quick tunnel as the visible fallback."""

    def __init__(
        self,
        tools: Path,
        creds: Callable[[], dict[str, str] | None],
        notify: Callable[[str, str, str], None],
        port: int = 8000,
        spawn_fn: Callable[[list[str]], Any] = spawn,
        ensure_ngrok_fn: Callable[[Path], Path] = ensure_ngrok,
        ensure_cf_fn: Callable[[Path], Path] = ensure_cloudflared,
        retry_ngrok_s: float = 300.0,
        stable_s: float = 8.0,
    ) -> None:
        self.tools, self.creds, self.notify, self.port = tools, creds, notify, port
        self.spawn_fn, self.ensure_ngrok_fn, self.ensure_cf_fn = spawn_fn, ensure_ngrok_fn, ensure_cf_fn
        self.retry_ngrok_s, self.stable_s = retry_ngrok_s, stable_s
        self.state = TunnelState()
        self._stop = threading.Event()
        self._proc: Any = None
        self._thread: threading.Thread | None = None
        self._seen: dict[str, str] = {}
        self._poked = False
        self._lock = threading.Lock()

    # ---- lifecycle ----
    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="tunnel", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._kill()

    def poke(self) -> None:
        """Credentials changed: restart whatever is running so the new ones are used now."""
        self._poked = True
        self._kill()

    def _kill(self) -> None:
        with self._lock:
            p, self._proc = self._proc, None
        if p is not None:
            with contextlib.suppress(Exception):
                p.terminate()

    def _alert(self, level: str, title: str, body: str) -> None:
        if self._seen.get(title) != body:  # one notification per distinct problem, not one per retry
            self._seen[title] = body
            self.notify(level, title, body)

    # ---- one run of a tunnel process; returns why it ended ----
    def _watch(self, cmd: list[str], secret: str, on_line: Callable[[str], None]) -> str:
        proc = self.spawn_fn(cmd)
        with self._lock:
            self._proc = proc
        reason = ""
        for raw in proc.stdout:
            line = redact(raw.strip(), secret)
            on_line(line)
            m = ERR_RE.search(line)
            if m:
                reason = explain(m.group(0), line)
            if self._stop.is_set():
                break
        return reason or "the tunnel program stopped"

    def run_ngrok(self, c: dict[str, str]) -> str:
        """Blocks while ngrok lives. Returns the reason it ended."""
        domain, token = clean_domain(c["domain"]), c["authtoken"]
        exe = self.ensure_ngrok_fn(self.tools)
        cfg = write_ngrok_config(self.tools, token)

        def on_line(line: str) -> None:
            if "started tunnel" in line:
                self.state = TunnelState("ngrok", domain)
                self._seen.clear()
                log.info("tunnel.ngrok_active", domain=domain)

        return self._watch(ngrok_cmd(exe, cfg, domain, self.port), token, on_line)

    def run_cloudflare(self) -> str:
        exe = self.ensure_cf_fn(self.tools)

        def on_line(line: str) -> None:
            m = QUICK_RE.search(line)
            if m and self.state.mode != "cloudflare":
                self.state = TunnelState("cloudflare", quick_url=m.group(0), error=self.state.error)
                log.info("tunnel.cloudflare_active")

        return self._watch(
            [str(exe), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{self.port}"], "", on_line
        )

    def _loop(self) -> None:
        fails = 0
        while not self._stop.is_set():
            try:
                c = self.creds()
                if c and c.get("authtoken") and c.get("domain") and fails < 3:
                    t0 = time.time()
                    why = self.run_ngrok(c)
                    fails = 0 if time.time() - t0 > self.stable_s else fails + 1
                    if self._stop.is_set():
                        return
                    if self._poked:
                        self._poked, fails = False, 0
                        continue
                    self.state = TunnelState("none", error=f"ngrok stopped: {why}")
                    self.state.error = f"ngrok stopped: {why}"
                    continue
                prior = self.state.error
                reason = "ngrok is not set up" if not (c and c.get("authtoken")) else f"ngrok keeps failing ({prior})"
                if c:
                    self._alert("warn", "Using a temporary Cloudflare link", reason)
                self.state.error = reason if c else ""
                started = time.time()
                why = self.run_cloudflare_until(started, bool(c))
                if self._stop.is_set():
                    return
                if self._poked:
                    self._poked, fails = False, 0
                    continue
                if why:
                    self.state = TunnelState("none", error=f"tunnel stopped: {why}")
                    self._alert("error", "No public webhook URL", f"{why}. TradingView alerts cannot reach Paytience.")
                    self._stop.wait(10)
                fails = 0  # retry ngrok
            except Exception as e:
                self.state = TunnelState("none", error=f"{type(e).__name__}: {e}"[:200])
                self._alert("error", "Tunnel error", self.state.error)
                fails = min(fails + 1, 3)
                self._stop.wait(30)

    def run_cloudflare_until(self, started: float, ngrok_configured: bool) -> str:
        """Quick tunnel; if ngrok is configured, drop it after retry_ngrok_s so ngrok is tried again."""
        if ngrok_configured and self.retry_ngrok_s > 0:
            timer = threading.Timer(self.retry_ngrok_s, self._kill)
            timer.daemon = True
            timer.start()
            try:
                why = self.run_cloudflare()
            finally:
                timer.cancel()
            return "" if time.time() - started >= self.retry_ngrok_s else why
        return self.run_cloudflare()
