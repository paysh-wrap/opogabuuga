"""FastAPI app factory."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

import structlog
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.types import Scope

from app.api.ai_ledger import router as ai_ledger_router
from app.api.automation import router as automation_router
from app.api.backtest import router as backtest_router
from app.api.dashboard import router as dashboard_router
from app.api.gate import router as gate_router
from app.api.income import router as income_router
from app.api.insights import router as insights_router
from app.api.journal import router as journal_router
from app.api.lab import router as lab_router
from app.api.live import router as live_router
from app.api.logs import router as logs_router
from app.api.market import router as market_router
from app.api.notifications import router as notifications_router
from app.api.orderflow import router as orderflow_router
from app.api.orders import router as orders_router
from app.api.payouts import router as payouts_router
from app.api.plan import router as plan_router
from app.api.replay import router as replay_router
from app.api.research import router as research_router
from app.api.risk import router as risk_router
from app.api.routes import http_client, router
from app.api.signals import router as signals_router
from app.api.strategy_gates import router as strategy_gates_router
from app.api.system import router as system_router
from app.api.updates import router as updates_router
from app.api.webhook import router as webhook_router
from app.auth import SESSION_COOKIE, RateLimiter, resolve_session
from app.automation.controller import Controller
from app.bias.tradingagents_adapter import TradingAgentsAdapter
from app.clock import Clock, SystemClock
from app.config import load_rules
from app.db import Base, make_engine, make_sessionmaker
from app.engine.market_state import MarketStateStore
from app.events import EventBus
from app.execution.adapters.router import RoutingAdapter
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


async def _nightly(app: FastAPI, s: Session, now: datetime) -> None:
    """Weekdays at schedule.nightly_backtest (17:15 ET): self-review backtest of recent sessions → Lab."""
    from app.automation import state as stt
    from app.backtest.nightly import nightly
    from app.clock import parse_hhmm, session_date, to_et

    st = app.state
    local, sess = to_et(now), session_date(now)
    if local.weekday() >= 5 or local.time() < parse_hhmm(st.rules.rules.schedule.nightly_backtest):
        return
    if local.time() >= parse_hhmm(st.rules.rules.session.reopen):
        return
    if stt.get_setting(s, "job.nightly.session") == sess.isoformat():
        return
    stt.set_setting(s, "job.nightly.session", sess.isoformat(), now)  # mark first: one attempt per session
    s.commit()
    st.bus.job("nightly", "scheduled", "Nightly self-review backtest", "running", 0)
    try:
        await nightly(app, s, now)
        from app.lab.cycle import auto_rollback, shadow_check

        report = {"shadow": await shadow_check(app, s, now), "rollback": auto_rollback(app, s, now)}
    finally:
        st.bus.job("nightly", "scheduled", "Nightly self-review backtest", "done", 100)
    stt.set_setting(s, "lab.last_nightly", {"at": now.isoformat(), **report}, now)
    s.commit()


async def _lab(app: FastAPI, s: Session, now: datetime) -> None:
    """§17: approved Lab changes apply at the 18:00 reset (never mid-session); the challenger search runs weekly."""
    from app.automation import state as stt
    from app.clock import parse_hhmm, session_date, to_et
    from app.lab.cycle import apply_approved, run_cycle
    from app.payouts.service import due, week_key

    st = app.state
    sched = st.rules.rules.schedule
    local, sess = to_et(now), session_date(now)
    if (
        local.time() >= parse_hhmm(sched.reconcile_reset)
        and stt.get_setting(s, "job.lab_apply.session") != sess.isoformat()
    ):
        stt.set_setting(s, "job.lab_apply.session", sess.isoformat(), now)
        s.commit()
        if apply_approved(s, st.rules.base, st.clock):
            st.rules.refresh(s)
    if due(now, sched.lab_cycle, stt.get_setting(s, "job.lab_cycle.week")):  # type: ignore[arg-type]
        stt.set_setting(s, "job.lab_cycle.week", week_key(now), now)  # mark first: one attempt per week
        s.commit()
        st.bus.job("lab-cycle", "lab", "Strategy Lab weekly search", "running", 0)
        try:
            report = await run_cycle(app, s, now)
        finally:
            st.bus.job("lab-cycle", "lab", "Strategy Lab weekly search", "done", 100)
        stt.set_setting(s, "lab.last_cycle", {"at": now.isoformat(), "report": report}, now)
        s.commit()


async def _eod(app: FastAPI, s: Session, now: datetime) -> None:
    """Weekdays at schedule.eod_update (after the 16:44 hard flat): EOD accounts trail their MLL once."""
    from app.automation import state as stt
    from app.clock import parse_hhmm, session_date, to_et

    st = app.state
    local, sess = to_et(now), session_date(now)
    if local.weekday() >= 5 or local.time() < parse_hhmm(st.rules.rules.schedule.eod_update):
        return
    if local.time() >= parse_hhmm(st.rules.rules.session.reopen):
        return  # after the reopen it is already the next session
    if stt.get_setting(s, "job.eod.session") == sess.isoformat():
        return
    await st.controller.eod_all()
    stt.set_setting(s, "job.eod.session", sess.isoformat(), now)
    s.commit()


async def _inactivity(app: FastAPI, s: Session, now: datetime) -> None:
    """Once per session: alert accounts with no trade for behavior.inactivity_alert_days (§10)."""
    from sqlalchemy import select

    from app.automation import state as stt
    from app.clock import session_date
    from app.models import Account
    from app.phases.phase_engine import inactivity_alert

    sess = session_date(now).isoformat()
    if stt.get_setting(s, "job.inactivity.session") == sess:
        return
    stt.set_setting(s, "job.inactivity.session", sess, now)
    s.commit()
    days = app.state.rules.rules.behavior.inactivity_alert_days
    for a in s.execute(select(Account).where(Account.closed_by_firm.is_(False))).scalars():
        if inactivity_alert(a.last_trade_at or a.stage_started_at, now, days):
            app.state.controller.notify(
                "warn", "Inactivity alert", f"{a.label or a.id}: no trade for {days}+ days", "inactivity"
            )


async def _daily_bias(app: FastAPI, s: Session, now: datetime) -> None:
    from app.automation import state as stt
    from app.bias import service as bias
    from app.clock import session_date
    from app.crypto import Vault

    st = app.state
    sess = session_date(now)
    last = stt.get_setting(s, "job.bias.session")
    if not bias.due(now, st.rules.rules.schedule.bias, last, sess):  # type: ignore[arg-type]
        # D78: already ran today, but a proxy failed → retry every 30 min until 09:25 ET (never silent)
        if last != sess.isoformat() or not bias.retry_due(
            now,
            str(stt.get_setting(s, "job.bias.retry") or "") or None,
            bool(bias.missing_proxies(s, st.rules.rules, sess)),
        ):
            return
        stt.set_setting(s, "job.bias.retry", now.isoformat(), now)
    vault = Vault(st.settings.master_key.get_secret_value())
    await bias.run_bias(
        s,
        st.ta,
        vault,
        st.rules.rules,
        st.clock,
        sess,
        st.controller.notify,
        vt_root=st.settings.vt_root,
        context=bias.openbb_context(st),
    )
    stt.set_setting(s, "job.bias.session", sess.isoformat(), now)
    s.commit()


async def _of_ta_advisor(app: FastAPI, s: Session, now: datetime) -> None:
    """D109: Order Flow TradingAgents advisor — the existing bias job for the Order Flow markets, once per session
    at ta_advisor_lead_min before the first Order Flow entry window (ET). Failure = no advice (never blocks)."""
    from app.automation import state as stt
    from app.bias import of_advisor as ofa
    from app.bias import service as bias
    from app.clock import session_date
    from app.crypto import Vault

    st = app.state
    r = st.rules.rules
    sess = session_date(now)
    if not ofa.due(now, r, stt.get_setting(s, "job.of_ta.session"), sess):  # type: ignore[arg-type]
        return
    stt.set_setting(s, "job.of_ta.session", sess.isoformat(), now)
    s.commit()
    try:
        await bias.run_bias(
            s,
            st.ta,
            Vault(st.settings.master_key.get_secret_value()),
            r,
            st.clock,
            sess,
            st.controller.notify,
            vt_root=st.settings.vt_root,
            context=bias.openbb_context(st),
            only=ofa.proxies(r),
        )
    except Exception as e:  # advisory only: a failure means no advice, never a trading block (§1.8: logged + notified)
        s.rollback()
        log.warning("of_ta_advisor.failed", error=type(e).__name__)
        st.controller.notify("warn", "Order Flow AI advisor: no advice today", type(e).__name__)
    ofa.record(s, r, st.clock, sess)


async def _ta_mgc_research(app: FastAPI, s: Session, now: datetime) -> None:
    """D84: the MGC research part of AI Duo. Off unless AI Duo is on with MGC. Reuses the existing TradingAgents /
    Vibe-Trading connections; no key = nothing runs (the Strategy page shows "AI key not connected")."""
    from app.automation import state as stt
    from app.bias import service as bias
    from app.bias import ta_mgc_research as tr
    from app.clock import session_date, to_et
    from app.crypto import Vault

    st = app.state
    r = st.rules.rules
    if not (r.strategy.ai_duo and "MGC" in r.strategy.ai_duo_cfg.markets):
        return
    cfg, sess = r.strategy.ta_mgc_cfg, session_date(now)
    row = tr.latest(s, cfg.proxy, sess)
    done = row is not None and not (tr.payload(row) or {}).get("error")
    last = str(stt.get_setting(s, "job.ta_mgc.try") or "") or None
    if not tr.research_due(to_et(now), cfg.research_at, last, done, r.strategy.ai_duo_cfg.window_for("MGC")[1]):
        return
    if not tr.connected(s):
        return
    stt.set_setting(s, "job.ta_mgc.try", to_et(now).isoformat(), now)
    cal = [f"{e.at.isoformat()} {e.title}" for e in (st.calendar(sess) or [])]
    await tr.run_research(
        s,
        st.ta,
        Vault(st.settings.master_key.get_secret_value()),
        r,
        st.clock,
        sess,
        st.controller.notify,
        vt_root=st.settings.vt_root,
        context={"openbb": bias.openbb_context(st).get("MGC")},
        calendar=cal,
    )


async def _refresh_calendar(app: FastAPI, s: Session, now: datetime) -> None:
    """Fetch the week's USD high-impact events when missing or older than 4 h. Failure → banner; trading stays
    blocked only if the session date isn't covered (no data = no trading, §15)."""
    from datetime import timedelta

    from app.automation import state as stt
    from app.econ_calendar.forexfactory import CalendarError, CalendarStore, fetch

    store = app.state.calendar
    if not isinstance(store, CalendarStore):
        return
    if store.fetched_at is not None and now - store.fetched_at < timedelta(hours=4):
        return
    try:
        store.set(await fetch(app.state.http), now)
    except CalendarError as e:
        store.error = str(e)
        app.state.controller.notify("error", "Economic calendar fetch failed", str(e))
        return
    stt.set_setting(s, "calendar.cache", store.to_json(), now)
    s.commit()


