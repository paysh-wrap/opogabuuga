"""Pure filter helpers for G1/G3 and the model-fail cooldown (§6). No I/O; times are aware datetimes or ms."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.clock import parse_hhmm, to_et


@dataclass(frozen=True)
class NewsEvent:
    at: datetime  # aware
    title: str
    currency: str = "USD"
    impact: str = "high"


def in_windows(at: datetime, windows: list[tuple[str, str]]) -> bool:
    t = to_et(at).time()
    return any(parse_hhmm(a) <= t < parse_hhmm(b) for a, b in windows)


def news_block(at: datetime, events: list[NewsEvent], before_min: int, after_min: int) -> NewsEvent | None:
    """High-impact USD event within [event − before_min, event + after_min] blocks new entries."""
    for e in events:
        if (
            e.currency == "USD"
            and e.impact == "high"
            and e.at - timedelta(minutes=before_min) <= at <= e.at + timedelta(minutes=after_min)
        ):
            return e
    return None


def c1_range_ok(
    c1_high: Decimal, c1_low: Decimal, htf_atr: Decimal | None, min_ratio: Decimal
) -> tuple[bool, Decimal | None]:
    if htf_atr is None or htf_atr <= 0:
        return False, None
    ratio = (c1_high - c1_low) / htf_atr
    return ratio >= min_ratio, ratio


def session_open_c1(c1_open_ms: int, open_times: list[str]) -> bool:
    t = to_et(datetime.fromtimestamp(c1_open_ms / 1000, tz=UTC)).time()
    return any(t == parse_hhmm(x) for x in open_times)


def add_sessions(d: date, n: int) -> date:
    """n trading sessions after d (Mon–Fri session dates; holidays not modelled)."""
    out = d
    while n > 0:
        out += timedelta(days=1)
        if out.weekday() < 5:
            n -= 1
    return out


@dataclass(frozen=True)
class CooldownState:
    streak: int = 0
    until_session: date | None = None

    def active(self, session: date) -> bool:
        return self.until_session is not None and session <= self.until_session


def cooldown_on_model_event(
    st: CooldownState, event: str, session: date, streak_limit: int, sessions: int
) -> CooldownState:
    """3 consecutive MODEL_FAILED → pause this symbol+profile for `sessions` sessions. Reaching T1 resets."""
    if event == "MODEL_FAILED":
        n = st.streak + 1
        if n >= streak_limit:
            return CooldownState(0, add_sessions(session, sessions))
        return CooldownState(n, st.until_session)
    if event in ("T1_HIT", "T2_HIT"):
        return CooldownState(0, st.until_session)
    return st


def entry_deadline_ms(confirm_ms: int, c3_close_ms: int, tf_min: int, max_wait_bars: int) -> int:
    """Expire after max_wait_bars LTF bars or half of C3, whichever comes first (§6)."""
    half_c3 = confirm_ms + (c3_close_ms - confirm_ms) // 2
    return min(confirm_ms + max_wait_bars * tf_min * 60_000, half_c3)
