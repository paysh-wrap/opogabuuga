"""D98 Order Flow chart API (display only, ESTIMATED from bars)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from app import audit
from app.api.orderflow import AR_KEYS, session_of
from app.clock import FixedClock
from app.models import Bar, Event

# 2026-11-05 14:31 UTC = 09:31 ET (session 2026-11-05); prior session 2026-11-04
T0 = datetime(2026, 11, 5, 14, 31, tzinfo=UTC)


def test_session_of_globex_day():
    assert session_of(datetime(2026, 11, 5, 22, 59, tzinfo=UTC)).isoformat() == "2026-11-05"  # 17:59 ET
    assert session_of(datetime(2026, 11, 5, 23, 1, tzinfo=UTC)).isoformat() == "2026-11-06"  # 18:01 ET


def test_empty_state_and_bad_symbol(authed):
    r = authed.get("/api/orderflow?symbol=MNQ").json()
    assert r["bars"] == [] and r["estimated"] is True and r["source"] == "estimated"
    assert "ESTIMATED" in r["note"]
    assert authed.get("/api/orderflow?symbol=ES").status_code == 422
    assert authed.get("/api/orderflow?symbol=MGC&session=2026-01-01").json()["bars"] == []


def test_orderflow_session_profile_prior_and_markers(authed):
    with authed.app.state.sessionmaker() as s:
        for day, base in ((T0 - timedelta(days=1), 20000), (T0, 20010)):
            for i in range(5):
                p = D(base + i)
                s.add(
                    Bar(
                        symbol="MNQ",
                        tf="1",
                        close_time=day + timedelta(minutes=i),
                        o=p,
                        h=p + 2,
                        l=p - 1,
                        c=p + 1,
                        v=D(30),
                        source="tv",
                    )
                )
        s.add(
            Event(
                event_id="of-1",
                symbol="MNQ",
                profile="TIGHT",
                event="ORDER_FLOW",
                direction="LONG",
                bar_time=T0 + timedelta(minutes=2),
                payload={"order_flow": {"kind": "ABSORPTION", "env": "EXPANSION", "delta_source": "real"}},
            )
        )
        audit.record(
            s, FixedClock(T0), "engine", "order_flow.skip", "MNQ-OF-2026-11-05",
            {"code": "OF_COMPRESSION", "detail": "x", "layer": "ENVIRONMENT", "direction": "LONG",
             "env": "COMPRESSION"},
        )  # fmt: skip
        s.commit()
    r = authed.get("/api/orderflow?symbol=MNQ").json()
    assert r["session"] == "2026-11-05" and r["sessions"] == ["2026-11-04", "2026-11-05"]
    assert len(r["bars"]) == 5 and r["row_size"] == "1.00"
    b = r["bars"][0]
    assert b["source"] == "estimated" and b["levels"] and D(b["delta"]) > 0
    assert D(r["bars"][-1]["cvd"]) == sum(D(x["delta"]) for x in r["bars"])
    assert b["zone"] == "premium"  # above the prior session's value area
    assert r["profile"]["poc"] is not None and r["prior"]["session"] == "2026-11-04" and r["prior"]["vah"]
    assert r["round_levels"] == []
    assert r["signals"] == [
        {
            "time_ms": int((T0 + timedelta(minutes=2)).timestamp() * 1000),
            "kind": "ABSORPTION",
            "label": "Absorption",
            "direction": "LONG",
            "ar": {**dict.fromkeys(AR_KEYS), "env": "EXPANSION", "delta_source": "real"},
        }
    ]
    # D101: the four AR layers (from the plan file) and the alerts the engine refused, with their reason codes
    assert [x["key"] for x in r["ar"]["layers"]] == ["ENVIRONMENT", "LOCATION", "PATH", "CONFIRMATION"]
    assert r["ar"]["paper_only"] is True and r["ar"]["verified"] is False
    sk = r["skips"][0]
    assert (sk["code"], sk["layer"], sk["direction"], sk["ar"]["env"]) == (
        "OF_COMPRESSION",
        "ENVIRONMENT",
        "LONG",
        "COMPRESSION",
    )
    assert "compression" in sk["label"]
    old = authed.get("/api/orderflow?symbol=MNQ&session=2026-11-04").json()
    assert len(old["bars"]) == 5 and old["prior"] is None and old["bars"][0]["zone"] == "unknown"
