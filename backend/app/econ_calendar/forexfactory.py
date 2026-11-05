"""Economic calendar from the ForexFactory weekly JSON feed (format verified 2026-11-05):
GET https://nfs.faireconomy.media/ff_calendar_thisweek.json → list of
{"title", "country" (currency code, e.g. "USD"), "date" ("2026-11-06T08:30:00-05:00", ISO with offset),
 "impact" ("High" | "Medium" | "Low" | "Holiday"), "forecast", "previous"}.
Covers the current week only (Sun–Sat). Fetched at most a few times a day (feed is CDN-cached 60 s).
Only USD High-impact events matter (blackouts / funded hard-breach windows). No data = no trading (§15).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import httpx

from app.clock import to_et
from app.engine.filters import NewsEvent

URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


class CalendarError(Exception):
    pass


def parse(raw: Any) -> list[NewsEvent]:
    if not isinstance(raw, list):
        raise CalendarError("calendar feed: expected a JSON list")
    out = []
    for e in raw:
        if not isinstance(e, dict) or e.get("country") != "USD" or e.get("impact") != "High":
            continue
        at = datetime.fromisoformat(str(e["date"]))
        if at.tzinfo is None:
            raise CalendarError(f"calendar feed: date without offset: {e['date']}")
        out.append(NewsEvent(at=at, title=str(e.get("title", "")), currency="USD", impact="high"))
    return sorted(out, key=lambda n: n.at)


def week_of(d: date) -> tuple[date, date]:
    """ForexFactory week: Sunday → Saturday."""
    start = d - timedelta(days=(d.weekday() + 1) % 7)
    return start, start + timedelta(days=6)


async def fetch(http: httpx.AsyncClient) -> list[NewsEvent]:
    try:
        r = await http.get(URL, headers={"User-Agent": "Paytience/1.0 (personal use)"})
    except httpx.HTTPError as e:
        raise CalendarError(f"calendar fetch failed: {type(e).__name__}") from e
    if r.status_code != 200:
        raise CalendarError(f"calendar fetch: HTTP {r.status_code}")
    return parse(r.json())


class CalendarStore:
    """Holds the fetched week. provider(session_date) → events, or None when that date isn't covered (= no trading)."""

    def __init__(self) -> None:
        self.events: list[NewsEvent] = []
        self.fetched_at: datetime | None = None
        self.error: str | None = None

    def set(self, events: list[NewsEvent], now: datetime) -> None:
        self.events, self.fetched_at, self.error = events, now, None

    def __call__(self, d: date) -> list[NewsEvent] | None:
        if self.fetched_at is None:
            return None
        lo, hi = week_of(to_et(self.fetched_at).date())
        if not lo <= d <= hi:
            return None
        return [e for e in self.events if to_et(e.at).date() == d]

    def to_json(self) -> dict[str, Any]:
        return {
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "error": self.error,
            "events": [{"at": e.at.isoformat(), "title": e.title} for e in self.events],
        }

    @classmethod
    def from_json(cls, j: dict[str, Any]) -> CalendarStore:
        s = cls()
        if j.get("fetched_at"):
            s.fetched_at = datetime.fromisoformat(j["fetched_at"])
            s.events = [NewsEvent(at=datetime.fromisoformat(e["at"]), title=e["title"]) for e in j.get("events", [])]
        return s
