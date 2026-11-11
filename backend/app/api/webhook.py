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
from app.signals.service import SignalUpdate
from app.webhook.service import Accepted, Ignored, ingest

router = APIRouter(prefix="/api")
log = structlog.get_logger()
PINE_DIR = REPO_ROOT / "pine"
PINE_FILES = {"bridge": "Paytience_Bridge.pine"}


async def _run_sync(st: Any, fn: Any) -> Any:
    """DB work off the event loop (live). Backtests set app.state.inline_db_work: one event loop and no other
    requests, so the thread hop is pure overhead there — same code, same order of operations."""
    if getattr(st, "inline_db_work", False):
        return fn()
    return await run_in_threadpool(fn)


def _mark_processed(st: Any, event_id: str) -> None:
    from sqlalchemy import update

    with st.sessionmaker() as s:
        s.execute(update(Event).where(Event.event_id == event_id).values(processed_at=st.clock.now()))
        s.commit()


async def _after_accept(request: Request, acc: Accepted) -> None:
    await after_accept(request.app, acc)


async def after_accept(app: Any, acc: Accepted, replay: bool = False) -> None:
    """Process one stored event. replay=True (watchdog / startup replay of a heartbeat that was accepted but never
    processed): market state is left alone and strategies may only EXIT - a late bar never opens a
    position - but fills / stops / strategy exits on that bar still run."""
    st = app.state
    p = acc.payload
    st.inflight_events.add(p.id)
    try:
        await _process(app, acc, replay)
    finally:
        st.inflight_events.discard(p.id)


