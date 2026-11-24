from datetime import UTC, datetime, timedelta
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


def test_session_check_every_2_sessions_lucid_pro(authed, clock):  # D65
    from app.config import PayoutsCfg
    from app.models import Payout, Trade
    from app.payouts.service import _sessions_since, session_due
    from tests.conftest import PASSWORD

    thu = datetime(2026, 11, 5, 22, 10, tzinfo=UTC)  # Thu 17:10 ET
    assert session_due(thu, "17:05", None) and not session_due(thu, "17:05", "2026-11-05")
    assert not session_due(datetime(2026, 11, 7, 22, 10, tzinfo=UTC), "17:05", None)  # Saturday
    assert _sessions_since(None, thu) > 100 and _sessions_since(datetime(2026, 11, 3, 22, 0, tzinfo=UTC), thu) == 2
    clock.set(thu)
    r = authed.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    authed.headers["x-csrf-token"] = r.json()["csrf"]
    aid = authed.post("/api/accounts", json={"label": "P1", "stage": "FUNDED", "balance": "27000"}).json()["id"]
    st = authed.app.state
    h = st.rules
    pc = PayoutsCfg.model_validate(
        {**h.rules.payouts.model_dump(), "frequency": "every_n_sessions", "mode": "max_eligible"}
    )
    h.rules = h.rules.model_copy(update={"payouts": pc})
    with st.sessionmaker() as s:
        for i, pnl in enumerate((400, 300, 300)):  # cycle profit 1,000, largest day 400 = 40% → eligible
            day = datetime(2026, 11, 3 + i, 20, 0, tzinfo=UTC)
            s.add(
                Trade(
                    account_id=aid,
                    symbol="MNQ",
                    direction="LONG",
                    qty=1,
                    entry=D(1),
                    exit=D(2),
                    pnl_usd=D(pnl),
                    risk_usd=D(70),
                    opened_at=day,
                    closed_at=day,
                    trade_ref=f"P{i}",
                )
            )
        s.commit()
    made = authed.post("/api/payouts/check").json()["created"]
    assert [(m["kind"], m["amount"]) for m in made] == [("max", "900.00")]  # 27,000 − 26,100 buffer
    assert authed.post("/api/payouts/check").json()["created"] == []  # one open payout at a time
    pid = made[0]["id"]
    authed.post(f"/api/payouts/{pid}/status", json={"status": "submitted"})
    authed.post(f"/api/payouts/{pid}/status", json={"status": "processed"})
    assert authed.post("/api/payouts/check").json()["created"] == []  # < 2 sessions since the last payout
    with st.sessionmaker() as s:
        assert s.query(Payout).filter_by(account_id=aid).one().week == "2026-11-05"
    st_ = authed.get("/api/payouts/settings").json()
    assert st_["frequency"] == "every_n_sessions" and st_["mode"] == "max_eligible" and st_["min_sessions_between"] == 2
    r = authed.put(
        "/api/payouts/settings",
        json={"skim_mode": "half", "frequency": "every_n_sessions", "mode": "max_eligible", "min_pct_of_cap": "0.5"},
    )
    assert r.status_code == 200 and r.json()["min_pct_of_cap"] == "0.5"
    r = authed.put(
        "/api/payouts/settings", json={"skim_mode": "half", "frequency": "every_n_sessions", "min_pct_of_cap": None}
    )
    assert r.json()["min_pct_of_cap"] is None


# ---------- D182: on-demand payouts (CONFIRMED, Lucid help center 2026-11-24) ----------
MON = datetime(2026, 11, 23, 15, 0, tzinfo=UTC)  # Mon 10:00 ET, inside the session


def _fund_pro(authed, clock, bal="54000"):
    from tests.conftest import PASSWORD

    clock.set(MON)
    r = authed.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    authed.headers["x-csrf-token"] = r.json()["csrf"]
    aid = authed.post("/api/accounts", json={"label": "P1", "stage": "FUNDED", "balance": bal, "plan": "lucid_pro_50k"}).json()["id"]
    with authed.app.state.sessionmaker() as s:
        from app.models import Trade

        for i, (days_ago, pnl) in enumerate(((3, 500), (2, 450), (1, 400), (0, 600))):
            t = MON - timedelta(days=days_ago)
            s.add(Trade(account_id=aid, symbol="MNQ", direction="LONG", qty=1, entry=D(1), exit=D(2), pnl_usd=D(pnl), risk_usd=D(70), opened_at=t, closed_at=t, trade_ref=f"OD{i}"))
        a = s.get(Account, aid)
        a.stage_started_at = MON - timedelta(days=10)
        s.commit()
    return aid


