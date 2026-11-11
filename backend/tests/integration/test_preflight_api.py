"""D99: pre-flight / arming through the API. Only MANDATORY items block; OPTIONAL ones never do."""

from datetime import timedelta
from email.utils import format_datetime

import httpx
import pytest
from sqlalchemy import select

from app.models import ApiCredential, BiasDecision
from tests.integration.test_signals_flow import AT, MIN, MS, hb


def _ready(authed, clock, *, bias=True, calendar=True, attest=True, heartbeat=True):
    st = authed.app.state
    clock.set(AT)
    st.calendar = (lambda d: []) if calendar else (lambda d: None)
    if heartbeat:
        hb(authed, clock, MS - MIN)
        clock.set(AT)
    if bias:
        with st.sessionmaker() as s:
            s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating="Buy", mapped="LONG_ONLY", version="x"))
            s.commit()
    if attest:
        assert authed.post("/api/attestation", json={"confirm": True}).status_code == 200
    st.clock_reading = None


def _pf(authed):
    return authed.post("/api/automation/preflight").json()


def test_everything_present_passes_and_clock_is_unknown_when_unmeasurable(authed, clock):
    _ready(authed, clock)  # mock_http has no route: the clock probe fails -> unknown, not a blocker
    pf = _pf(authed)
    assert pf["ok"] is True and pf["failures"] == [] and pf["warnings"] == []
    row = next(c for c in pf["checks"] if c["check"] == "clock_drift")
    assert row["ok"] is True and row["unknown"] is True
    assert authed.put("/api/automation", json={"mode": "SEMI"}).json()["mode"] == "SEMI"


def test_no_optional_credential_is_needed_to_arm(authed, clock):
    _ready(authed, clock)
    with authed.app.state.sessionmaker() as s:
        assert s.execute(select(ApiCredential)).first() is None  # no Discord / AI / data / GitHub key at all
    assert authed.put("/api/automation", json={"mode": "SEMI"}).status_code == 200


def test_missing_daily_bias_never_blocks_arming_but_warns(authed, clock):
    _ready(authed, clock, bias=False)
    pf = _pf(authed)
    assert pf["ok"] is True and pf["failures"] == [] and pf["warnings"] == ["bias"]
    r = authed.put("/api/automation", json={"mode": "SEMI"})
    assert r.status_code == 200 and r.json()["mode"] == "SEMI"
    assert any("Optional item missing" in n["title"] for n in authed.app.state.controller.notices)


@pytest.mark.parametrize(
    "kw,failing",
    [
        ({"calendar": False}, "calendar"),
        ({"attest": False}, "attestation"),
        ({"heartbeat": False}, "heartbeat_fresh"),
    ],
)
def test_each_mandatory_item_missing_blocks_arming(authed, clock, kw, failing):
    _ready(authed, clock, **kw)
    r = authed.put("/api/automation", json={"mode": "SEMI"})
    assert r.status_code == 409, kw
    assert failing in r.json()["detail"]["preflight"]["failures"]
    assert authed.get("/api/automation").json()["mode"] == "OFF"


def test_missing_webhook_secret_blocks(authed, clock):
    from pydantic import SecretStr

    _ready(authed, clock)
    authed.app.state.settings.webhook_secret = SecretStr("")
    pf = _pf(authed)
    assert not pf["ok"] and "webhook_secret" in pf["failures"]


def _date_header(authed, offset_s):
    return format_datetime(authed.app.state.clock.now() + timedelta(seconds=offset_s), usegmt=True)


def test_measured_clock_drift_blocks_only_when_known_over_2s(authed, clock, mock_http):
    mock_http["https://www."] = lambda req: httpx.Response(200, headers={"date": _date_header(authed, -3600)})
    _ready(authed, clock)
    pf = _pf(authed)
    assert not pf["ok"] and "clock_drift" in pf["failures"]
    row = next(c for c in pf["checks"] if c["check"] == "clock_drift")
    assert "unknown" not in row and "+3599" in str(row["detail"])
    r = authed.put("/api/automation", json={"mode": "SEMI"})
    assert r.status_code == 409
    # a good clock passes (the Date header is whole seconds, so ~0.5 s of the measurement is quantisation)
    mock_http["https://www."] = lambda req: httpx.Response(200, headers={"date": _date_header(authed, 0)})
    authed.app.state.clock_reading = None
    pf = _pf(authed)
    assert pf["ok"] is True
    row = next(c for c in pf["checks"] if c["check"] == "clock_drift")
    assert row["ok"] and "unknown" not in row
