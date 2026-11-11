import json
import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.models import AuditLog, Bar, Event
from tests.conftest import WEBHOOK_SECRET

NOW = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)  # Thursday 10:00 ET — CME open
NOW_MS = int(NOW.timestamp() * 1000)


def hb(age_s=1, **over):
    p = {
        "v": 1,
        "secret": WEBHOOK_SECRET,
        "id": f"MNQ1!-TIGHT-{NOW_MS - age_s * 1000}-HEARTBEAT",
        "symbol": "MNQ1!",
        "profile": "TIGHT",
        "tf": "1",
        "bar_time_ms": NOW_MS - age_s * 1000,
        "event": "HEARTBEAT",
        "direction": "NONE",
        "price": {"o": "20000.25", "h": "20001.00", "l": "19999.50", "c": "20000.75", "v": "1234"},
    }
    p.update(over)
    return p


def mso_evt(event="MSO_CHOCH", age_s=5, **over):
    p = {
        "v": 1,
        "secret": WEBHOOK_SECRET,
        "id": f"MNQ1!-TIGHT-{NOW_MS}-{event}-LONG",
        "symbol": "MNQ1!",
        "profile": "TIGHT",
        "tf": "1",
        "bar_time_ms": NOW_MS - age_s * 1000,
        "event": event,
        "direction": "LONG",
        "mso": {
            "trend": "BULL",
            "osc": "60",
            "div": None,
            "htf_trend": "BULL",
            "confirm_time_ms": NOW_MS - age_s * 1000,
        },
    }
    p.update(over)
    return p


def fractal_evt(event="MODEL_CONFIRMED", age_s=5, **over):
    p = {
        "v": 1,
        "secret": WEBHOOK_SECRET,
        "id": f"MNQ1!-TIGHT-{NOW_MS}-{event}",
        "symbol": "MNQ1!",
        "profile": "TIGHT",
        "tf": "1",
        "bar_time_ms": NOW_MS - age_s * 1000,
        "event": event,
        "direction": "LONG",
        "fractal": {
            "c1_high": "20050",
            "c1_low": "19990",
            "c1_time_ms": NOW_MS - 1_800_000,
            "htf_atr14": "60.5",
            "t1": "20020",
            "t2": "20050",
            "invalid": "19981",
            "sweep_extreme": "19981",
            "sweep_time_ms": NOW_MS - 600_000,
            "cisd_level": "20005",
            "cisd_before_c2_close": True,
            "t1_preticked": False,
            "c3_close_time_ms": NOW_MS + 900_000,
        },
    }
    p.update(over)
    return p


def post(c, payload, raw=None):
    body = raw if raw is not None else json.dumps(payload)
    return c.post("/api/webhook/tradingview", content=body, headers={"content-type": "text/plain"})


@pytest.fixture
def wc(client, clock):
    clock.set(NOW)
    return client


def test_heartbeat_accepted_fast_and_stored_exactly(wc):
    t0 = time.perf_counter()
    r = post(wc, hb())
    assert time.perf_counter() - t0 < 1.0  # §5.4 respond within 1 s
    assert r.status_code == 200 and r.json() == {"ok": True, "duplicate": False}
    with wc.app.state.sessionmaker() as s:
        ev = s.query(Event).one()
        assert (ev.symbol, ev.profile, ev.event) == ("MNQ", "TIGHT", "HEARTBEAT")
        assert "secret" not in json.dumps(ev.payload)  # never stored
        bar = s.query(Bar).one()
        assert str(bar.c) == "20000.75" and bar.tf == "1"
    st = wc.app.state.market.get("MNQ", "TIGHT")
    assert st is not None and st.last_heartbeat_ms == NOW_MS - 1000


def test_duplicate_is_idempotent(wc):
    assert post(wc, hb()).json()["duplicate"] is False
    assert post(wc, hb()).json()["duplicate"] is True
    with wc.app.state.sessionmaker() as s:
        assert s.query(Event).count() == 1


