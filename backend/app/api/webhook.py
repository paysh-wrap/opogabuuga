"""POST /api/webhook/tradingview — public (secret-authenticated), answers within 1 s, processes async."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import structlog
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
from app.signals.service import SignalUpdate, process
from app.webhook.service import Accepted, ingest

router = APIRouter(prefix="/api")
log = structlog.get_logger()
PINE_DIR = REPO_ROOT / "pine"
PINE_FILES = {"bridge": "Paytience_Bridge.pine"}


async def _after_accept(request: Request, acc: Accepted) -> None:
    st = request.app.state
    p = acc.payload
    key = f"{acc.symbol}-{p.profile}"
    lock = st.signal_locks.setdefault(key, asyncio.Lock())
    async with lock:  # one evaluation at a time per symbol+profile (webhooks for one bar arrive concurrently)
        state = st.market.apply(acc.symbol, p)

        def work() -> list[SignalUpdate]:
            with st.sessionmaker() as s:
                return process(
                    s,
                    state,
                    rules=st.rules.rules,
                    clock=st.clock,
                    calendar=st.calendar,
                    event=p.event,
                    event_time_ms=p.bar_time_ms,
                    one_to_one=st.rules.rules.one_to_one_mode.enabled,
                    cache=st.stats_cache,
                )

        try:
            updates = await run_in_threadpool(work)
        except Exception as e:  # §1.9: never silent — log + banner; entries stay blocked because nothing passed
            log.error("signal.process_failed", key=key, error=type(e).__name__, detail=str(e)[:300])
            await st.hub.broadcast(
                "risk.alert",
                {"level": "error", "title": "Signal processing failed", "detail": f"{key}: {type(e).__name__}"},
            )
            updates = []
    now = time.monotonic()
    if p.event != "HEARTBEAT" or now - st.ws_throttle.get(key, 0.0) > 15:
        st.ws_throttle[key] = now
        await st.hub.broadcast("connection.updated", {"id": "tradingview", "symbol": acc.symbol, "profile": p.profile})
    ctl = st.controller
    if p.event == "HEARTBEAT" and p.price is not None:
        await ctl.on_bar(acc.symbol, p.price.o, p.price.h, p.price.l, p.price.c, st.clock.now())
        await ctl.flat_time_check()
    for u in updates:
        if u.status == "PASS":
            what = ctl.on_signal_pass(u.signal_id)
            if what == "APPROVAL":
                await st.hub.broadcast("approval.created", {"signal": u.signal_id})
            elif what == "EXECUTE" and not ctl.entries_blocked_by_time():
                res = await ctl.execute(u.signal_id, "automation")
                await st.hub.broadcast("order.updated", {"signal": u.signal_id, "results": len(res)})

        await st.hub.broadcast(
            "signal.updated",
            {"id": u.signal_id, "model_key": u.model_key, "status": u.status, "reason": u.reason, "score": u.score},
        )
    if p.event == "MODEL_FAILED":
        await st.hub.broadcast("cooldown.changed", {"symbol": acc.symbol, "profile": p.profile})


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
