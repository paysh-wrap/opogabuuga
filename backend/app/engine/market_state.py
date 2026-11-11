"""Market State Store (§4): latest feed and MSO/trend snapshot per symbol+profile. Pure — no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.indicators.trend import TrendState
from app.webhook.schemas import MSO_EVENTS, WebhookPayload


@dataclass
class SymbolState:
    symbol: str
    profile: str
    tf: str
    last_heartbeat_ms: int | None = None
    last_price: dict[str, Decimal] | None = None
    mso: dict[str, Any] | None = None
    mso_events: list[tuple[str, str, int]] = field(default_factory=list)  # (event, direction, confirm_ms)
    trend: TrendState = field(default_factory=TrendState)  # D44 VWAP / EMA200 5m / UT Bot 5m


def _feed_trend(tr: TrendState, p: WebhookPayload) -> None:
    from datetime import UTC, datetime

    from app.clock import session_date
    from app.indicators.bars import tf_minutes

    assert p.price is not None
    tf_ms = tf_minutes(p.tf) * 60_000
    sess = session_date(datetime.fromtimestamp(p.bar_time_ms / 1000 - 1, tz=UTC)).toordinal()
    pr = p.price
    tr.update(p.bar_time_ms - tf_ms, tf_ms, sess, pr.o, pr.h, pr.l, pr.c, pr.v)  # bar_time_ms = bar CLOSE


@dataclass
class MarketStateStore:
    states: dict[tuple[str, str], SymbolState] = field(default_factory=dict)
    max_mso_events: int = 200

    def get(self, symbol: str, profile: str) -> SymbolState | None:
        return self.states.get((symbol, profile))

    def apply(self, symbol: str, p: WebhookPayload) -> SymbolState:
        st = self.states.setdefault((symbol, p.profile), SymbolState(symbol, p.profile, p.tf))
        st.tf = p.tf
        newer = st.last_heartbeat_ms is None or p.bar_time_ms >= st.last_heartbeat_ms
        if p.event == "HEARTBEAT" and p.price is not None and newer:
            st.last_heartbeat_ms = p.bar_time_ms
            st.last_price = p.price.model_dump()
            _feed_trend(st.trend, p)
        if p.mso is not None and (st.mso is None or p.mso.confirm_time_ms >= st.mso.get("confirm_time_ms", 0)):
            st.mso = p.mso.model_dump()
        if p.event in MSO_EVENTS:
            assert p.mso is not None
            st.mso_events.append((p.event, p.direction, p.mso.confirm_time_ms))
            del st.mso_events[: -self.max_mso_events]
        return st


def rebuild(store: MarketStateStore, rows: list[tuple[str, dict[str, Any]]]) -> int:
    """Replay stored webhook payloads (symbol, payload json) in bar-time order after a restart."""
    n = 0
    for symbol, payload in sorted(rows, key=lambda r: (r[1].get("bar_time_ms", 0), r[1].get("event") != "HEARTBEAT")):
        try:
            p = WebhookPayload.model_validate({**payload, "secret": "-"})
        except Exception:  # noqa: S112 - a malformed historic row must not block startup
            continue
        store.apply(symbol, p)
        n += 1
    return n