def test_bad_secret_rejected_and_audited_once(wc):
    for _ in range(3):
        r = post(wc, hb(secret="wrong"))
        assert r.status_code == 401 and r.json()["code"] == "BAD_SECRET"
    with wc.app.state.sessionmaker() as s:
        assert s.query(Event).count() == 0
        assert s.query(AuditLog).filter_by(action="webhook.bad_secret").count() == 1


def test_empty_server_secret_rejects_everything(wc):
    from pydantic import SecretStr

    wc.app.state.settings.webhook_secret = SecretStr("")
    assert post(wc, hb(secret="")).status_code == 401


@pytest.mark.parametrize(
    "payload_fn,age,ok",
    [
        (hb, 29, True),
        (hb, 31, False),  # HEARTBEAT > 30 s → reject
        (mso_evt, 89, True),
        (mso_evt, 91, True),  # D120: MSO alerts are ignored (200) before any freshness check
    ],
)
def test_freshness_limits(wc, payload_fn, age, ok):
    r = post(wc, payload_fn(age_s=age))
    assert (r.status_code == 200) is ok, r.text
    if not ok:
        assert r.json()["code"] == "STALE"


def test_test_alert_is_a_dry_run(authed, clock):
    clock.set(NOW)

    def t(body):
        return authed.post("/api/webhook/test-alert", content=body).json()

    assert t(json.dumps(hb())) == {"ok": True, "code": "OK", "detail": "HEARTBEAT NONE MNQ1! TIGHT 1"}
    assert t(json.dumps(hb(secret="wrong")))["code"] == "BAD_SECRET"
    assert t("not json")["code"] == "BAD_JSON"
    with authed.app.state.sessionmaker() as s:
        assert s.query(Event).count() == 0  # nothing stored
    assert authed.app.state.market.get("MNQ", "TIGHT") is None
    authed.headers.pop("x-csrf-token")
    assert authed.post("/api/webhook/test-alert", content="{}").status_code in (401, 403)


def test_future_timestamp_rejected(wc):
    r = post(wc, hb(age_s=-60))
    assert r.status_code == 422 and r.json()["code"] == "FUTURE_TIMESTAMP"


def test_std_profile_heartbeat_age_from_bar_close_not_stale(wc):
    # 5m chart: bar closed 2 s ago → fresh even though the bar OPENED 5 min ago
    r = post(wc, hb(age_s=2, profile="STD", tf="5", id="MNQ1!-STD-x-HEARTBEAT"))
    assert r.status_code == 200


@pytest.mark.parametrize(
    "over,code",
    [
        ({"symbol": "ESZ6", "id": "a"}, "UNKNOWN_SYMBOL"),
        ({"tf": "5", "id": "b"}, "TF_MISMATCH"),
        ({"event": "NOPE", "id": "c"}, "BAD_PAYLOAD"),
        ({"price": None, "id": "d"}, "BAD_PAYLOAD"),
        ({"v": 2, "id": "e"}, "BAD_PAYLOAD"),
        ({"extra_field": 1, "id": "f"}, "BAD_PAYLOAD"),
    ],
)
def test_invalid_payloads(wc, over, code):
    r = post(wc, hb(**over))
    assert r.status_code == 422 and r.json()["code"] == code


def test_fractal_event_without_fields_rejected(wc):
    r = post(wc, fractal_evt(fractal=None))
    assert r.status_code == 422 and "fractal" in r.json()["detail"]


def test_malformed_json_and_too_large(wc):
    assert post(wc, None, raw="{not json").json()["code"] == "BAD_JSON"
    assert post(wc, None, raw="x" * 20000).status_code == 413


def test_contract_symbols_map_to_root(wc):
    for i, sym in enumerate(("MNQZ2026", "MNQZ6", "CME_MINI:MNQ1!")):
        assert post(wc, hb(symbol=sym, id=f"m{i}")).status_code == 200