async def _scheduler(app: FastAPI) -> None:
    """In-process jobs (one app process). Each job runs once per period; failures never silent."""
    from app.automation import state as stt
    from app.clock import session_date
    from app.payouts.service import due, session_check, session_due, week_key, weekly_check

    st = app.state
    while True:
        try:
            now = st.clock.now()
            pc = st.rules.rules.payouts
            with st.sessionmaker() as s:
                if pc.frequency == "weekly" and due(now, pc.check_time, stt.get_setting(s, "job.payouts.week")):  # type: ignore[arg-type]
                    await weekly_check(s, st.controller, st.rules.rules, now)
                    stt.set_setting(s, "job.payouts.week", week_key(now), now)
                    s.commit()
                elif pc.frequency == "every_n_sessions" and session_due(  # D65
                    now,
                    pc.session_check_time,
                    stt.get_setting(s, "job.payouts.day"),  # type: ignore[arg-type]
                ):
                    await session_check(s, st.controller, st.rules.rules, now)
                    stt.set_setting(s, "job.payouts.day", session_date(now).isoformat(), now)
                    s.commit()
                await _refresh_calendar(app, s, now)
                await _inactivity(app, s, now)
                await _daily_bias(app, s, now)
                await _of_ta_advisor(app, s, now)
                await _ta_mgc_research(app, s, now)
                await _eod(app, s, now)
                await _nightly(app, s, now)
                await _lab(app, s, now)
        except Exception as e:  # never silent (§1.8)
            log.error("scheduler.error", error=type(e).__name__)
            st.controller.notify("error", "Scheduled job failed", type(e).__name__)
        await asyncio.sleep(30)


