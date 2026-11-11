"""Signal runtime helpers shared by the strategy services.

D105 (user 2026-11-11): the LunqFX fractal confluence engine (market state -> gates G2-G7 -> stored Signal) was
removed from the runtime; only the helpers other strategies use remain here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.confluence import Bias
from app.engine.filters import NewsEvent
from app.models import BiasDecision

CalendarProvider = Callable[[date], list[NewsEvent] | None]


def no_calendar(_: date) -> list[NewsEvent] | None:
    """Phase 7 wires the real economic calendar. Until then: no data = no trading (§15)."""
    return None


@dataclass(frozen=True)
class SignalUpdate:
    signal_id: int
    model_key: str
    status: str
    reason: str | None
    score: str | None


def today_bias(s: Session, sess: date, proxy: str) -> Bias:
    """Bias computed on THIS instrument's proxy ETF (NQ→QQQ, ES→SPY, YM→DIA, GC→GLD). Missing → NO_TRADE."""
    row = s.execute(
        select(BiasDecision)
        .where(BiasDecision.session_date == sess, BiasDecision.proxy == proxy)
        .order_by(BiasDecision.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None or row.mapped not in ("LONG_ONLY", "SHORT_ONLY", "NEUTRAL"):
        return "NO_TRADE"
    return row.mapped  # type: ignore[return-value]
