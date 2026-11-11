"""D97: what is this server? Build commit, process start time, executable — shown by /api/health and the UI footer.

Unauthenticated and non-sensitive: commit, build time, start time and the executable NAME are public. The PID and the
full executable path are only returned to a genuinely local request (loopback AND no proxy/tunnel header), because a
tunnel (ngrok/cloudflared) also reaches us from 127.0.0.1.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Request

from app import updater

STARTED_AT = datetime.now(UTC)
SHUTDOWN_TOKEN_ENV = "PAYTIENCE_SHUTDOWN_TOKEN"  # noqa: S105 - the env var NAME, not a secret
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_PROXY_HEADERS = ("x-forwarded-for", "forwarded", "x-real-ip", "cf-connecting-ip", "cf-ray", "x-forwarded-host")


def is_local_request(request: Request) -> bool:
    """True only for a direct request from this computer: loopback peer and no reverse-proxy / tunnel header."""
    host = request.client.host if request.client else ""
    return host in _LOOPBACK and not any(h in request.headers for h in _PROXY_HEADERS)


def build_info(request: Request) -> dict[str, Any]:
    v = updater.load_version()
    exe = Path(sys.executable)
    out: dict[str, Any] = {
        "build": v.as_dict(),
        "started_at": STARTED_AT.isoformat(),
        "executable": exe.name,
        "frozen": bool(getattr(sys, "frozen", False)),
    }
    if is_local_request(request):
        out["pid"] = os.getpid()
        out["executable_path"] = str(exe)
    return out