async def watchdog_once(app: FastAPI) -> None:
    """One wall-clock safety pass (flat time, hard flat, news, MLL monitor, stuck exits) on the injected clock."""
    from app.clock import session_date

    st = app.state
    try:
        events = st.calendar(session_date(st.clock.now()))
    except Exception as e:  # calendar trouble must not skip the flatten checks
        events = None
        log.error("watchdog.calendar_error", error=type(e).__name__)
        st.controller.notify("error", "Watchdog could not read the news calendar", type(e).__name__)
    await st.controller.watchdog_tick(events)
    from app.signals import recovery

    try:  # lost signals: replay unprocessed heartbeats, flag a missed NOISE check minute (never silent)
        await recovery.reprocess_unprocessed(app)
        recovery.alert_missed_checks(app)
    except Exception as e:
        log.error("watchdog.replay_error", error=type(e).__name__)
        st.controller.notify("error", "Lost-signal check failed", type(e).__name__)


async def _watchdog(app: FastAPI) -> None:
    interval = app.state.settings.watchdog_interval_s
    while True:
        try:
            await watchdog_once(app)
        except Exception as e:  # never silent (§1.8)
            log.error("watchdog.error", error=type(e).__name__)
            app.state.controller.notify("error", "Safety watchdog failed", type(e).__name__)
        await asyncio.sleep(interval)


