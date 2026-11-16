"""CONTI ORB (D146) end to end: stored bars → signal → controller Lucid-fit size; Pro plan fit table."""

from __future__ import annotations

import asyncio
from datetime import UTC, timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.models import AuditLog, Bar, Signal, TradePlanRow
from app.signals import strategy_service as SS
from tests.integration.lucid_fit_helpers import fit
from tests.unit.test_conti_orb import T0, day

AT = (T0 + timedelta(minutes=31)).astimezone(UTC)


def _rules(loaded_rules):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    st = r.strategy.model_copy(update={"conti_orb": True})
    return r.model_copy(update={"strategy": st, "instruments": {**r.instruments, "MNQ": mnq}})


def _run(s, rules, at):
    return SS.run(s, rules=rules, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)


def test_signal_from_stored_bars_and_1530_exit(client, loaded_rules):
    rules = _rules(loaded_rules)
    with client.app.state.sessionmaker() as s:
        for b in day([(100, 112, 99, 111)] + [(111, 112, 110, 111)] * 400):
            s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                      v=b.v, source="tv"))  # fmt: skip
        s.commit()
        out = _run(s, rules, AT)
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MNQ-CORB-2026-10-13-1001" and sig.direction == "LONG"
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "CONTI_ORB" and (plan.stop, plan.take_profit) == (D(90), D(132))
        assert _run(s, rules, AT).updates == []
        assert _run(s, rules, (T0 + timedelta(hours=6)).astimezone(UTC)).exits == [(sig.id, "CORB_TIME_EXIT")]
        off = rules.model_copy(update={"strategy": rules.strategy.model_copy(update={"conti_orb": False})})
        assert _run(s, off, AT + timedelta(minutes=1)).updates == []


def test_controller_size_and_skip(authed, clock):
    from app.engine.trade_plan import Direction

    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "O", "stage": "EVAL", "balance": "25000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"conti_orb": True})})

    def sig(stop, tag):
        with st.sessionmaker() as s:
            x = SS._new_signal(
                s, FixedClock(AT), symbol="MNQ", key=f"MNQ-CORB-x-{tag}", direction=Direction.LONG, at=AT,
                gate=(True, "OK", ""), features={},
                plan=("CONTI_ORB", D(20000), D(20000) - stop, D(20000) + stop, stop, D(1)),
            )  # fmt: skip
            s.commit()
            return x.id

    res = asyncio.run(st.controller.execute(sig(D(900), "b"), "automation", only=[aid]))
    assert [r.reason for r in res] == ["CORB_SIZE_BELOW_1"]  # a 900 pt range is too wide for one micro
    asyncio.run(st.controller.execute(sig(D(30), "a"), "automation", only=[aid]))
    with st.sessionmaker() as s:
        rows = [x.payload for x in s.query(AuditLog).filter_by(action="trade.corb_size")]
    assert rows[-1]["contracts"] >= 1 and rows[0]["contracts"] == 0


@pytest.mark.parametrize(
    ("k", "risk", "n"),
    [(25, "250.00", [4, 2]), (50, "500.00", [8, 4]), (100, "750.00", [12, 6]), (150, "1125.00", [18, 9])],
)
@pytest.mark.parametrize("stage", ["EVAL", "FUNDED"])
def test_pro_plan_fit_table(k, risk, n, stage):
    assert fit(k, stage, "conti_orb_cfg", 1, (30, 60)) == (risk, n)
