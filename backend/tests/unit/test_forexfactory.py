from datetime import UTC, date, datetime

import httpx
import pytest

from app.econ_calendar.forexfactory import URL, CalendarError, CalendarStore, fetch, parse, week_of

# verbatim entries from the feed (2026-11-05)
RAW = [
    {
        "title": "Average Hourly Earnings m/m",
        "country": "USD",
        "date": "2026-11-06T08:30:00-05:00",
        "impact": "High",
        "forecast": "0.3%",
        "previous": "0.1%",
    },
    {
        "title": "Non-Farm Employment Change",
        "country": "USD",
        "date": "2026-11-06T08:30:00-05:00",
        "impact": "High",
        "forecast": "65K",
        "previous": "29K",
    },
    {
        "title": "Building Approvals m/m",
        "country": "AUD",
        "date": "2026-11-01T19:30:00-05:00",
        "impact": "Low",
        "forecast": "1.8%",
        "previous": "-6.1%",
    },
    {
        "title": "ISM",
        "country": "USD",
        "date": "2026-11-04T10:00:00-05:00",
        "impact": "Medium",
        "forecast": "",
        "previous": "",
    },
]
NOW = datetime(2026, 11, 5, 11, 0, tzinfo=UTC)


def test_parse_keeps_usd_high_only():
    ev = parse(RAW)
    assert [e.title for e in ev] == ["Average Hourly Earnings m/m", "Non-Farm Employment Change"]
    assert ev[0].at == datetime(2026, 11, 6, 13, 30, tzinfo=UTC)


def test_parse_rejects_bad_feed():
    with pytest.raises(CalendarError):
        parse({"x": 1})
    with pytest.raises(CalendarError):
        parse([{"country": "USD", "impact": "High", "date": "2026-11-06T08:30:00"}])


def test_week_and_store_coverage():
    assert week_of(date(2026, 11, 5)) == (date(2026, 11, 1), date(2026, 11, 7))
    s = CalendarStore()
    assert s(date(2026, 11, 6)) is None  # nothing fetched → no trading
    s.set(parse(RAW), NOW)
    assert len(s(date(2026, 11, 6))) == 2 and s(date(2026, 11, 5)) == []
    assert s(date(2026, 11, 9)) is None  # next week not covered → no trading
    s2 = CalendarStore.from_json(s.to_json())
    assert s2(date(2026, 11, 6)) == s(date(2026, 11, 6))
    assert CalendarStore.from_json({})(date(2026, 11, 6)) is None


async def test_fetch():
    ok = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=RAW)))
    assert len(await fetch(ok)) == 2
    bad = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(403)))
    with pytest.raises(CalendarError):
        await fetch(bad)

    def boom(r):
        raise httpx.ConnectError("x")

    with pytest.raises(CalendarError):
        await fetch(httpx.AsyncClient(transport=httpx.MockTransport(boom)))
    assert URL.startswith("https://nfs.faireconomy.media/")
