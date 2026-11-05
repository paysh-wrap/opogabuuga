"""POST /api/webhook/tradingview — public (secret-authenticated), answers within 1 s, processes async."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from app import audit
from app.api.deps import Principal, current_user
from app.indicators.bars import tf_minutes
from app.models import Event
from app.monitor.feed import feed_status
from app.settings import REPO_ROOT
from app.webhook.service import Accepted, ingest

router = APIRouter(prefix="/api")
PINE_DIR = REPO_ROOT / "pine"
PINE_FILES = {"bridge": "Paytience_Bridge.pine"}


async def _after_accept(request: Request, acc: Accepted) -> None:
    st = request.app.state
    state = st.market.apply(acc.symbol, acc.payload)
    key = f"{acc.symbol}-{acc.payload.profile}"
    now = time.monotonic()
    if acc.payload.event != "HEARTBEAT" or now - st.ws_throttle.get(key, 0.0) > 15:
        st.ws_throttle[key] = now
        await st.hub.broadcast(
            "connection.updated", {"id": "tradingview", "symbol": acc.symbol, "profile": acc.payload.profile}
        )
    if acc.payload.event != "HEARTBEAT":
        await st.hub.broadcast(
            "signal.updated",
            {
                "symbol": acc.symbol,
                "profile": acc.payload.profile,
                "event": acc.payload.event,
                "direction": acc.payload.direction,
                "models": len(state.models),
            },
        )


@router.post("/webhook/tradingview")
async def tradingview(request: Request, background: BackgroundTasks) -> JSONResponse:
    st = request.app.state
    ip = request.client.host if request.client else "?"
    if not st.webhook_limiter.allow(ip, time.monotonic()):
        return JSONResponse({"ok": False, "code": "RATE_LIMIT"}, status_code=429)
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > st.rules.rules.webhook.max_body_bytes:
        return JSONResponse({"ok": False, "code": "TOO_LARGE"}, status_code=413)
    body = await request.body()

    def work() -> Any:
        with st.sessionmaker() as s:
            return ingest(
                s,
                body,
                rules=st.rules.rules,
                secret=st.settings.webhook_secret.get_secret_value(),
                clock=st.clock,
                ip=ip,
                stats=st.webhook_stats,
            )

    res = await run_in_threadpool(work)
    if isinstance(res, Accepted):
        if not res.duplicate:
            background.add_task(_after_accept, request, res)
        return JSONResponse({"ok": True, "duplicate": res.duplicate})
    return JSONResponse({"ok": False, "code": res.code, "detail": res.detail}, status_code=res.status)


@router.get("/webhook/status")
def webhook_status(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    st = request.app.state
    feeds = []
    with st.sessionmaker() as s:
        rows = s.execute(
            select(Event.symbol, Event.profile, func.max(Event.bar_time))
            .where(Event.event == "HEARTBEAT")
            .group_by(Event.symbol, Event.profile)
        ).all()
    now = st.clock.now()
    for sym, prof, last in rows:
        ltf = st.rules.rules.profiles.TIGHT.ltf if prof == "TIGHT" else st.rules.rules.profiles.STD.ltf
        last_ms = int(last.timestamp() * 1000) if last else None
        feeds.append(
            {
                "symbol": sym,
                "profile": prof,
                "last_heartbeat": last.isoformat() if last else None,
                "status": feed_status(last_ms, tf_minutes(ltf), now, st.rules.rules.webhook.stale_after_bar_multiple),
            }
        )
    stats = st.webhook_stats
    return {
        "path": "/api/webhook/tradingview",
        "secret_set": bool(st.settings.webhook_secret.get_secret_value()),
        "feeds": feeds,
        "accepted": dict(stats.accepted),
        "rejected": dict(stats.rejected),
        "last_rejection": stats.last_rejection,
    }


@router.post("/webhook/secret/reveal")
def reveal_secret(request: Request, p: Principal = Depends(current_user)) -> dict[str, str]:
    st = request.app.state
    secret = st.settings.webhook_secret.get_secret_value()
    if not secret:
        raise HTTPException(503, "PAYTIENCE_WEBHOOK_SECRET not set — run `make keys`")
    with st.sessionmaker() as s:
        audit.record(s, st.clock, p.user.username, "webhook.secret_revealed")
        s.commit()
    return {"secret": secret}


@router.get("/pine/{name}")
def pine_file(name: str, _: Principal = Depends(current_user)) -> PlainTextResponse:
    fname = PINE_FILES.get(name)
    path = PINE_DIR / fname if fname else None
    if path is None or not Path(path).is_file():
        raise HTTPException(404, "unknown script")
    return PlainTextResponse(
        path.read_text(encoding="utf-8"),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
