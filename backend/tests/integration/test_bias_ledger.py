"""D55 calibration ledger: AI calls scored against the real session; advisory until proven; /api/strategies."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal as D

from app.bias import ledger as L
from app.bias.policy import Policy
from app.clock import ET
from app.models import Bar, BiasDecision


def _day_bars(s, d: date, up: bool):
    o, c = D(20000), D(20100) if up else D(19900)
    for hh, mm, px in ((9, 31, o), (16, 0, c)):
        s.add(
            Bar(
                symbol="MNQ",
                tf="1",
                close_time=datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET),
                o=o,
                h=max(o, c),
                l=min(o, c),
                c=px,
                v=D(1),
                source="tradingview",
            )
        )


def _call(s, d: date, label: str):
    s.add(BiasDecision(session_date=d, proxy="QQQ", raw_rating=label, mapped="NEUTRAL", reasoning="", version=""))


def test_parse_label():
    assert L.parse_label("BUY·VT SHORT 85") == ("BUY", "SHORT", 85)
    assert L.parse_label("HOLD") == ("HOLD", None, None)
    assert L.parse_label("") == ("", None, None)


def test_ledger_scores_and_proves(client):
    today = date(2026, 11, 9)
    with client.app.state.sessionmaker() as s:
        days = [today - timedelta(days=i) for i in range(1, 41)]
        for i, d in enumerate(days):
            _day_bars(s, d, up=True)
            # 36 right calls, 4 wrong: strong BUY + VT LONG 80 on up days, SELL on 4 of them
            _call(s, d, "BUY·VT LONG 80" if i % 10 else "SELL·VT SHORT 80")
        _call(s, today, "SELL·VT SHORT 90")  # today: strong, both tools agree SHORT
        s.commit()
        st = L.status(s, "QQQ", "MNQ", today, 0.70)
        assert st["stats"]["n"] == 40 and st["stats"]["hit_rate"] == 0.9 and st["state"] == "PROVEN"
        assert st["badge"] == "MAY BLOCK (proven)"
        assert L.may_block(s, "QQQ", "MNQ", today, +1, 0.70) == "BIAS_PROVEN_AGAINST"  # long blocked
        assert L.may_block(s, "QQQ", "MNQ", today, -1, 0.70) is None  # short agrees with the call
        assert L.may_block(s, "QQQ", "MNQ", today, +1, 0.95) is None  # not proven at 95%


def test_ledger_warmup_and_unscored_days(client):
    today = date(2026, 11, 9)
    with client.app.state.sessionmaker() as s:
        _call(s, today - timedelta(days=1), "BUY")  # no bars that day → not scored
        _call(s, today, "SELL·VT SHORT 90")
        s.commit()
        st = L.status(s, "QQQ", "MNQ", today, 0.70)
        assert st["state"] == "WARMUP" and st["badge"] == "ADVISORY" and st["stats"]["n"] == 0
        assert L.may_block(s, "QQQ", "MNQ", today, +1, 0.70) is None
        assert L.may_block(s, "QQQ", "MNQ", today - timedelta(days=5), +1, 0.70) is None  # no call that day
        assert L.proven(L.LedgerStats(30, 0.8, 0.30, 0.75), Policy(True), 0.7) is False  # Brier too high


def test_strategies_endpoint(authed):
    r = authed.get("/api/strategies")
    assert r.status_code == 200, r.text
    body = r.json()
    keys = [x["key"] for x in body["strategies"]]
    assert keys == ["pm_fade", "noise", "ai_bias", "ai_duo", "noise_ai_split", "order_flow"]
    noise = body["strategies"][1]
    assert noise["win_pct"] == 45.0 and noise["pro25k_pass_pct"] == 56.9 and noise["setting"] == "strategy.noise"
    assert body["noise_warmup"]["ready"] is False and body["noise_warmup"]["needed"] == 10
    # the button saves through versioned My Settings
    r = authed.put("/api/risk/settings", json={"changes": {"strategy.noise": True}, "note": "test"})
    assert r.status_code == 200, r.text
    assert authed.get("/api/strategies").json()["strategies"][1]["enabled"] is True
    r = authed.put("/api/risk/settings", json={"changes": {"strategy.ai_bias": True}, "note": "test"})
    assert r.status_code == 200, r.text
    ai = authed.get("/api/strategies").json()["strategies"][2]
    assert ai["enabled"] is True and ai["win_pct"] is None and ai["status"] == "UNVERIFIED"


def test_ai_threshold_from_config_and_no_generic_gate_chain(authed):
    """The AI threshold defaults to 70%. D106: the generic gate chain moved to the per-strategy gates endpoint."""
    d = authed.get("/api/strategies").json()
    assert "gate_chain" not in d and "lunqfx_flags" not in d
    assert d["ai_ledger"][0]["required_accuracy"] == 0.7
