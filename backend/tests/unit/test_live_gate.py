from dataclasses import replace

from app.risk.live_gate import LIVE_PHRASE, LiveInputs, can_enable_toggle, checklist, live_allowed

OK = LiveInputs(True, True, "crosstrade", True, True, 20, 0, True, None)


def test_all_ok_allows_live():
    assert live_allowed(OK)
    assert all(c["detail"] == "" for c in checklist(OK))


def test_any_single_failure_blocks_live():
    for f in [
        {"env_allow_live": False},
        {"toggle_on": False},
        {"broker_reads_back": False},
        {"broker_connected": False},
        {"parity_sessions": 19},
        {"unconfirmed_verify": 1},
        {"preflight_ok": False},
        {"rules_error": "bad yaml"},
    ]:
        i = replace(OK, **f)
        assert not live_allowed(i), f
        assert sum(not c["ok"] for c in checklist(i)) == 1


def test_phrase():
    assert can_enable_toggle(f"  {LIVE_PHRASE} ")
    assert not can_enable_toggle("i accept live risk")