def _start_live(app: FastAPI) -> list[asyncio.Task[None]]:
    """PAYTIENCE_ALLOW_LIVE=true only: attach CrossTrade for non-paper accounts. Orders still need the full
    Live-Readiness Checklist (re-checked every 30 s; any failure → live orders refused)."""
    import types

    from sqlalchemy import select

    from app.api.live import live_inputs
    from app.crypto import Vault
    from app.execution.adapters.crosstrade import CrossTradeAdapter
    from app.models import Account, ApiCredential
    from app.risk.live_gate import live_allowed

    st = app.state
    with st.sessionmaker() as s:
        cred = s.execute(select(ApiCredential).where(ApiCredential.provider == "crosstrade")).scalar_one_or_none()
        accts = {a.broker_account_id for a in s.execute(select(Account).where(Account.is_sim.is_(False))).scalars()}
    if cred is None:
        log.warning("live.no_crosstrade")
        return []
    token = Vault(st.settings.master_key.get_secret_value()).open(cred.ciphertext).get("token", "")
    tv = {k: v.tv_symbol for k, v in st.rules.rules.instruments.items()}
    from app.clock import session_date
    from app.contracts import order_contract

    def contract_for(sym: str) -> str:
        """Real futures contract for orders (MGCZ6), never the continuous chart symbol (MGC1!)."""
        inst = st.rules.rules.instruments[sym]
        c = order_contract(sym, inst.contract, session_date(st.clock.now()))
        if c is None:
            from app.execution.adapters.base import BrokerError

            raise BrokerError(f"{sym}: no futures contract configured; refusing to send a continuous symbol")
        return c

    ct = CrossTradeAdapter(token, st.http, tv, contract_for=contract_for)
    flag = {"ok": False}
    st.controller.adapter.set_live(ct, accts, lambda: flag["ok"])
    st.controller.adapter.start()

    async def gate_loop() -> None:
        req = types.SimpleNamespace(app=app)
        while True:
            try:
                with st.sessionmaker() as s:
                    flag["ok"] = live_allowed(await live_inputs(req, s))  # type: ignore[arg-type]
            except Exception as e:  # never silent; fail closed
                flag["ok"] = False
                log.error("live.gate_error", error=type(e).__name__)
            await asyncio.sleep(30)

    async def fills_loop() -> None:
        while True:
            try:
                await st.controller.process_live_fills()
            except Exception as e:
                log.error("live.fills_error", error=type(e).__name__)
                st.controller.notify("error", "Live fill processing failed", type(e).__name__)
            await asyncio.sleep(2)

    return [asyncio.create_task(gate_loop()), asyncio.create_task(fills_loop())]


