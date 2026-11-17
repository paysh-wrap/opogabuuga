"""D151: the TradingAgents advisor hook in front of the D142-D150 strategies."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from decimal import Decimal as D

import pytest
from pydantic import ValidationError

from app.bias import ledger
from app.clock import FixedClock
from app.config import ADVISED_MODES, AdvisorCfg
from app.engine.trade_plan import Direction
from app.models import AuditLog, BiasDecision
from app.signals import strategy_service as SS

AT = datetime(2026, 10, 13, 14, 52, tzinfo=UTC)
RUNNERS = {
    "JJ_FPT": SS.run_jj_fpt, "GALA_PA": SS.run_gala_pa, "CONTI_ORB": SS.run_conti_orb,
    "CONTI_VWAP": SS.run_conti_vwap, "OKALA_8020": SS.run_okala_8020, "BRUNI_STRUCTURE": SS.run_bruni_structure,
    "CANDACE_ICT": SS.run_candace_ict, "ORDER_FLOW_AUCTION": SS.run_order_flow_auction,
}  # fmt: skip


def _rules(base, **kw):
    return base.model_copy(update={"strategy": base.strategy.model_copy(update={"advisor": AdvisorCfg(**kw)})})


def _proven(monkeypatch, yes: bool):
    st = {"n": 40, "hit_rate": 0.85, "brier": 0.2, "wilson_lb": 0.75 if yes else 0.5}
    monkeypatch.setattr(ledger, "ledger", lambda *_a, **_k: {"stats": st})


def _call(s, rating="SELL"):
    s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating=rating, mapped="x", version="x"))
    s.flush()


_N = iter(range(10**6))


def _sig(s, rules, mode, direction=Direction.LONG, ok=True):
    return SS._new_signal(
        s, FixedClock(AT), symbol="MNQ", key=f"MNQ-{mode}-{next(_N)}", direction=direction, at=AT,
        gate=(ok, "OK" if ok else "OUTSIDE_WINDOW", ""), features={"x": 1},
        plan=(mode, D(100), D(99), D(102), D(1), D(2)), rules=rules,
    )  # fmt: skip


def test_every_runner_passes_rules_to_the_hook():
    assert set(RUNNERS) == set(ADVISED_MODES)
    for mode, fn in RUNNERS.items():
        src = inspect.getsource(fn)
        assert f'"{mode}"' in src and "rules=rules" in src, mode


@pytest.mark.parametrize("mode", ADVISED_MODES)
def test_advisory_records_and_never_blocks(client, loaded_rules, monkeypatch, mode):
    _proven(monkeypatch, True)
    with client.app.state.sessionmaker() as s:
        _call(s)
        sig = _sig(s, loaded_rules.rules, mode)  # default mode ADVISORY
        a = sig.features["advisor"]
        assert sig.status == "PASS" and a["verdict"] == "DISAGREE" and a["label"] == "SELL"
        assert a["ledger_proven"] is True and a["blocks"] is False and a["prob_up"] < 0.5
        assert s.query(AuditLog).filter_by(action="signal.advisor").count() == 1


@pytest.mark.parametrize("mode", ADVISED_MODES)
def test_gate_blocks_only_a_proven_disagree(client, loaded_rules, monkeypatch, mode):
    r = _rules(loaded_rules.rules, mode="gate")
    with client.app.state.sessionmaker() as s:
        _call(s)
        _proven(monkeypatch, False)
        assert _sig(s, r, mode).status == "PASS"  # not proven → behaves like ADVISORY
        _proven(monkeypatch, True)
        blocked = _sig(s, r, mode)
        assert blocked.status == "SKIP" and blocked.skip_reason == "ADVISOR_DISAGREE"
        assert blocked.features["advisor"]["blocks"] is True
        agree = _sig(s, r, mode, Direction.SHORT)
        assert agree.status == "PASS" and agree.features["advisor"]["verdict"] == "AGREE"
        skip = _sig(s, r, mode, Direction.LONG, ok=False)  # already a SKIP: keeps its own code (tighten-only)
        assert skip.skip_reason == "OUTSIDE_WINDOW" and skip.features["advisor"]["blocks"] is False


def test_no_call_and_neutral_never_block(client, loaded_rules, monkeypatch):
    _proven(monkeypatch, True)
    r = _rules(loaded_rules.rules, mode="GATE")
    with client.app.state.sessionmaker() as s:
        sig = _sig(s, r, "GALA_PA")
        assert sig.status == "PASS" and sig.features["advisor"]["verdict"] == "NO_CALL"
        _call(s, "HOLD")
        sig = _sig(s, r, "CONTI_ORB")
        assert sig.status == "PASS" and sig.features["advisor"]["verdict"] == "NEUTRAL"


def test_off_and_opt_out_change_nothing(client, loaded_rules, monkeypatch):
    _proven(monkeypatch, True)
    with client.app.state.sessionmaker() as s:
        _call(s)
        off = _sig(s, _rules(loaded_rules.rules, mode="OFF"), "JJ_FPT")
        assert off.status == "PASS" and "advisor" not in off.features
        opt = _sig(s, _rules(loaded_rules.rules, mode="GATE", skip_strategies=["OKALA_8020"]), "OKALA_8020")
        assert opt.status == "PASS" and "advisor" not in opt.features
        noise = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key="n", direction=Direction.LONG, at=AT, gate=(True, "OK", ""),
            features={}, plan=("NOISE", D(100), D(99), D(102), D(1), D(2)),
            rules=_rules(loaded_rules.rules, mode="GATE"),
        )  # fmt: skip
        assert "advisor" not in noise.features  # NOISE keeps its own D77 gate
        assert s.query(AuditLog).filter_by(action="signal.advisor").count() == 0


def test_config_validation():
    assert AdvisorCfg().mode == "ADVISORY"
    with pytest.raises(ValidationError):
        AdvisorCfg(skip_strategies=["NOISE"])
    with pytest.raises(ValidationError):
        AdvisorCfg(mode="LOUD")


def test_settings_and_api(authed, monkeypatch):
    _proven(monkeypatch, True)
    r = authed.put("/api/risk/settings", json={"changes": {"strategy.advisor.mode": "GATE"}, "note": "advisor gate"})
    assert r.status_code == 200, r.text
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.advisor.skip_strategies": ["X"]}, "note": "x"})
    assert bad.status_code >= 400
    st = authed.app.state
    with st.sessionmaker() as s:
        sig = _sig(s, st.rules.rules, "CONTI_VWAP")
        s.commit()
        sid = sig.id
    adv = authed.get("/api/strategies").json()["advisor"]
    assert adv["mode"] == "GATE" and adv["connected"] is False and set(adv["cards"]) >= {"jj_fpt", "order_flow_auction"}
    assert adv["cards"]["gala_pa"]["call_label"] is None
    row = next(x for x in authed.get("/api/signals").json()["signals"] if x["id"] == sid)
    assert row["advisor"]["verdict"] == "NO_CALL"
