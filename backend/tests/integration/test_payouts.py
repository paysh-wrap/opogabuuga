from datetime import UTC, datetime
from decimal import Decimal as D

from app.models import Account
from app.payouts.service import due

FRI = datetime(2026, 11, 6, 22, 10, tzinfo=UTC)  # Fri 17:10 ET


def test_due_once_per_week():
    assert due(FRI, "Fri 17:05", None)
    assert not due(FRI, "Fri 17:05", "2026-W45")
    assert not due(datetime(2026, 11, 6, 21, 0, tzinfo=UTC), "Fri 17:05", None)  # 16:00 ET


def test_weekly_check_submit_blocks_then_processed_debits(authed, clock):
    from tests.conftest import PASSWORD

    clock.set(FRI)
    r = authed.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    authed.headers["x-csrf-token"] = r.json()["csrf"]
    r = authed.post("/api/accounts", json={"label": "F1", "stage": "FUNDED", "balance": "28700"})
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    authed.post("/api/accounts", json={"label": "F2", "stage": "FUNDED"})  # 25,000 → nothing to pay
    ctl = authed.app.state.controller
    with authed.app.state.sessionmaker() as s:  # profit since last payout (none yet) must be ≥ $1
        from app.models import Trade

        s.add(
            Trade(
                account_id=aid,
                symbol="MNQ",
                direction="LONG",
                qty=1,
                entry=D(1),
                exit=D(2),
                pnl_usd=D(600),
                risk_usd=D(70),
                opened_at=FRI,
                closed_at=FRI,
                trade_ref="X1",
            )
        )
        s.commit()
    made = authed.post("/api/payouts/check").json()["created"]
    assert [(m["label"], m["kind"], m["amount"]) for m in made] == [("F1", "sweep", "600.00")]
    assert authed.post("/api/payouts/check").json()["created"] == []  # once per week
    pid = made[0]["id"]
    assert authed.post(f"/api/payouts/{pid}/status", json={"status": "processed"}).status_code == 409
    assert authed.post(f"/api/payouts/{pid}/status", json={"status": "submitted"}).status_code == 200
    with authed.app.state.sessionmaker() as s:
        from app.automation.state import payout_pending

        assert payout_pending(s, s.get(Account, aid))  # trading blocked while pending
    assert authed.post(f"/api/payouts/{pid}/status", json={"status": "processed"}).json()["status"] == "processed"
    ext = authed.get("/api/accounts").json()["accounts"]
    bal = {x["label"]: x["balance"] for x in authed.get("/api/positions").json()["accounts"]}
    assert D(bal["F1"]) == D(28100) and ext
    assert ctl.notices and "Payout ready" in [n["title"] for n in ctl.notices]


def test_calendar_api(authed):
    r = authed.get("/api/calendar").json()
    assert r["loaded"] is False and r["events"] == []  # no data → no trading
