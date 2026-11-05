"""FastAPI app factory."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from decimal import Decimal

import structlog
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.automation import router as automation_router
from app.api.risk import router as risk_router
from app.api.routes import http_client, router
from app.api.signals import router as signals_router
from app.api.webhook import router as webhook_router
from app.auth import SESSION_COOKIE, RateLimiter, resolve_session
from app.automation.controller import Controller
from app.bias.tradingagents_adapter import TradingAgentsAdapter
from app.clock import Clock, SystemClock
from app.config import load_rules
from app.db import Base, make_engine, make_sessionmaker
from app.engine.market_state import MarketStateStore
from app.execution.adapters.sim import SimAdapter, SimInstrument
from app.execution.order_manager import OrderManager
from app.risk.holder import RulesHolder
from app.settings import Settings, get_settings
from app.signals.service import no_calendar
from app.signals.stats import StatsCache
from app.webhook.service import SlidingWindow, WebhookStats
from app.ws import Hub

log = structlog.get_logger()

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; connect-src 'self' ws: wss:; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'",
}


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    settings = settings or get_settings()
    rules = load_rules(settings.rules_path)
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.database_url.startswith("sqlite"):
            settings_db_dir = settings.database_url.removeprefix("sqlite:///")
            if settings_db_dir and settings_db_dir != ":memory:":
                from pathlib import Path

                Path(settings_db_dir).parent.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(engine)  # Alembic owns migrations; this is a no-op on a migrated DB
        from datetime import timedelta

        from sqlalchemy import select

        from app.engine.market_state import rebuild
        from app.models import Event

        with app.state.sessionmaker() as s:
            app.state.rules.refresh(s)
        if app.state.rules.error:
            log.error("rules.invalid", error=app.state.rules.error)
        app.state.controller.load_accounts()
        since = app.state.clock.now() - timedelta(days=2)
        with app.state.sessionmaker() as s:
            rows = [(e.symbol, e.payload) for e in s.execute(select(Event).where(Event.bar_time >= since)).scalars()]
        log.info("market_state.rebuilt", events=rebuild(app.state.market, rows))
        app.state.http = http_client(settings.http_timeout_s)
        log.info("paytience.start", mode="LIVE" if settings.allow_live else "PAPER")
        yield
        await app.state.http.aclose()
        engine.dispose()

    app = FastAPI(title="Paytience", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.clock = clock or SystemClock()
    app.state.rules = RulesHolder(rules)
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.hub = Hub()
    app.state.login_limiter = RateLimiter(5, 60)
    app.state.webhook_limiter = SlidingWindow(rules.rules.webhook.rate_limit_per_min, 60)
    app.state.webhook_stats = WebhookStats()
    app.state.market = MarketStateStore()
    app.state.ws_throttle = {}
    app.state.signal_locks = {}
    app.state.calendar = no_calendar
    app.state.stats_cache = StatsCache()
    sim = SimAdapter(
        app.state.clock,
        {k: SimInstrument(v.tick, v.tick_value, v.fee_rt) for k, v in rules.rules.instruments.items()},
        rules.rules.trade_plan.slippage_ticks,
    )
    app.state.controller = Controller(
        app.state.sessionmaker,
        app.state.clock,
        app.state.rules,
        sim,
        OrderManager(
            sim,
            rules.rules.drawdown_guard.runner_trail_r,
            rules.rules.behavior.min_hold_seconds,
            rules.rules.drawdown_guard.early_exits_until_r,
        ),
    )
    app.state.ta = TradingAgentsAdapter(
        settings.ta_python, rules.rules.bias.pinned_version, timeout_s=rules.rules.bias.timeout_min * 60
    )

    @app.middleware("http")
    async def headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        resp = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            resp.headers.setdefault(k, v)
        return resp

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:  # §1.9: never silent
        log.error("unhandled", path=request.url.path, error=type(exc).__name__)
        return JSONResponse({"detail": "internal error — see logs"}, status_code=500)

    app.include_router(router)
    app.include_router(webhook_router)
    app.include_router(signals_router)
    app.include_router(risk_router)
    app.include_router(automation_router)

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        with app.state.sessionmaker() as s:
            ok = resolve_session(s, ws.cookies.get(SESSION_COOKIE), app.state.clock) is not None
        if not ok:
            await ws.close(code=4401)
            return
        await ws.accept()
        await app.state.hub.add(ws)
        try:
            while True:
                await ws.receive_text()  # pings from client keep the socket alive
        except WebSocketDisconnect:
            pass
        finally:
            await app.state.hub.remove(ws)

    dist = settings.web_dist
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str) -> Response:
            if path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            f = (dist / path).resolve()
            if path and f.is_file() and dist.resolve() in f.parents:
                return FileResponse(f)
            return FileResponse(dist / "index.html")

    return app


def _decimal_guard() -> None:
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")


_decimal_guard()
