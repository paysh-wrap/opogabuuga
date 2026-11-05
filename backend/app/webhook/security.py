"""Webhook authentication + freshness checks (§5.4, §20). Pure functions; the route wires them up."""

from __future__ import annotations

import hmac
from dataclasses import dataclass

from app.config import WebhookCfg


@dataclass(frozen=True)
class Rejection:
    status: int
    code: str
    detail: str


def secret_ok(expected: str, given: str) -> bool:
    """Constant-time comparison. An empty server secret rejects everything."""
    if not expected:
        return False
    return hmac.compare_digest(expected.encode(), given.encode())


def freshness(event: str, bar_time_ms: int, now_ms: int, cfg: WebhookCfg) -> Rejection | None:
    """Age is measured from the bar CLOSE (TradingView time_close), so 15m/1H heartbeats are not stale."""
    age_ms = now_ms - bar_time_ms
    if age_ms < -cfg.max_future_skew_s * 1000:
        return Rejection(422, "FUTURE_TIMESTAMP", f"bar time is {-age_ms // 1000}s in the future (clock skew?)")
    limit = cfg.heartbeat_max_age_s if event == "HEARTBEAT" else cfg.event_max_age_s
    if age_ms > limit * 1000:
        return Rejection(422, "STALE", f"{event} is {age_ms // 1000}s old (limit {limit}s)")
    return None
