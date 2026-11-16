"""CONTI VWAP (D147) end to end: stored bars → signal / VWAP-cross exit / reversal; controller fit; Pro fit table."""

from __future__ import annotations

import asyncio
from datetime import UTC, timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.models import AuditLog, Bar, Signal, TradePlanRow
from app.signals import strategy_service as SS
from tests.integration.lucid_fit_helpers import fit
from tests.unit.test_conti_vwap import T0, bar


def _rules(loaded_rules):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    st = r.strategy.model_copy(update={"conti_vwap": True})
    return r.model_copy(update={"strategy": st, "instruments": {**r.instruments, "MNQ": mnq}})


def _run(s, rules, minute):
    at = (T0 + timedelta(minutes=minute)).astimezone(UTC)
    return SS.run(s, rules=rules, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)


def test_signal_exit_and_reversal_from_stored_bars(client, loaded_rules):
    rules = _rules(loaded_rules)
    with client.app.state.sessionmaker() as s:
        for b in [bar(1, 100, spread=0), bar(2, 102, spread=0), bar(3, 103, spread=0), bar(4, 99, spread=0)]:
            s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                      v=b.v, source="tv"))  # fmt: skip
        s.commit()
        long_ = s.get(Signal, _run(s, rules, 2).updates[0].signal_id)
        assert long_.model_key == "MNQ-CVWAP-2026-10-13-0932" and long_.direction == "LONG"
        plan = s.query(TradePlanRow).filter_by(signal_id=long_.id).one()
        assert plan.mode == "CONTI_VWAP" and plan.stop == D(77)
        assert _run(s, rules, 3).updates == []
        out = _run(s, rules, 4)
        assert out.exits == [(long_.id, "CVWAP_CROSS")]  # C5
        assert s.get(Signal, out.updates[0].signal_id).direction == "SHORT"  # the controller waits for flat (D139)


def test_controller_fit_and_skip(authed, clock):
    st = authed.app.state
    at = (T0 + timedelta(minutes=40)).astimezone(UTC)
    clock.set(at)
    aid = authed.post("/api/accounts", json={"label": "V", "stage": "EVAL", "balance": "25000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"conti_vwap": True})})

    def sig(stop, tag):
        with st.sessionmaker() as s:
            x = SS._new_signal(
                s, FixedClock(at), symbol="MNQ", key=f"MNQ-CVWAP-x-{tag}", direction=Direction.SHORT, at=at,
                gate=(True, "OK", ""), features={},
                plan=("CONTI_VWAP", D(20000), D(20000) + stop, D(19800), stop, D(200) / stop),
            )  # fmt: skip
            s.commit()
            return x.id

    assert [r.reason for r in asyncio.run(st.controller.execute(sig(D(900), "b"), "automation", only=[aid]))] == [
        "CVWAP_SIZE_BELOW_1"
    ]
    asyncio.run(st.controller.execute(sig(D(25), "a"), "automation", only=[aid]))
    with st.sessionmaker() as s:
        rows = [x.payload for x in s.query(AuditLog).filter_by(action="trade.cvwap_size")]
    assert rows[-1]["risk_usd"] == "158.33" and rows[-1]["contracts"] == 3


@pytest.mark.parametrize(
    ("k", "stage", "want"),
    [
        (25, "EVAL", ("158.33", [3, 7])), (25, "FUNDED", ("180.00", [3, 8])),
        (50, "EVAL", ("360.00", [6, 16])), (50, "FUNDED", ("360.00", [6, 16])),
        (100, "EVAL", ("540.00", [10, 24])), (100, "FUNDED", ("540.00", [10, 24])),
        (150, "EVAL", ("810.00", [15, 36])), (150, "FUNDED", ("810.00", [15, 36])),
    ],
)  # fmt: skip
def test_pro_plan_fit_table(k, stage, want):
    assert fit(k, stage, "conti_vwap_cfg", 3, (25, 10)) == want
