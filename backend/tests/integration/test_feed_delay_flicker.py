"""Item 8 (session 22): two MNQ charts that disagree about CME delay no longer flip the state on every heartbeat."""

from tests.integration.test_signals_flow import MIN, MS, send


def _hb(c, clock, t, profile, feed):
    send(c, clock, "HEARTBEAT", t, "NONE", profile=profile, data_feed=feed,
         price={"o": "20000", "h": "20000", "l": "20000", "c": "20000", "v": "1"})  # fmt: skip


def _titles(ctl):
    return [n["title"] for n in ctl.notices if "CME data" in n["title"]]


def test_disagreeing_charts_block_once_and_clear_after_three_real_time_bars(authed, clock):
    ctl = authed.app.state.controller
    t = MS
    _hb(authed, clock, t, "TIGHT", "delayed")
    assert "MNQ" in ctl.feed_delayed and _titles(ctl) == ["CME data is DELAYED"]
    for i in range(1, 3):  # the 5m chart is fine and the 1m chart recovers: still blocked (old code cleared at once)
        _hb(authed, clock, t + i * 5 * MIN, "STD", "realtime")
        _hb(authed, clock, t + i * 5 * MIN + MIN, "TIGHT", "realtime")
        assert "MNQ" in ctl.feed_delayed
    _hb(authed, clock, t + 15 * MIN + MIN, "TIGHT", "realtime")  # 3rd real-time bar in a row on the 1m chart
    assert "MNQ" not in ctl.feed_delayed
    assert _titles(ctl) == ["CME data is DELAYED", "CME data is real-time again"]  # one notice per change, no spam