def test_pine_empty_extra_produces_valid_json(wc):
    """§21: f_send with extra == '' must still be valid JSON (no trailing comma)."""
    raw = (
        '{"v":1,"secret":"' + WEBHOOK_SECRET + '","id":"MNQ1!-TIGHT-' + str(NOW_MS) + '-MSO_BOS","symbol":"MNQ1!",'
        '"profile":"TIGHT","tf":"1","bar_time_ms":' + str(NOW_MS) + ',"event":"HEARTBEAT","direction":"NONE"}'
    )
    r = post(wc, None, raw=raw)
    assert r.json()["code"] == "BAD_PAYLOAD"  # valid JSON; rejected only because HEARTBEAT needs price
    assert "price" in r.json()["detail"]


def test_lunqfx_model_event_is_ignored_and_stores_nothing(wc):
    """D105: fractal alerts answer 200 {ignored, LUNQFX_REMOVED}; no Event row, no market state."""
    r = post(wc, fractal_evt())
    assert r.status_code == 200 and r.json()["ignored"] is True and r.json()["code"] == "LUNQFX_REMOVED"
    assert wc.app.state.market.get("MNQ", "TIGHT") is None
    with wc.app.state.sessionmaker() as s:
        assert s.query(Event).count() == 0


def test_rate_limit(wc):
    wc.app.state.webhook_limiter.max_hits = 3
    codes = [post(wc, hb(id=f"r{i}")).status_code for i in range(5)]
    assert codes == [200, 200, 200, 429, 429]


def test_status_endpoint_and_connections_card_react(authed, clock, mock_http):
    # /api/connections also asks GitHub for the latest TradingAgents tag; stub it (was order-dependent: passed only
    # when an earlier test had filled the module-level tag cache)
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)
    clock.set(NOW)
    assert post(authed, hb()).status_code == 200
    st = authed.get("/api/webhook/status").json()
    assert st["feeds"] == [
        {
            "symbol": "MNQ",
            "profile": "TIGHT",
            "last_heartbeat": st["feeds"][0]["last_heartbeat"],
            "data_feed": "unknown",
            "status": "FRESH",
        }
    ]
    assert st["accepted"]["HEARTBEAT"] == 1 and st["secret_set"] is True
    card = next(c for c in authed.get("/api/connections").json()["connections"] if c["id"] == "tradingview")
    assert card["status"] == "connected" and "MNQ TIGHT: fresh" in card["detail"]
    clock.set(NOW + timedelta(minutes=5))  # no heartbeat for 5 bars → stale
    card = next(c for c in authed.get("/api/connections").json()["connections"] if c["id"] == "tradingview")
    assert card["status"] == "failed"


def test_secret_reveal_requires_login_csrf_and_is_audited(client, authed):
    r = authed.post("/api/webhook/secret/reveal")
    assert r.json() == {"secret": WEBHOOK_SECRET}
    with authed.app.state.sessionmaker() as s:
        assert s.query(AuditLog).filter_by(action="webhook.secret_revealed").count() == 1
    del authed.headers["x-csrf-token"]
    assert authed.post("/api/webhook/secret/reveal").status_code == 403


def test_pine_download(authed):
    r = authed.get("/api/pine/bridge")
    assert r.status_code == 200 and r.text.startswith("//@version=6")
    assert "Paytience_Bridge" in r.text and "PERSONAL USE ONLY" in r.text
    assert 'attachment; filename="Paytience_Bridge.pine"' in r.headers["content-disposition"]
    assert authed.get("/api/pine/../../etc/passwd").status_code == 404


def test_same_bar_opposite_direction_events_are_not_deduplicated(wc):
    """Spec §5.3's id had no direction: an outside bar sweeping both sides would collide. Ids now end in -DIR."""
    base = mso_evt("MSO_BOS")
    a = {**base, "id": f"MNQ1!-TIGHT-{NOW_MS}-MSO_BOS-LONG", "direction": "LONG"}
    b = {**base, "id": f"MNQ1!-TIGHT-{NOW_MS}-MSO_BOS-SHORT", "direction": "SHORT"}
    ra, rb = post(wc, a).json(), post(wc, b).json()
    assert ra["code"] == rb["code"] == "MSO_REMOVED" and ra["ignored"] and rb["ignored"]  # D120: MSO alerts ignored
