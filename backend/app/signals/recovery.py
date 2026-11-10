"""Lost-signal protection (session 14, item 3): replay heartbeats that were accepted but never processed, and flag a
NOISE check minute that has no stored bar. DB + app glue (the pure decisions stay in strategy_service)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update

from app.clock import ET
from app.config import RulesConfig
from app.engine import noise as N
from app.models import Bar, Event
from app.webhook.schemas import WebhookPayload
from app.webhook.service import Accepted

log = structlog.get_logger()
MIN_AGE_S = 20  # a heartbeat younger than this is probably still in its normal background task
MAX_ATTEMPTS = 3  # a heartbeat that keeps failing is marked processed after this many replays (alert already sent)


async def reprocess_unprocessed(app: Any) -> int:
    """Replay (exits/management only) the heartbeats of the last reliability.reprocess_window_min minutes whose
    processed_at is still empty. Idempotent: a processed event is never touched; entries are never replayed."""
    from app.api.webhook import after_accept

    st = app.state
    now = st.clock.now()
    cfg = st.rules.rules.reliability
    with st.sessionmaker() as s:
        rows = list(
            s.execute(
                select(Event)
                .where(
                    Event.event == "HEARTBEAT",
                    Event.processed_at.is_(None),
                    Event.bar_time >= now - timedelta(minutes=cfg.reprocess_window_min),
                    Event.bar_time <= now - timedelta(seconds=MIN_AGE_S),
                )
                .order_by(Event.bar_time)
            ).scalars()
        )
        todo = [(e.event_id, e.symbol, dict(e.payload)) for e in rows]
    n = 0
    for event_id, symbol, payload in todo:
        if event_id in st.inflight_events:
            continue
        try:
            acc = Accepted(WebhookPayload.model_validate({**payload, "secret": "-"}), symbol, duplicate=False)
        except ValueError:
            _give_up(st, event_id, "unreadable payload")
            continue
        tries = st.replay_attempts.get(event_id, 0) + 1
        st.replay_attempts[event_id] = tries
        await after_accept(app, acc, replay=True)
        n += 1
        if tries >= MAX_ATTEMPTS and _unprocessed(st, event_id):
            _give_up(st, event_id, f"{tries} replays failed")
    if n:
        log.info("events.replayed", count=n)
        st.controller.notify(
            "warn", "Replayed missed price bars", f"{n} heartbeat(s) were accepted but not processed", "replay"
        )
    return n


def _unprocessed(st: Any, event_id: str) -> bool:
    with st.sessionmaker() as s:
        row = s.execute(select(Event.processed_at).where(Event.event_id == event_id)).first()
        return row is not None and row[0] is None


def _give_up(st: Any, event_id: str, why: str) -> None:
    with st.sessionmaker() as s:
        s.execute(update(Event).where(Event.event_id == event_id).values(processed_at=st.clock.now()))
        s.commit()
    st.controller.notify("error", "A price bar could not be processed", f"{event_id}: {why}", "replay")


def check_minute_closes(rules: RulesConfig, day: datetime) -> list[datetime]:
    """UTC close times of today's NOISE check minutes (weekdays only)."""
    cfg = rules.strategy.noise_cfg
    et = day.astimezone(ET)
    if et.weekday() >= 5:
        return []
    open_dt = et.replace(hour=N.RTH_OPEN.hour, minute=N.RTH_OPEN.minute, second=0, microsecond=0)
    return [
        (open_dt + timedelta(minutes=k + 1)).astimezone(day.tzinfo)
        for k in range(N.RTH_BARS)
        if N.is_check(k, cfg.check_minutes, cfg.first_check, cfg.last_check)
    ]


def missed_checks(s: Any, rules: RulesConfig, now: datetime, lookback_min: int = 30) -> list[dict[str, str]]:
    """NOISE check minutes that closed more than missed_check_alert_s ago (within lookback) with no stored 1-minute
    bar. Needs at least one bar already stored today (otherwise the market is simply closed / a holiday)."""
    if not rules.strategy.noise:
        return []
    symbol = rules.strategy.noise_cfg.symbol
    grace = timedelta(seconds=rules.reliability.missed_check_alert_s)
    due = [
        c for c in check_minute_closes(rules, now) if timedelta(0) <= now - c - grace <= timedelta(minutes=lookback_min)
    ]
    if not due:
        return []
    midnight = now.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0)
    have_any = s.execute(
        select(Bar.id).where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time >= midnight, Bar.close_time < due[0])
    ).first()
    if have_any is None:
        return []
    stored = set(
        s.execute(select(Bar.close_time).where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time.in_(due))).scalars()
    )
    return [
        {"symbol": symbol, "minute_et": c.astimezone(ET).strftime("%H:%M"), "key": f"{symbol}@{c.isoformat()}"}
        for c in due
        if c not in stored
    ]


def alert_missed_checks(app: Any) -> None:
    st = app.state
    with st.sessionmaker() as s:
        miss = missed_checks(s, st.rules.rules, st.clock.now())
    for m in miss:
        if m["key"] in st.controller._missed_alerted:
            continue
        st.controller._missed_alerted.add(m["key"])
        st.controller.notify(
            "error",
            "Missed check minute",
            f"{m['symbol']} {m['minute_et']} ET: no price bar arrived, so the NOISE decision for that minute was "
            "skipped. Check the TradingView alert / tunnel.",
            "missed_check",
        )
