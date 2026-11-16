"""CANDACE ICT SCALP (D149) end to end: stored bars → signal; controller grade size (tighten-only); Pro fit table."""

from __future__ import annotations

import asyncio
from datetime import UTC, timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.lucid_fit import grade_contracts
from app.engine.trade_plan import Direction
from app.models import AuditLog, Bar, Signal, TradePlanRow
from app.signals import strategy_service as SS
from tests.integration.lucid_fit_helpers import fit
from tests.unit.test_candace_ict import T9, bars

AT = (T9 + timedelta(minutes=13)).astimezone(UTC)


def test_signal_from_stored_bars(client, loaded_rules):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    cc = r.strategy.candace_ict_cfg.model_copy(update={"premium_pct": D("0.2")})
    rules = r.model_copy(
        update={"strategy": r.strategy.model_copy(update={"candace_ict": True, "candace_ict_cfg": cc}),
                "instruments": {**r.instruments, "MNQ": mnq}}
    )  # fmt: skip
    with client.app.state.sessionmaker() as s:
        for b in bars():
            s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                      v=b.v, source="tv"))  # fmt: skip
        s.commit()
        out = SS.run(s, rules=rules, clock=FixedClock(AT), calendar=lambda _d: [], symbol="MNQ", tf="1", at=AT)
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MNQ-CAND-2026-10-13-0913" and sig.direction == "SHORT"
        assert sig.features["grade"] == "C" and sig.features["size_mult"] == "0.5"
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "CANDACE_ICT" and plan.stop == D("109.5")
        ex = (T9 + timedelta(minutes=28)).astimezone(UTC)
        s.add(Bar(symbol="MNQ", tf="1", close_time=ex, o=D(101), h=D(101), l=D(101), c=D(101), v=D(1), source="tv"))
        for m in range(14, 28):
            t = (T9 + timedelta(minutes=m)).astimezone(UTC)
            s.add(Bar(symbol="MNQ", tf="1", close_time=t, o=D(101), h=D(101), l=D(101), c=D(101), v=D(1), source="tv"))
        s.commit()
        out = SS.run(s, rules=rules, clock=FixedClock(ex), calendar=lambda _d: [], symbol="MNQ", tf="1", at=ex)
        assert out.exits == [(sig.id, "CAND_TIME_EXIT")]  # B2 about 15 minutes


def test_grade_contracts_is_tighten_only():
    assert [grade_contracts(4, D(x)) for x in ("2.0", "1.0", "0.5", "5")] == [4, 2, 1, 4]


@pytest.mark.parametrize(
    ("mult", "want"), [("2.0", (None, 3)), ("1.0", (None, 1)), ("0.5", ("CAND_GRADE_SIZE_BELOW_1", None))]
)
def test_controller_grade_size(authed, clock, mult, want):
    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "C", "stage": "EVAL", "balance": "25000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MNQ"] = D(20000)
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"candace_ict": True})})
    with st.sessionmaker() as s:
        x = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=f"MNQ-CAND-x-{mult}", direction=Direction.SHORT, at=AT,
            gate=(True, "OK", ""), features={"size_mult": mult},
            plan=("CANDACE_ICT", D(20000), D(20020), D(19960), D(20), D(2)),
        )  # fmt: skip
        s.commit()
        sid = x.id
    [res] = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    assert res.reason == want[0]
    if want[1] is not None:
        assert sum(t.qty for t in st.controller.om.trades.values()) == want[1]
        with st.sessionmaker() as s:
            assert s.query(AuditLog).filter_by(action="trade.cand_size").one().payload["contracts"] == want[1]


@pytest.mark.parametrize(
    ("k", "stage", "want"),
    [
        (25, "EVAL", ("158.33", [3, 1])), (25, "FUNDED", ("180.00", [4, 2])),
        (50, "EVAL", ("360.00", [8, 4])), (50, "FUNDED", ("360.00", [8, 4])),
        (100, "EVAL", ("540.00", [12, 6])), (100, "FUNDED", ("540.00", [12, 6])),
        (150, "EVAL", ("810.00", [19, 9])), (150, "FUNDED", ("810.00", [19, 9])),
    ],
)  # fmt: skip
def test_pro_plan_fit_table(k, stage, want):
    assert fit(k, stage, "candace_ict_cfg", 3, (20, 40)) == want
