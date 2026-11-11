"""Webhook ingestion: validate → authenticate → freshness → idempotent store. Sync DB work (run in threadpool)."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import audit
from app.clock import Clock
from app.config import RulesConfig
from app.indicators.bars import tf_minutes
from app.models import Bar as BarRow
from app.models import Event
from app.webhook.parser_bridge import map_symbol, parse
from app.webhook.schemas import FRACTAL_EVENTS, WebhookPayload
from app.webhook.security import Rejection, freshness, secret_ok


class SlidingWindow:
    def __init__(self, max_hits: int, per_s: float) -> None:
        self.max_hits, self.per = max_hits, per_s
        self._q: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now_s: float) -> bool:
        q = self._q[key]
        while q and q[0] <= now_s - self.per:
            q.popleft()
        if len(q) >= self.max_hits:
            return False
        q.append(now_s)
        return True


@dataclass
class WebhookStats:
    accepted: Counter[str] = field(default_factory=Counter)
    rejected: Counter[str] = field(default_factory=Counter)
    last_rejection: dict[str, Any] | None = None
    last_bad_secret_audit_s: dict[str, float] = field(default_factory=dict)

    def reject(self, r: Rejection, at: datetime, ip: str) -> None:
        self.rejected[r.code] += 1
        self.last_rejection = {"code": r.code, "detail": r.detail, "at": at.isoformat(), "ip": ip}


@dataclass(frozen=True)
class Accepted:
    payload: WebhookPayload
    symbol: str
    duplicate: bool


@dataclass(frozen=True)
class Ignored:
    """D105: a LunqFX fractal alert (feature removed): acknowledged with 200 (no TradingView error), nothing stored."""

    code: str
    detail: str


def ingest(
    s: Session, body: bytes, *, rules: RulesConfig, secret: str, clock: Clock, ip: str, stats: WebhookStats
) -> Accepted | Ignored | Rejection:
    now = clock.now()
    p, rej = parse(body, rules)
    if rej is not None or p is None:
        assert rej is not None
        stats.reject(rej, now, ip)
        return rej
    if not secret_ok(secret, p.secret.get_secret_value()):
        r = Rejection(401, "BAD_SECRET", "webhook secret mismatch")
        stats.reject(r, now, ip)
        last = stats.last_bad_secret_audit_s.get(ip, 0.0)
        if now.timestamp() - last > 60:  # audit at most once a minute per source
            stats.last_bad_secret_audit_s[ip] = now.timestamp()
            audit.record(s, clock, "webhook", "webhook.bad_secret", ip, {"symbol": p.symbol, "event": p.event})
            s.commit()
        return r
    sym = map_symbol(p.symbol, rules)
    if sym is None:
        r = Rejection(422, "UNKNOWN_SYMBOL", f"{p.symbol!r} is not a configured instrument")
        stats.reject(r, now, ip)
        return r
    if p.event in FRACTAL_EVENTS:
        stats.accepted["LUNQFX_REMOVED"] += 1
        detail = "LunqFX was removed from Paytience (D105): this alert is ignored - delete it in TradingView"
        return Ignored("LUNQFX_REMOVED", detail)
    expected_tf = rules.profiles.TIGHT.ltf if p.profile == "TIGHT" else rules.profiles.STD.ltf
    try:
        tf_ok = tf_minutes(p.tf) == tf_minutes(expected_tf)
    except ValueError:
        tf_ok = False
    if not tf_ok:
        r = Rejection(422, "TF_MISMATCH", f"profile {p.profile} expects a {expected_tf}m chart, got {p.tf!r}")
        stats.reject(r, now, ip)
        return r
    fr = freshness(p.event, p.bar_time_ms, int(now.timestamp() * 1000), rules.webhook)
    if fr is not None:
        stats.reject(fr, now, ip)
        return fr
    bar_time = datetime.fromtimestamp(p.bar_time_ms / 1000, tz=now.tzinfo)
    payload_json = p.model_dump(mode="json", exclude={"secret"})
    try:
        s.add(
            Event(
                event_id=p.id,
                symbol=sym,
                profile=p.profile,
                event=p.event,
                direction=p.direction,
                bar_time=bar_time,
                payload=payload_json,
            )
        )
        s.flush()
    except IntegrityError:
        s.rollback()
        stats.accepted["DUPLICATE"] += 1
        return Accepted(p, sym, duplicate=True)
    if p.event == "HEARTBEAT" and p.price is not None:
        try:
            with s.begin_nested():
                s.add(
                    BarRow(
                        symbol=sym,
                        tf=p.tf,
                        close_time=bar_time,
                        o=p.price.o,
                        h=p.price.h,
                        l=p.price.l,
                        c=p.price.c,
                        v=p.price.v,
                        source="tradingview",
                    )
                )
        except IntegrityError:
            pass  # same bar already recorded
    s.commit()
    stats.accepted[p.event] += 1
    return Accepted(p, sym, duplicate=False)
