import json
from datetime import UTC, datetime
from decimal import Decimal as D

from app.backtest.parity import compare, replay_payloads
from app.config import load_rules
from app.monitor.feed import cme_globex_open, feed_status
from app.webhook.parser_bridge import map_symbol, parse
from tests.conftest import RULES_PATH
from tests.unit.test_indicators import c1_bars, long_model_c2


def et(y, m, d, hh, mm):
    from zoneinfo import ZoneInfo

    return datetime(y, m, d, hh, mm, tzinfo=ZoneInfo("America/New_York"))


def test_cme_session_hours():
    assert cme_globex_open(et(2026, 11, 5, 10, 0))  # Thu
    assert not cme_globex_open(et(2026, 11, 5, 17, 30))  # daily halt
    assert cme_globex_open(et(2026, 11, 5, 18, 0))
    assert not cme_globex_open(et(2026, 11, 6, 17, 0))  # Fri close
    assert not cme_globex_open(et(2026, 11, 7, 12, 0))  # Sat
    assert not cme_globex_open(et(2026, 11, 8, 17, 59))  # Sun before open
    assert cme_globex_open(et(2026, 11, 8, 18, 0))


def test_feed_status():
    now = et(2026, 11, 5, 10, 0)
    ms = int(now.timestamp() * 1000)
    assert feed_status(ms - 60_000, 1, now, 2) == "FRESH"
    assert feed_status(ms - 121_000, 1, now, 2) == "STALE"
    assert feed_status(ms - 9 * 60_000, 5, now, 2) == "FRESH"  # STD 5m chart
    assert feed_status(None, 1, now, 2) == "NO_DATA"
    assert feed_status(ms, 1, et(2026, 11, 7, 12, 0), 2) == "CLOSED"


def test_symbol_mapping():
    r = load_rules(RULES_PATH).rules
    assert [map_symbol(s, r) for s in ("MNQ1!", "MGC1!", "MYMZ2026", "MESH7", "COMEX_MINI:MGC1!", "NQ1!", "ESZ6")] == [
        "MNQ",
        "MGC",
        "MYM",
        "MES",
        "MGC",
        None,
        None,
    ]


def _replay():
    r = load_rules(RULES_PATH).rules
    return replay_payloads(
        c1_bars() + long_model_c2(),
        symbol="MNQ1!",
        profile="TIGHT",
        tf="1",
        htf_min=15,
        tick=D("0.25"),
        atr_period=14,
        pivot_left=5,
        pivot_right=3,
    ), r


def test_replayed_payloads_pass_the_real_webhook_parser():
    payloads, rules = _replay()
    assert any(p["event"] == "MODEL_CONFIRMED" for p in payloads)
    for p in payloads:
        p2 = {**p, "secret": "s"}
        _parsed, rej = parse(json.dumps(p2).encode(), rules)
        assert rej is None, (p["event"], rej)


def test_parity_identical_streams_are_clean_and_perturbation_is_caught():
    a, _ = _replay()
    b = json.loads(json.dumps(a))
    rep = compare(a, b)
    assert rep.clean and rep.matched > 0 and not rep.passed(min_sessions=20)  # needs ≥20 sessions
    assert rep.passed(min_sessions=1)
    conf = next(p for p in b if p["event"] == "MODEL_CONFIRMED")
    conf["fractal"]["invalid"] = str(D(conf["fractal"]["invalid"]) - D("0.25"))
    b.append({**conf, "event": "T1_HIT", "id": "x"})
    rep = compare(a, b)
    assert not rep.clean
    assert any("invalid" in m for m in rep.field_mismatches) and len(rep.only_bridge) == 1


def test_parity_utc_session_grouping():
    a, _ = _replay()
    rep = compare(a, a)
    assert len(rep.sessions) == 1
    assert datetime.fromtimestamp(a[0]["bar_time_ms"] / 1000, tz=UTC).year == 2025
