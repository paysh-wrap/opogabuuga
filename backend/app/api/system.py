"""D97: local-only graceful shutdown, used by a NEW Paytience start to retire an OLD one that still holds port 8000.

Triple guard: request must come straight from this computer (loopback, no proxy/tunnel header), must carry the
per-process secret that only the desktop launcher knows (stored in paytience-data/run/), and the endpoint does not
exist unless the launcher registered a shutdown hook. It is never reachable remotely or through a tunnel.
"""

from __future__ import annotations

import contextlib
import hmac
import os

import structlog
from fastapi import APIRouter, Header, HTTPException, Request

from app.buildinfo import SHUTDOWN_TOKEN_ENV, is_local_request

router = APIRouter(prefix="/api/system")
log = structlog.get_logger()


@router.post("/shutdown")
def shutdown(request: Request, x_paytience_shutdown: str = Header(default="")) -> dict[str, bool]:
    expected = os.environ.get(SHUTDOWN_TOKEN_ENV, "")
    hook = getattr(request.app.state, "request_shutdown", None)
    if not is_local_request(request) or not expected or not hmac.compare_digest(x_paytience_shutdown, expected):
        raise HTTPException(403, "Forbidden")
    if hook is None:
        raise HTTPException(409, "Shutdown is only available in the desktop app")
    log.warning("system.shutdown_requested", reason="a newer Paytience start needs port 8000")
    with contextlib.suppress(Exception):  # never block the shutdown on a notification problem
        request.app.state.controller.notify(
            "warning", "Paytience is closing", "A newer start asked this server to exit.", "system"
        )
    hook()
    return {"ok": True}
