"""§24.2 Trade Replay API."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from app.api.replay import fractal_from_events
from app.models import Bar, Event, Signal, SignalGate, Trade, TradePlanRow

T0 = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
C1 = 1_762_354_800_000


def test_fractal_snapshot_is_per_model_and_latest_wins():
    p = [
        {"fractal": {"c1_time_ms": C1, "c1_high": 10, "c1_low": 5, "t2": 20}},
        {"fractal": {"c1_time_ms": 999, "c1_high": 99}},
        {"fractal": {"c1_time_ms": C1, "cisd_level": 7, "t2": 21}},
        {"mso": {}},
    ]
    assert fractal_from_events(p, C1) == {"c1_time_ms": C1, "c1_high": 10, "c1_low": 5, "t2": 21, "cisd_level": 7}
    assert fractal_from_events([], C1) is None


def test_replay_and_trade_list(authed):
    aid = authed.post("/api/accounts", json={"label": "A", "stage": "EVAL"}).json()["id"]
    with authed.app.state.sessionmaker() as s:
        sig = Signal(
            symbol="MGC",
            profile="STD",
            direction="LONG",
            model_key=f"MGC-STD-{C1}",
            bar_time=T0,
            score=D(72),
            passed=True,
            status="PASS",
            features={"score_items": {"cisd": "25"}},
        )
        s.add(sig)
        s.flush()
        s.add(
            TradePlanRow(
                signal_id=sig.id, direction="LONG", entry=D(100), stop=D(95), take_profit=D(110), risk_pts=D(5), rr=D(2)
            )
        )
        s.add(
            SignalGate(signal_id=sig.id, gate="G1", passed=True, detail={"code": "OK", "hard": False, "detail": None})
        )
        for i in range(5):
            s.add(
                Bar(
                    symbol="MGC",
                    tf="1",
                    close_time=T0 + timedelta(minutes=i),
                    o=D(100),
                    h=D(101),
                    l=D(99),
                    c=D(100),
                    v=D(1),
                    source="tv",
                )
            )
        s.add(Bar(symbol="MGC", tf="5", close_time=T0, o=D(1), h=D(1), l=D(1), c=D(1), v=D(1), source="tv"))
        s.add(
            Event(
                event_id="e1",
                symbol="MGC",
                profile="STD",
                event="MODEL_CONFIRMED",
                direction="LONG",
                bar_time=T0,
                payload={"fractal": {"c1_time_ms": C1, "c1_high": 102, "c1_low": 98}},
            )
        )
        s.add(
            Event(
                event_id="e2",
                symbol="MGC",
                profile="STD",
                event="MSO_CHOCH",
                direction="LONG",
                bar_time=T0,
                payload={"mso": {"confirm_time_ms": 123}},
            )
        )
        s.add(
            Event(
                event_id="e3", symbol="MGC", profile="STD", event="MSO_BOS", direction="LONG", bar_time=T0, payload={}
            )
        )
        s.add(
            Trade(
                account_id=aid,
                signal_id=sig.id,
                symbol="MGC",
                direction="LONG",
                qty=1,
                entry=D(100),
                exit=D(110),
                risk_usd=D(50),
                pnl_usd=D(98),
                net_r=D("1.9"),
                opened_at=T0,
                closed_at=T0 + timedelta(minutes=3),
                resolution="TP",
            )
        )
        s.add(Trade(account_id=aid, symbol="MGC", direction="SHORT", qty=1, entry=D(100), risk_usd=D(50), opened_at=T0))
        s.commit()
    lst = authed.get("/api/trades").json()["trades"]
    assert len(lst) == 2
    tid = next(x["id"] for x in lst if x["closed_at"])
    r = authed.get(f"/api/trades/{tid}/replay").json()
    assert len(r["bars"]) == 5 and r["plan"]["take_profit"] == "110" and r["fractal"]["c1_high"] == 102
    assert 123 in [m["time_ms"] for m in r["mso_events"]] and len(r["mso_events"]) == 2
    assert r["gates"][0]["code"] == "OK" and r["score"]["items"] == {"cisd": "25"}
    manual = next(x["id"] for x in lst if x["closed_at"] is None)
    m = authed.get(f"/api/trades/{manual}/replay").json()
    assert m["plan"] is None and m["signal"] is None and m["trade"]["closed_ms"] is None
    assert authed.get("/api/trades/9999/replay").status_code == 404
