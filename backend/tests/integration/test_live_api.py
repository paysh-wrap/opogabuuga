def test_live_checklist_defaults_to_paper(authed):
    r = authed.get("/api/live").json()
    assert r["live"] is False and r["toggle_on"] is False
    checks = {c["check"]: c["ok"] for c in r["checklist"]}
    assert checks["server_allows_live"] is False and checks["broker_reads_back"] is True  # sim reads back
    assert checks["paper_sessions"] is False and "indicator_parity" not in checks  # B1: dead item replaced
    assert r["readiness"] == {"mode": "paper_sessions", "sessions": 0, "needed": 20}


def test_live_toggle_needs_phrase_and_off_is_one_click(authed):
    assert authed.put("/api/live", json={"enabled": True, "confirm": "yes"}).status_code == 422
    r = authed.put("/api/live", json={"enabled": True, "confirm": "I ACCEPT LIVE RISK"}).json()
    assert r["toggle_on"] is True and r["live"] is False  # still blocked by the rest of the checklist
    assert authed.put("/api/live", json={"enabled": False}).json()["toggle_on"] is False


def test_live_needs_login(client):
    assert client.get("/api/live").status_code == 401


def _paper_trade(st, at, strategy="NOISE", mode="PAPER"):
    from decimal import Decimal as D

    from app.models import Signal, Trade

    with st.sessionmaker() as s:
        sig = Signal(symbol="MNQ", profile="TIGHT", direction="LONG", model_key=f"k{at.isoformat()}{strategy}",
                     bar_time=at, status="PASS", passed=True, features={"strategy": strategy},
                     updated_at=at)  # fmt: skip
        s.add(sig)
        s.flush()
        s.add(Trade(account_id=_acct(s), signal_id=sig.id, symbol="MNQ", direction="LONG", qty=1, entry=D(1),
                    risk_usd=D(1), opened_at=at, closed_at=at, mode=mode, pnl_usd=D(1)))  # fmt: skip
        s.commit()


def _acct(s):
    from decimal import Decimal as D

    from app.models import Account

    a = s.query(Account).first()
    if a is None:
        a = Account(label="p", broker_account_id="SIM-T", stage="EVAL", drawdown_type="eod", starting_balance=D(25000))
        s.add(a)
        s.flush()
    return a.id


def test_paper_sessions_count_clean_completed_sessions_of_active_strategies(authed, clock):
    """B1: one clean session per day with a closed PAPER trade of a strategy that is ON; an error banner, a LIVE
    trade, an inactive strategy or today's unfinished session do not count."""
    from datetime import timedelta

    from app.models import Notification

    st = authed.app.state
    h = st.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"noise": True})})
    now = clock.now()
    for d in range(1, 6):
        _paper_trade(st, now - timedelta(days=d))
    _paper_trade(st, now - timedelta(days=6), strategy="ORDER_FLOW")  # strategy OFF → not counted
    _paper_trade(st, now - timedelta(days=7), mode="LIVE")  # not paper
    _paper_trade(st, now)  # today: not completed
    with st.sessionmaker() as s:
        s.add(Notification(level="error", title="Order failed", created_at=now - timedelta(days=2)))
        s.add(Notification(level="warn", title="just a warning", created_at=now - timedelta(days=3)))
        s.commit()
    r = authed.get("/api/live").json()
    assert r["readiness"]["sessions"] == 4
    item = next(c for c in r["checklist"] if c["check"] == "paper_sessions")
    assert item["ok"] is False and item["detail"].startswith("4/20")


def test_readiness_toggle_off_skips_one_item_and_is_audited(authed):
    from app.models import AuditLog

    assert authed.put("/api/live/readiness", json={"mode": "maybe"}).status_code == 422
    r = authed.put("/api/live/readiness", json={"mode": "off"}).json()
    item = next(c for c in r["checklist"] if c["check"] == "paper_sessions")
    assert r["readiness"]["mode"] == "off" and item["ok"] is True and item["skipped"] is True
    assert r["live"] is False  # every other gate still applies (server flag, typed phrase, ...)
    st = authed.app.state
    with st.sessionmaker() as s:
        row = s.query(AuditLog).filter_by(action="live.readiness_check").one()
        assert row.payload == {"from": "paper_sessions", "to": "off"}
    back = authed.put("/api/live/readiness", json={"mode": "paper_sessions"}).json()
    assert back["readiness"]["mode"] == "paper_sessions"
    assert next(c for c in back["checklist"] if c["check"] == "paper_sessions")["ok"] is False