async def _process(app: Any, acc: Accepted, replay: bool) -> None:
    st = app.state
    p = acc.payload
    key = f"{acc.symbol}-{p.profile}"
    lock = st.signal_locks.setdefault(key, asyncio.Lock())
    async with lock:  # one evaluation at a time per symbol+profile (webhooks for one bar arrive concurrently)
        if not replay:
            st.market.apply(acc.symbol, p)

        def strategies() -> Any:  # D55: NOISE / OPEN_DRIVE from the stored 1-minute TradingView bars
            from datetime import UTC, datetime

            from app.signals import strategy_service

            with st.sessionmaker() as s:
                return strategy_service.run(
                    s,
                    rules=st.rules.rules,
                    clock=st.clock,
                    calendar=st.calendar,
                    symbol=acc.symbol,
                    tf=p.tf,
                    at=datetime.fromtimestamp(p.bar_time_ms / 1000, tz=UTC),
                    exits_only=replay,
                )

        def order_flow() -> Any:  # D95: ORDER_FLOW alert → paper-only strategy signal
            from app.signals import strategy_service

            with st.sessionmaker() as s:
                return strategy_service.run_order_flow(
                    s, rules=st.rules.rules, clock=st.clock, calendar=st.calendar, symbol=acc.symbol, payload=p
                )

        exits: list[tuple[int, str]] = []
        try:
            updates: list[SignalUpdate] = []
            if p.event == "ORDER_FLOW":
                updates = [] if replay else (await _run_sync(st, order_flow)).updates
            if p.event == "HEARTBEAT" and p.price is not None:
                strat = await _run_sync(st, strategies)
                updates = [*updates, *strat.updates]
                exits = strat.exits
        except Exception as e:  # §1.9: never silent — log + banner; entries stay blocked because nothing passed
            log.error("signal.process_failed", key=key, error=type(e).__name__, detail=str(e)[:300])
            await st.hub.broadcast(
                "risk.alert",
                {"level": "error", "title": "Signal processing failed", "detail": f"{key}: {type(e).__name__}"},
            )
            st.controller.notify("error", "Signal processing failed", f"{key}: {type(e).__name__}", "risk")
            updates = []
            failed = True
        else:
            failed = False
    if not failed:  # a crash between here and the exits is covered by the persisted exit markers (exit_watchdog)
        await _run_sync(st, lambda: _mark_processed(st, p.id))
    now = time.monotonic()
    if p.event != "HEARTBEAT" or now - st.ws_throttle.get(key, 0.0) > 15:
        st.ws_throttle[key] = now
        await st.hub.broadcast("connection.updated", {"id": "tradingview", "symbol": acc.symbol, "profile": p.profile})
    ctl = st.controller
    for sid, why in exits:  # D55 strategy exits (trailing / 16:00 flat / time stop) before any new entry
        try:
            n = await ctl.strategy_exit(sid, why)
        except Exception as e:  # never silent; the exit marker stays on the signal and the watchdog retries it
            log.error("strategy.exit_failed", signal=sid, error=type(e).__name__)
            ctl.notify("error", "Strategy exit failed - retrying", f"signal {sid}: {type(e).__name__}", "exit")
            continue
        await st.hub.broadcast("order.updated", {"signal": sid, "exit": why, "trades": n})
    if p.event == "HEARTBEAT" and p.price is not None:
        finest = ctl.bar_feed_ok(acc.symbol, p.tf, st.clock.now())  # D37: no pre-entry ranges from slower bars
        if finest:
            await ctl.on_bar(acc.symbol, p.price.o, p.price.h, p.price.l, p.price.c, st.clock.now())
        if replay:
            return
        await ctl.flat_time_check()
        from app.clock import session_date

        await ctl.news_check(st.calendar(session_date(st.clock.now())))
        await ctl.feed_guard()
        ss = st.market.states.get((acc.symbol, p.profile))
        if ss is not None and finest:
            by_profile = {
                prof: (x.mso, x.mso_events)
                for prof in ("TIGHT", "STD")
                if (x := st.market.states.get((acc.symbol, prof))) is not None
            }
            await ctl.defence_check(acc.symbol, p.price.h, p.price.l, ss.mso, ss.mso_events, by_profile)
    for u in updates:
        if u.status == "PASS":
            what = ctl.on_signal_pass(u.signal_id)
            if what in ("APPROVAL", "EXECUTE_AND_APPROVAL"):  # FULL + SEMI-override accounts → approval for those
                await st.hub.broadcast("approval.created", {"signal": u.signal_id})
            if what in ("EXECUTE", "EXECUTE_AND_APPROVAL") and not ctl.entries_blocked_by_time():
                res = await ctl.execute(u.signal_id, "automation")
                await st.hub.broadcast("order.updated", {"signal": u.signal_id, "results": len(res)})

        await st.hub.broadcast(
            "signal.updated",
            {"id": u.signal_id, "model_key": u.model_key, "status": u.status, "reason": u.reason, "score": u.score},
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

    res = await _run_sync(st, work)
    if isinstance(res, Ignored):  # D105: LunqFX alerts are acknowledged and dropped - no signal, no banner
        return JSONResponse({"ok": True, "ignored": True, "code": res.code, "detail": res.detail})
    if isinstance(res, Accepted):
        if not res.duplicate:
            background.add_task(after_accept, request.app, res)
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


@router.post("/webhook/test-alert")
async def test_alert(request: Request, p: Principal = Depends(current_user)) -> dict[str, Any]:
    """Dry run of a pasted TradingView alert message: parse + secret check only. Nothing is stored, no signal or
    heartbeat is recorded (a fake heartbeat would make a dead feed look fresh)."""
    from app.webhook.parser_bridge import parse
    from app.webhook.security import secret_ok

    st = request.app.state
    payload, rej = parse(await request.body(), st.rules.rules)
    if rej is not None or payload is None:
        return {"ok": False, "code": rej.code if rej else "BAD_JSON", "detail": rej.detail if rej else ""}
    if not secret_ok(st.settings.webhook_secret.get_secret_value(), payload.secret.get_secret_value()):
        return {"ok": False, "code": "BAD_SECRET", "detail": "secret does not match PAYTIENCE_WEBHOOK_SECRET"}
    return {
        "ok": True,
        "code": "OK",
        "detail": f"{payload.event} {payload.direction} {payload.symbol} {payload.profile} {payload.tf}",
    }


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