def test_on_demand_available_amount_is_session_profit_limited(authed, clock):
    aid = _fund_pro(authed, clock)
    j = authed.get("/api/payouts/on-demand").json()
    assert j["status"] == "CONFIRMED (Lucid help center)" and "until the end of the trading day" in j["pause_rule"]
    row = [x for x in j["accounts"] if x["account_id"] == aid][0]
    assert row["available"], (row["reason"], row["message"])
    assert row["amount"] == "600.00" and row["net"] == "540.00" and row["limited_by"] == "session_profit"
    assert not row["paused"] and row["dll_enabled"]


def test_on_demand_blocked_by_hedging_violation_and_dll_off(authed, clock):
    aid = _fund_pro(authed, clock)
    assert authed.patch(f"/api/accounts/{aid}", json={"hedging_violation": True}).status_code == 200
    row = [x for x in authed.get("/api/payouts/on-demand").json()["accounts"] if x["account_id"] == aid][0]
    assert not row["available"] and row["reason"] == "HEDGING_VIOLATION" and row["hedging_violation"]
    assert authed.post(f"/api/payouts/on-demand/{aid}/plan").status_code == 409
    assert authed.get("/api/accounts").json()["accounts"][0]["hedging_violation"] is True
    authed.patch(f"/api/accounts/{aid}", json={"hedging_violation": False})
    with authed.app.state.sessionmaker() as s:
        s.get(Account, aid).dll_enabled = False
        s.commit()
    row = [x for x in authed.get("/api/payouts/on-demand").json()["accounts"] if x["account_id"] == aid][0]
    assert row["reason"] == "DLL_OFF"


def test_on_demand_request_pauses_account_until_end_of_trading_day_and_is_never_auto_submitted(authed, clock):
    from app.automation.state import payout_pending

    aid = _fund_pro(authed, clock)
    made = authed.post(f"/api/payouts/on-demand/{aid}/plan")
    assert made.status_code == 200 and made.json()["kind"] == "ondem" and made.json()["status"] == "ready"
    pid = made.json()["id"]
    with authed.app.state.sessionmaker() as s:  # planned only: nothing was sent, trading is NOT blocked yet
        assert not payout_pending(s, s.get(Account, aid), clock.now())
    assert authed.post(f"/api/payouts/on-demand/{aid}/plan").status_code == 409  # one open request at a time
    assert authed.post(f"/api/payouts/{pid}/status", json={"status": "submitted"}).status_code == 200  # the user requested it
    with authed.app.state.sessionmaker() as s:
        a = s.get(Account, aid)
        assert payout_pending(s, a, clock.now())
        assert authed.post(f"/api/payouts/{pid}/status", json={"status": "processed"}).status_code == 200
        assert payout_pending(s, a, clock.now())  # processed within minutes, but trading stays paused until the end of the day
        assert payout_pending(s, a, MON + timedelta(hours=5))  # still the same session (15:00 ET)
        assert not payout_pending(s, a, MON + timedelta(hours=9))  # 19:00 ET = the next session
        assert not payout_pending(s, a)  # without a clock only an open "submitted" payout counts
    assert [x for x in authed.get("/api/payouts/on-demand").json()["accounts"] if x["account_id"] == aid][0]["reason"] == "PAUSED_UNTIL_EOD"


def test_pretrade_blocks_new_entry_after_payout_request(authed, clock):
    """The controller feeds payout_pending(now) into the pre-trade check: PAYOUT_PENDING blocks the entry."""
    aid = _fund_pro(authed, clock)
    pid = authed.post(f"/api/payouts/on-demand/{aid}/plan").json()["id"]
    authed.post(f"/api/payouts/{pid}/status", json={"status": "submitted"})
    authed.post(f"/api/payouts/{pid}/status", json={"status": "processed"})
    from app.automation import state as stt

    with authed.app.state.sessionmaker() as s:
        assert stt.payout_pending(s, s.get(Account, aid), authed.app.state.clock.now())
