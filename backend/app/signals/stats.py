"""History-based inputs for the D16 filters: model T1 hit rate (E2) and HTF-ATR percentile (E6). Read-only."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event

OUTCOME_EVENTS = ("MODEL_CONFIRMED", "T1_HIT", "MODEL_FAILED", "C3_CLOSED", "C1_SWEPT")


@dataclass
class History:
    outcomes: list[tuple[int, bool]]  # (c1_time_ms, reached T1) for resolved confirmed models, oldest first
    atrs: list[Decimal]


@dataclass
class StatsCache:
    ttl_s: float = 300.0
    _data: dict[tuple[str, str], tuple[float, History]] = field(default_factory=dict)

    def get(self, key: tuple[str, str]) -> History | None:
        hit = self._data.get(key)
        return hit[1] if hit and time.monotonic() - hit[0] < self.ttl_s else None

    def put(self, key: tuple[str, str], h: History) -> None:
        self._data[key] = (time.monotonic(), h)


def load_history(s: Session, symbol: str, profile: str, now: datetime, days: int = 120) -> History:
    rows = s.execute(
        select(Event.event, Event.payload).where(
            Event.symbol == symbol,
            Event.profile == profile,
            Event.event.in_(OUTCOME_EVENTS),
            Event.bar_time >= now - timedelta(days=days),
        )
    ).all()
    per: dict[int, set[str]] = {}
    atrs: dict[int, Decimal] = {}
    for ev, payload in rows:
        fr = (payload or {}).get("fractal") or {}
        key = fr.get("c1_time_ms")
        if key is None:
            continue
        per.setdefault(int(key), set()).add(ev)
        if fr.get("htf_atr14") is not None and ev == "MODEL_CONFIRMED":
            atrs[int(key)] = Decimal(str(fr["htf_atr14"]))
    outcomes = []
    for key in sorted(per):
        evs = per[key]
        if "MODEL_CONFIRMED" not in evs:
            continue
        if "T1_HIT" in evs:
            outcomes.append((key, True))
        elif "MODEL_FAILED" in evs or "C3_CLOSED" in evs:
            outcomes.append((key, False))
    return History(outcomes, [atrs[k] for k in sorted(atrs)])


def t1_rate(h: History, exclude_c1: int | None, last_n: int = 100) -> tuple[Decimal | None, int]:
    xs = [ok for k, ok in h.outcomes if k != exclude_c1][-last_n:]
    if not xs:
        return None, 0
    return (Decimal(sum(xs)) / Decimal(len(xs))).quantize(Decimal("0.0001")), len(xs)


def atr_percentile(h: History, value: Decimal | None, last_n: int = 300) -> tuple[Decimal | None, int]:
    xs = h.atrs[-last_n:]
    if value is None or not xs:
        return None, len(xs)
    below = sum(1 for v in xs if v < value)
    equal = sum(1 for v in xs if v == value)
    return (Decimal(100) * (Decimal(below) + Decimal(equal) / 2) / len(xs)).quantize(Decimal("0.1")), len(xs)