def _start_tunnel(app: FastAPI) -> None:
    """D79: ngrok static domain if saved, else a visible Cloudflare quick-tunnel fallback (desktop app)."""
    from app import tunnel
    from app.connections import service as conn_service
    from app.crypto import Vault

    def creds() -> dict[str, str] | None:
        try:
            vault = Vault(app.state.settings.master_key.get_secret_value())
            with app.state.sessionmaker() as s:
                return conn_service.credentials(s, vault, "ngrok")
        except Exception as e:
            log.error("tunnel.credentials_unreadable", error=type(e).__name__)
            return None

    tunnel.ACTIVE = tunnel.TunnelManager(app.state.settings.tools_dir, creds, app.state.bus.notify)
    tunnel.ACTIVE.start()


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
        app.state.bus.bind(asyncio.get_running_loop())
        app.state.controller.load_accounts()
        since = app.state.clock.now() - timedelta(days=2)
        with app.state.sessionmaker() as s:
            rows = [(e.symbol, e.payload) for e in s.execute(select(Event).where(Event.bar_time >= since)).scalars()]
        log.info("market_state.rebuilt", events=rebuild(app.state.market, rows))
        app.state.http = http_client(settings.http_timeout_s)
        log.info("paytience.start", mode="LIVE" if settings.allow_live else "PAPER")
        bg = _start_live(app) if settings.allow_live else []
        try:  # restart recovery: rebuild order management from the stored open trades + broker positions
            await app.state.controller.recover_open_trades()
        except Exception as e:  # never silent (§1.8)
            log.error("recovery.failed", error=type(e).__name__)
            app.state.controller.notify("error", "Restart recovery failed", type(e).__name__, "restart")
        try:
            from app.signals import recovery

            await recovery.reprocess_unprocessed(app)
        except Exception as e:
            log.error("recovery.replay_failed", error=type(e).__name__)
            app.state.controller.notify("error", "Lost-signal replay failed", type(e).__name__, "replay")
        from app.econ_calendar.forexfactory import CalendarStore

        with app.state.sessionmaker() as s:
            from app.automation.state import get_setting

            cached = get_setting(s, "calendar.cache")
        app.state.calendar = CalendarStore.from_json(cached) if isinstance(cached, dict) else CalendarStore()
        if settings.tunnel_autostart:
            _start_tunnel(app)
        if settings.scheduler_enabled:
            bg.append(asyncio.create_task(_scheduler(app)))
            bg.append(asyncio.create_task(_watchdog(app)))
        yield
        for t in bg:
            t.cancel()
        app.state.controller.adapter.stop()
        if settings.tunnel_autostart:
            from app import tunnel as _tunnel

            if _tunnel.ACTIVE is not None:
                _tunnel.ACTIVE.stop()
                _tunnel.ACTIVE = None
        await app.state.http.aclose()
        engine.dispose()

    app = FastAPI(title="Paytience", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.clock = clock or SystemClock()
    app.state.rules = RulesHolder(rules, plan=settings.rules_path.stem)
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.hub = Hub()
    app.state.bus = EventBus(app.state.hub, app.state.sessionmaker, app.state.clock.now)
    app.state.login_limiter = RateLimiter(5, 60)
    app.state.webhook_limiter = SlidingWindow(rules.rules.webhook.rate_limit_per_min, 60)
    app.state.webhook_stats = WebhookStats()
    app.state.market = MarketStateStore()
    app.state.ws_throttle = {}
    app.state.signal_locks = {}
    app.state.inflight_events = set()  # event ids whose background processing is running (replay skips them)
    app.state.replay_attempts = {}
    app.state.calendar = no_calendar
    app.state.stats_cache = StatsCache()
    sim = SimAdapter(
        app.state.clock,
        {k: SimInstrument(v.tick, v.tick_value, v.fee_rt) for k, v in rules.rules.instruments.items()},
        rules.rules.trade_plan.slippage_ticks,
    )
    broker = RoutingAdapter(sim)
    app.state.controller = Controller(
        app.state.sessionmaker,
        app.state.clock,
        app.state.rules,
        broker,
        OrderManager(
            broker,
            rules.rules.drawdown_guard.runner_trail_r,
            rules.rules.behavior.min_hold_seconds,
            rules.rules.drawdown_guard.early_exits_until_r,
        ),
    )
    app.state.controller.bus = app.state.bus
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
        log.error("unhandled", path=request.url.path, error=type(exc).__name__, detail=str(exc)[:300], exc_info=True)
        return JSONResponse({"detail": "internal error — see logs"}, status_code=500)

    app.include_router(router)
    app.include_router(webhook_router)
    app.include_router(signals_router)
    app.include_router(logs_router)
    app.include_router(risk_router)
    app.include_router(automation_router)
    app.include_router(live_router)
    app.include_router(dashboard_router)
    app.include_router(ai_ledger_router)
    app.include_router(research_router)  # D94: information only
    app.include_router(income_router)
    app.include_router(plan_router)  # before payouts: /payouts/settings must not hit /payouts/{pid}
    app.include_router(payouts_router)
    app.include_router(journal_router)
    app.include_router(orders_router)
    app.include_router(notifications_router)
    app.include_router(insights_router)
    app.include_router(backtest_router)
    app.include_router(gate_router)
    app.include_router(lab_router)
    app.include_router(market_router)
    app.include_router(replay_router)
    app.include_router(orderflow_router)  # D98: order-flow chart (display only, estimated)
    app.include_router(strategy_gates_router)  # D106: per-strategy gates (read-only)
    app.include_router(updates_router)
    app.include_router(system_router)  # D97: local-only shutdown for a newer start

    @app.websocket("/api/ws")
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
        app.mount("/assets", _ImmutableAssets(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str) -> Response:
            if path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            f = (dist / path).resolve()
            if path and f.is_file() and dist.resolve() in f.parents:
                return FileResponse(f, headers=NO_CACHE)  # sw.js, manifest, icons: always revalidate
            return FileResponse(dist / "index.html", headers=NO_STORE)  # D97: never serve a cached old interface

    return app


NO_STORE = {"Cache-Control": "no-store"}  # D97: index.html + SPA fallback
NO_CACHE = {"Cache-Control": "no-cache"}


class _ImmutableAssets(StaticFiles):
    """Vite's /assets/* names contain a content hash, so they can be cached forever; index.html never is."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        resp = await super().get_response(path, scope)
        if resp.status_code == 200:
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp


def _decimal_guard() -> None:
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")


_decimal_guard()
