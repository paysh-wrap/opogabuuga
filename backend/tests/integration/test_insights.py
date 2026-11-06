"""§24 insights: Today plan + daily P&L calendar + skip report."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal as D

from app.engine.filters import NewsEvent
from app.models import Cooldown, DailyAccountStats, Signal, Trade

AT = datetime(2026, 11, 5, 13, 30, tzinfo=UTC)


def _acct(authed, label, stage="EVAL"):
    return authed.post("/api/accounts", json={"label": label, "stage": stage}).json()["id"]


def _trade(authed, aid, pnl, closed):
    with authed.app.state.sessionmaker() as s:
        s.add(Trade(account_id=aid, symbol="MNQ", direction="LONG", qty=1, entry=D(1), exit=D(2), pnl_usd=D(pnl),
                    risk_usd=D(50), opened_at=closed - timedelta(minutes=5), closed_at=closed))
        s.commit()


def test_today_plan_blackouts_from_rules(authed):
    authed.app.state.calendar = lambda d: [NewsEvent(AT, "CPI")]
    p = authed.get("/api/today/plan").json()
    r = authed.app.state.rules.rules
    n = p["news"][0]
    before, flat = r.internal.no_entry_before_news_min, r.internal.news_flatten_before_min
    assert datetime.fromisoformat(n["no_entry_from"]) == AT - timedelta(minutes=before)
    assert datetime.fromisoformat(n["flatten_at"]) == AT - timedelta(minutes=flat)
    assert datetime.fromisoformat(n["no_entry_until"]) > AT
    assert p["news_rules"]["no_entry_before_min"] == before
    assert p["calendar_loaded"] and p["attested_today"] is False and p["preflight"] is None
    assert p["windows"] and p["windows"][0]["label"] == "Trading hours"


def test_today_plan_calendar_missing_accounts_pace_cooldown_preflight(authed):
    authed.app.state.calendar = lambda d: None
    aid = _acct(authed, "E1")
    authed.patch(f"/api/accounts/{aid}", json={"armed": True})
    sess = date(2026, 11, 5)
    with authed.app.state.sessionmaker() as s:
        s.add(Cooldown(symbol="MNQ", profile="TIGHT", streak=3, until_session=sess + timedelta(days=3)))
        s.add(DailyAccountStats(account_id=aid, session_date=sess, day_profit=D(100)))
        s.add(DailyAccountStats(account_id=aid, session_date=sess - timedelta(days=1), day_profit=D(-5)))
        s.commit()
    _trade(authed, aid, "100", AT + timedelta(hours=3))  # after the stage started (15:00Z)
    authed.post("/api/automation/preflight")
    authed.post("/api/attestation", json={"confirm": True})
    p = authed.get("/api/today/plan").json()
    assert p["calendar_loaded"] is False and p["news"] == []
    assert [a["label"] for a in p["accounts"]] == ["E1"]
    pace = p["eval_pace"][0]
    assert D(pace["profit"]) == 100
    assert pace["profitable_days"] == 1 and pace["min_profitable_days"] >= 1
    assert p["cooldowns"] and p["cooldowns"][0]["symbol"] == "MNQ"
    assert p["preflight"]["at"] and "ok" in p["preflight"]
    assert p["attested_today"] is True


def test_intraday_windows_listed_when_configured(authed):
    r = authed.app.state.rules.rules
    object.__setattr__(r.internal, "intraday_windows", [("07:00", "10:00")])
    try:
        labels = [w["label"] for w in authed.get("/api/today/plan").json()["windows"]]
    finally:
        object.__delattr__(r.internal, "intraday_windows")
    assert "Intraday mode (best hours)" in labels


def test_pnl_daily_household_accounts_weeks_eval(authed):
    a = _acct(authed, "E1")
    f = _acct(authed, "F1", "FUNDED")
    _trade(authed, a, "300", AT)
    _trade(authed, a, "-50", AT + timedelta(minutes=10))
    _trade(authed, a, "100", AT + timedelta(days=1))
    _trade(authed, f, "40", AT)
    with authed.app.state.sessionmaker() as s:  # open trade ignored
        s.add(Trade(account_id=a, symbol="MNQ", direction="LONG", qty=1, entry=D(1), risk_usd=D(5), opened_at=AT))
        s.commit()
    d = authed.get("/api/pnl/daily").json()
    assert D(d["household"]["total"]) == 390
    assert {x["date"]: D(x["pnl"]) for x in d["household"]["days"]}["2026-11-05"] == 290
    assert len(d["household"]["weeks"]) == 1 and D(d["household"]["weeks"][0]["pnl"]) == 390
    ev = next(x for x in d["accounts"] if x["id"] == a)["eval"]
    assert ev["largest_day"] == "2026-11-05" and D(ev["largest_pnl"]) == 250
    assert D(ev["cap"]) == D("500") and D(ev["largest_pct"]) > 0
    assert "eval" not in next(x for x in d["accounts"] if x["id"] == f)
    only = authed.get(f"/api/pnl/daily?account_id={f}").json()
    assert [x["id"] for x in only["accounts"]] == [f] and D(only["household"]["total"]) == 40


def test_pnl_daily_negative_eval_has_no_pct(authed):
    a = _acct(authed, "E1")
    _trade(authed, a, "-80", AT)
    ev = authed.get("/api/pnl/daily").json()["accounts"][0]["eval"]
    assert ev["largest_pct"] is None


def test_insights_require_auth(client):
    assert client.get("/api/pnl/daily").status_code == 401
    assert client.get("/api/today/plan").status_code == 401


def test_skips_multi_session_average(authed):
    with authed.app.state.sessionmaker() as s:
        for i, (days, reason) in enumerate(
            [(0, "RR_BELOW_MIN"), (0, "RR_BELOW_MIN"), (1, "RR_BELOW_MIN"), (2, "OUTSIDE_WINDOW")]
        ):
            s.add(Signal(symbol="MNQ", profile="STD", direction="LONG", model_key=f"k{i}", status="SKIP",
                         skip_reason=reason, bar_time=AT - timedelta(days=days)))
        s.commit()
    r = authed.get("/api/signals/skips?date=2026-11-05").json()
    assert r["counts"] == {"RR_BELOW_MIN": 2} and r["sessions_in_avg"] == 2
    assert r["avg_20"]["RR_BELOW_MIN"] == 0.5
