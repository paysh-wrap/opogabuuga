"""D106: per-strategy gates view (read-only) — pure helpers + the endpoint."""

from datetime import UTC, datetime, timedelta

from app import audit
from app.api.strategy_gates import LUCID, describe, evaluate, lucid_rules
from app.clock import FixedClock
from app.models import Signal

T0 = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)


def _by_key(r):
    return {s["key"]: s for s in describe(r)}


def test_each_strategy_has_its_own_gates_and_no_lunqfx(loaded_rules):
    rows = _by_key(loaded_rules.rules)
    assert set(rows) == {"noise", "pm_fade", "open_drive", "ai_bias", "ai_duo", "order_flow"}
    ids = {k: [g["id"] for g in v["gates"]] for k, v in rows.items()}
    assert "BREAKOUT" in ids["noise"] and "VWAP_TRAIL" in ids["noise"] and "FLAT" in ids["noise"]
    assert ids["order_flow"][:1] == ["ENVIRONMENT"] and "CONFIRMATION" in ids["order_flow"]
    assert "PLAN" in ids["order_flow"] and "PULLBACK" in ids["ai_duo"] and "TARGET" in ids["pm_fade"]
    assert ids["noise"] != ids["order_flow"]
    for v in rows.values():  # every strategy hands over to the shared Lucid rules exactly once
        assert ids[v["key"]].count(LUCID) == 1
        assert not any(g["id"].startswith(("G2", "G3", "G4", "G5", "G6", "G7")) for g in v["gates"])
    # off-by-default filters are not listed
    assert "STRUCTURE" not in ids["noise"]


def test_values_come_from_config(loaded_rules):
    base = loaded_rules.rules
    of = base.strategy.order_flow_cfg
    strat = base.strategy.model_copy(
        update={
            "noise_cfg": base.strategy.noise_cfg.model_copy(update={"max_entries_per_day": 7}),
            "order_flow_cfg": of.model_copy(update={"ar": of.ar.model_copy(update={"path_filter": False})}),
        }
    )
    r = base.model_copy(update={"strategy": strat})
    rows = _by_key(r)
    me = next(g for g in rows["noise"]["gates"] if g["id"] == "MAX_ENTRIES")
    assert "7" in me["text"]
    assert "PATH" not in [g["id"] for g in rows["order_flow"]["gates"]]


def test_lucid_rules_block(loaded_rules):
    ids = [g["id"] for g in lucid_rules(loaded_rules.rules)]
    assert ids == ["NEWS", "DLL_MLL", "CONSISTENCY", "HEDGE", "KILL", "ONE_POSITION", "FLAT_TIMES", "PREFLIGHT"]


def test_evaluate_statuses(loaded_rules):
    gates = _by_key(loaded_rules.rules)["order_flow"]["gates"]
    none = evaluate(gates, None)
    assert all(g["status"] is None for g in none["gates"]) and none["last"] is None
    ok = evaluate(gates, {"status": "PASS", "code": None})
    assert all(g["status"] == "PASS" for g in ok["gates"] if g["kind"] == "entry")
    assert all(g["status"] is None for g in ok["gates"] if g["kind"] == "exit")
    sk = {g["id"]: g["status"] for g in evaluate(gates, {"status": "SKIP", "code": "OF_NO_CONFIRM"})["gates"]}
    assert sk["ENVIRONMENT"] == "PASS" and sk["CONFIRMATION"] == "FAIL" and sk["PLAN"] == "NOT_REACHED"
    hl = evaluate(gates, {"status": "SKIP", "code": "HEDGE_LOCK"})
    st = {g["id"]: g["status"] for g in hl["gates"]}
    assert hl["lucid_code"] == "HEDGE_LOCK" and st[LUCID] == "FAIL" and st["DAILY_CAP"] == "PASS"
    unknown = evaluate(gates, {"status": "SKIP", "code": "DRAWDOWN_TOO_DEEP"})
    assert unknown["lucid_code"] == "DRAWDOWN_TOO_DEEP"


def test_endpoint_live_status(authed):
    assert authed.get("/api/strategy-gates").status_code == 200
    with authed.app.state.sessionmaker() as s:
        s.add(
            Signal(
                symbol="MNQ",
                profile="TIGHT",
                direction="LONG",
                model_key="MNQ-NOISE-2026-11-05-1",
                bar_time=T0,
                status="SKIP",
                passed=False,
                skip_reason="NEWS_BLACKOUT",
                features={},
            )
        )
        s.add(
            Signal(
                symbol="MNQ",
                profile="TIGHT",
                direction="SHORT",
                model_key="MNQ-OF-2026-11-05-1-SHORT",
                bar_time=T0,
                status="PASS",
                passed=True,
                features={},
            )
        )
        audit.record(
            s,
            FixedClock(T0 + timedelta(minutes=5)),
            "engine",
            "order_flow.skip",
            "MNQ-OF-2026-11-05",
            {"code": "OF_COMPRESSION", "layer": "ENVIRONMENT", "direction": "LONG"},
        )
        s.commit()
    d = authed.get("/api/strategy-gates").json()
    rows = {x["key"]: x for x in d["strategies"]}
    assert rows["noise"]["lucid_code"] == "NEWS_BLACKOUT"
    assert rows["noise"]["last"]["code"] == "NEWS_BLACKOUT"
    of = {g["id"]: g["status"] for g in rows["order_flow"]["gates"]}
    assert rows["order_flow"]["last"]["source"] == "audit" and of["ENVIRONMENT"] == "FAIL"
    assert rows["ai_duo"]["last"] is None
    assert d["lucid_rules"][0]["id"] == "NEWS"
    assert all("codes" in g for g in d["lucid_rules"])


def test_endpoint_needs_login(client):
    assert client.get("/api/strategy-gates").status_code == 401
