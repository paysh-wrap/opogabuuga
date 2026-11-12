from dataclasses import replace
from datetime import date

from app.risk.live_gate import (
    LIVE_PHRASE,
    MIN_PAPER_SESSIONS,
    LiveInputs,
    PaperDay,
    can_enable_toggle,
    checklist,
    clean_paper_sessions,
    live_allowed,
)

OK = LiveInputs(True, True, "crosstrade", True, True, MIN_PAPER_SESSIONS, 0, True, None)


def test_all_ok_allows_live():
    assert live_allowed(OK)
    assert all(c["detail"] == "" for c in checklist(OK))


def test_any_single_failure_blocks_live():
    for f in [
        {"env_allow_live": False},
        {"toggle_on": False},
        {"broker_reads_back": False},
        {"broker_connected": False},
        {"paper_sessions": MIN_PAPER_SESSIONS - 1},
        {"unconfirmed_verify": 1},
        {"preflight_ok": False},
        {"rules_error": "bad yaml"},
    ]:
        i = replace(OK, **f)
        assert not live_allowed(i), f
        assert sum(not c["ok"] for c in checklist(i)) == 1


def test_readiness_off_skips_only_the_paper_sessions_item():
    """B1: "off" skips that single item (labelled); every other gate still blocks."""
    off = replace(OK, paper_sessions=0, readiness_mode="off")
    assert live_allowed(off)
    item = next(c for c in checklist(off) if c["check"] == "paper_sessions")
    assert item["ok"] is True and item["skipped"] is True and "OFF" in str(item["detail"])
    assert not live_allowed(replace(off, toggle_on=False)) and not live_allowed(replace(off, env_allow_live=False))
    unknown = replace(OK, paper_sessions=3, readiness_mode="whatever")  # unknown mode → the count applies
    item = next(c for c in checklist(unknown) if c["check"] == "paper_sessions")
    assert item["ok"] is False and str(item["detail"]).startswith(f"3/{MIN_PAPER_SESSIONS}")


def test_clean_paper_sessions_counts_only_completed_error_free_trading_sessions():
    today = date(2026, 11, 12)
    days = [
        PaperDay(date(2026, 11, 9), 2, 0),  # counts
        PaperDay(date(2026, 11, 10), 1, 1),  # an error banner → not counted
        PaperDay(date(2026, 11, 11), 0, 0),  # no paper trade of an active strategy → not counted
        PaperDay(today, 3, 0),  # not completed yet
    ]
    assert clean_paper_sessions(days, today) == 1
    assert clean_paper_sessions([], today) == 0


def test_phrase():
    assert can_enable_toggle(f"  {LIVE_PHRASE} ")
    assert not can_enable_toggle("i accept live risk")
