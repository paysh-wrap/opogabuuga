"""D179: CME early closes (pure) + the controller flatten / entry block. Dates come from config/early_closes.yaml."""

import asyncio
from datetime import UTC, date, datetime, time

import pytest

from app.early_close import table
from app.risk.early_close import EarlyClose, close_minute, entries_blocked, flatten_due

EC = EarlyClose({"2026-11-27": "13:15", "2026-12-25": "closed"}, 45, 20)
D = date(2026, 11, 27)


def test_pure_rules():
    assert close_minute(EC, D) == 13 * 60 + 15 and close_minute(EC, date(2026, 11, 30)) is None
    assert close_minute(EC, date(2026, 12, 25)) == 0 and close_minute(None, D) is None
    assert not entries_blocked(EC, D, time(12, 29)) and entries_blocked(EC, D, time(12, 30))  # close - 45
    assert not flatten_due(EC, D, time(12, 54)) and flatten_due(EC, D, time(12, 55))  # close - 20
    assert entries_blocked(EC, date(2026, 12, 25), time(0, 1)) and flatten_due(EC, date(2026, 12, 25), time(0, 1))
    for fn in (entries_blocked, flatten_due):  # normal day / no table: unchanged
        assert not fn(EC, date(2026, 11, 30), time(15, 59)) and not fn(None, D, time(15, 59))


def test_config_table_is_loaded_from_the_file_and_marked_unverified():
    t = table()
    assert t is not None and t.days["2026-11-27"] == "13:15" and t.days["2026-11-26"] == "13:00"
    assert t.days["2026-12-24"] == "13:15" and t.days["2026-12-25"] == "closed"
    assert (t.no_entry_before_min, t.flatten_before_min) == (45, 20)
    assert "unverified: true" in open(__import__("app.early_close", fromlist=["PATH"]).PATH).read()


def test_missing_or_bad_file_changes_nothing(monkeypatch, tmp_path):
    import app.early_close as m

    monkeypatch.setattr(m, "PATH", tmp_path / "nope.yaml")
    m.table.cache_clear()
    assert m.table() is None
    m.table.cache_clear()


def _et(day, h, m):  # late November / December = EST (UTC-5)
    return datetime(day.year, day.month, day.day, h + 5, m, tzinfo=UTC)


def _open(st):
    async def go():
        with st.sessionmaker() as s:
            return await st.controller.open_positions(s)

    return asyncio.run(go())


@pytest.mark.parametrize(("day", "flat_at_1256"), [(date(2026, 11, 27), True), (date(2026, 11, 30), False)])
def test_noise_long_is_flattened_before_the_early_close_but_not_on_a_normal_day(authed, clock, day, flat_at_1256):
    from tests.integration.trade_helpers import _setup, _sig

    st, (a,) = _setup(authed, clock, [("a", "25000")], noise=True)
    clock.set(_et(day, 11, 0))
    from app.clock import session_date
    from app.models import Attestation, User

    with st.sessionmaker() as s:  # attestation is per session day (the login also expires with the clock jump)
        s.add(Attestation(session_date=session_date(clock.now()), user_id=s.query(User).first().id, text="t"))
        s.commit()
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[a]))[0].ok
    clock.set(_et(day, 12, 54))
    assert asyncio.run(st.controller.flat_time_check()) is None  # not yet: close - 20 is 12:55
    assert _open(st)
    clock.set(_et(day, 12, 56))
    got = asyncio.run(st.controller.flat_time_check())
    assert (got == "EARLY_CLOSE") is flat_at_1256
    assert (_open(st) == []) is flat_at_1256


def test_no_new_entry_after_close_minus_45_and_late_day_is_skipped(authed, clock, loaded_rules, monkeypatch):
    from app.signals import strategy_service as SS
    from tests.integration.trade_helpers import _setup

    st, _ = _setup(authed, clock, [("a", "25000")], noise=True)
    clock.set(_et(date(2026, 11, 27), 12, 31))
    assert st.controller.entries_blocked_by_time() is True
    clock.set(_et(date(2026, 11, 30), 12, 31))
    assert st.controller.entries_blocked_by_time() is False
    monkeypatch.setattr(SS, "in_windows", lambda *_a: True)  # isolate the early-close rule from the trading windows
    cal = lambda _d: []  # noqa: E731
    ok, code, _ = SS._gate(loaded_rules.rules, "MNQ", _et(date(2026, 11, 27), 15, 0), cal, True)  # late-day 15:00 entry
    assert not ok and code == "EARLY_CLOSE"
    ok, code, _ = SS._gate(loaded_rules.rules, "MNQ", _et(date(2026, 11, 30), 15, 0), cal, True)
    assert ok and code == "OK"
