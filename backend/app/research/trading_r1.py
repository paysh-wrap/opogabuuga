"""Trading-R1 (TauricResearch/Trading-R1, Apache-2.0) — INFORMATION-ONLY research card (D94).

Isolation (docs/results/session17/trading_r1/FINDINGS.md):
- Lives in its own virtualenv `<tr1_root>/.venv-tr1` (`make tradingr1`); never imported into the API process.
- Headless path: `trading-r1 serve` on 127.0.0.1 + POST /research (stream false) → JSON trajectory.
- TR1_HOME = `<tr1_root>/data/tr1` (all its state); the Anthropic key goes in by environment ONLY (never its
  credential store). The child environment is built from scratch (no inherited secrets such as TAURIC_API_KEY), so
  sync / daemon / channels are never configured or started.
- The answer is shown as advisory text. It never triggers, gates, sizes, scores or biases a trade.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import signal
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

PIN = "0.1.1"  # trading-r1 on PyPI
TIMEOUT_S = 900
START_TIMEOUT_S = 60
MAX_QUESTION = 1000
MAX_TEXT = 8000
LABEL = "Information only — never triggers or gates a trade"
# only these variables are copied into the child (no secrets, no proxies' credentials beyond what the OS needs)
_PASS_ENV = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "LANG", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE")


@dataclass(frozen=True)
class Result:
    ok: bool
    text: str
    termination: str
    error: str
    rounds: int


def executable(root: Path) -> Path:
    return root / ".venv-tr1" / ("Scripts/trading-r1.exe" if os.name == "nt" else "bin/trading-r1")


def home(root: Path) -> Path:
    return root / "data" / "tr1"


def status(root: Path, api_key: str | None) -> tuple[bool, str]:
    """(configured, message). Missing venv or key → not configured (nothing runs, nothing is invented)."""
    if not executable(root).exists():
        return False, "not configured — Trading-R1 is not installed (run `make tradingr1`)"
    if not api_key:
        return False, "not configured — save a Claude (Anthropic) key for Trading-R1 on the API Keys page"
    return True, "ready"


def child_env(api_key: str, tr1_home: Path, port: int, token: str) -> dict[str, str]:
    """Environment for `trading-r1 serve`, built from scratch: key by env only, loopback port, own TR1_HOME."""
    base = {k: os.environ[k] for k in _PASS_ENV if k in os.environ}
    return {
        **base,
        "HOME": str(tr1_home),
        "USERPROFILE": str(tr1_home),
        "TR1_HOME": str(tr1_home),
        "TR1_PORT": str(port),
        "TR1_API_TOKEN": token,
        "ANTHROPIC_API_KEY": api_key,
        "PYTHONIOENCODING": "utf-8",
    }


def body(question: str) -> dict[str, Any]:
    q = " ".join(question.split())
    if not q:
        raise ValueError("question is empty")
    if len(q) > MAX_QUESTION:
        raise ValueError(f"question longer than {MAX_QUESTION} characters")
    return {"question": q, "mode": "research", "profile": "anthropic", "stream": False}


def parse(data: Any) -> Result:
    """POST /research JSON → Result. Anything malformed → a failed Result (never raises, never invents text)."""
    if not isinstance(data, dict):
        return Result(False, "", "", "malformed response", 0)
    err = str(data.get("error") or "")[:300]
    text = str(data.get("text") or "")[:MAX_TEXT]
    try:
        rounds = int(data.get("rounds") or 0)
    except (TypeError, ValueError):
        rounds = 0
    term = str(data.get("termination") or "")[:60]
    ok = not err and bool(text.strip())
    if not ok and not err:
        err = "empty answer"
    return Result(ok, text, term, err, rounds)


class Runner(Protocol):
    async def research(self, question: str) -> Result: ...


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ServeRunner:
    """Starts `trading-r1 serve` on loopback for one question, POSTs /research, then kills the process group."""

    def __init__(self, root: Path, api_key: str, timeout_s: int = TIMEOUT_S) -> None:
        self.root, self.api_key, self.timeout_s = root, api_key, timeout_s

    async def research(self, question: str) -> Result:  # pragma: no cover - needs the real 400 MB venv + a key
        exe = executable(self.root)
        if not exe.exists():
            return Result(False, "", "", "not installed", 0)
        payload = body(question)
        h = home(self.root)
        h.mkdir(parents=True, exist_ok=True)
        port, token = _free_port(), secrets.token_urlsafe(24)
        try:
            p = await asyncio.create_subprocess_exec(
                str(exe),
                "serve",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=child_env(self.api_key, h, port, token),
                start_new_session=os.name != "nt",
            )
        except OSError as e:
            return Result(False, "", "", f"start failed: {type(e).__name__}", 0)
        url = f"http://127.0.0.1:{port}/research"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s, trust_env=False) as c:
                for _ in range(START_TIMEOUT_S * 2):
                    try:
                        _, w = await asyncio.open_connection("127.0.0.1", port)
                        w.close()
                        break
                    except OSError:
                        if p.returncode is not None:
                            return Result(False, "", "", f"serve exited {p.returncode}", 0)
                        await asyncio.sleep(0.5)
                else:
                    return Result(False, "", "", "serve did not start", 0)
                r = await c.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
                if r.status_code != 200:
                    return Result(False, "", "", f"HTTP {r.status_code}", 0)
                return parse(r.json())
        except (httpx.HTTPError, ValueError) as e:
            return Result(False, "", "", f"request failed: {type(e).__name__}", 0)
        finally:
            try:
                if os.name != "nt":
                    os.killpg(p.pid, signal.SIGKILL)
                else:
                    p.kill()
            except ProcessLookupError:
                pass
