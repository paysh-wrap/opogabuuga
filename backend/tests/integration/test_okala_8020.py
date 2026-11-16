"""OKALA 8020 (D145) end to end: stored bars → signal; controller Lucid fit; the add-to-winners exception."""

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
from tests.unit.test_okala_8020 import T0, seq

AT = (T0 + timedelta(minutes=40)).astimezone(UTC)


def test_signal_from_stored_bars(client, loaded_rules):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    okc = r.strategy.okala_8020_cfg.model_copy(update={"setups": ["LEVEL"]})
    rules = r.model_copy(
        update={"strategy": r.strategy.model_copy(update={"okala_8020": True, "okala_8020_cfg": okc}),
                "instruments": {**r.instruments, "MNQ": mnq}}
    )  # fmt: skip
    with client.app.state.sessionmaker() as s:
        for b in seq((25630, 25632, 25620, 25628)):
            s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                      v=b.v, source="tv"))  # fmt: skip
        s.commit()
        at = (T0 + timedelta(minutes=3)).astimezone(UTC)
        out = SS.run(s, rules=rules, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MNQ-OKALA-2026-10-13-0933" and sig.features["tp1"] == "25643.00"
        assert sig.features["add_no"] == 0 and "200 s" in sig.features["entry_bars"]
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "OKALA_8020" and plan.stop == D(25618)


def _setup(authed, clock):
    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "K", "stage": "EVAL", "balance": "25000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MNQ"] = D(20000)
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"okala_8020": True})})
    return st, aid


_n = [0]


def _sig(st, direction=Direction.LONG, add_no=0, mode="OKALA_8020"):
    _n[0] += 1
    sign = direction.sign
    with st.sessionmaker() as s:
        x = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=f"MNQ-OKALA-x-{_n[0]}", direction=direction, at=AT,
            gate=(True, "OK", ""), features={"add_no": add_no, "tp1": str(D(20000) + sign * 15), "be_cover_pts": "1"},
            plan=(mode, D(20000), D(20000) - sign * 10, D(20000) + sign * 30, D(10), D(3)),
        )  # fmt: skip
        s.commit()
        return x.id


def _go(st, sid, aid):
    return [r.reason for r in asyncio.run(st.controller.execute(sid, "automation", only=[aid]))]


def _to_be(st):
    for t in st.controller.om.trades.values():
        for leg in t.legs:
            leg.stop = leg.entry if leg.entry is not None else t.plan.entry


def test_add_to_winners_exception(authed, clock, monkeypatch):
    st, aid = _setup(authed, clock)
    assert _go(st, _sig(st), aid) == [None]  # the first position: TP1 leg + break-even runner (7 micros on 25K)
    with st.sessionmaker() as s:
        assert [x.payload["contracts"] for x in s.query(AuditLog).filter_by(action="trade.okala_size")] == [7]
    t = next(iter(st.controller.om.trades.values()))
    assert t.guard_on and t.plan.partial_price == D(20015) and t.plan.breakeven_price == D(20001)
    assert _go(st, _sig(st, add_no=1), aid) == ["OKALA_ADD_NOT_AT_BE"]
    _to_be(st)
    assert _go(st, _sig(st, Direction.SHORT, add_no=1), aid) == ["OKALA_ADD_OPPOSITE"]
    real = st.controller._equity

    async def near_mll(a):
        return D("24050"), D(0)

    monkeypatch.setattr(st.controller, "_equity", near_mll)
    assert _go(st, _sig(st, add_no=1), aid)[0] in ("RISK_BASE_BELOW_PAUSE", "NEAR_MLL", "OKALA_SIZE_BELOW_1",
                                                   "OKALA_ADD_CAP")  # a Lucid refusal stops the add  # fmt: skip
    monkeypatch.setattr(st.controller, "_equity", real)
    assert _go(st, _sig(st, add_no=1), aid) == [None]  # add 1
    _to_be(st)
    assert _go(st, _sig(st, add_no=2), aid) == [None]  # add 2
    _to_be(st)
    assert _go(st, _sig(st, add_no=3), aid) == ["OKALA_MAX_ADDS"]


def test_add_refused_when_the_cap_is_used(authed, clock):
    st, aid = _setup(authed, clock)
    assert _go(st, _sig(st), aid) == [None]
    _to_be(st)
    for t in st.controller.om.trades.values():
        for leg in t.legs:
            leg.qty = 200  # fees + slippage on 400 micros already exceed one trade's cap
    assert _go(st, _sig(st, add_no=1), aid) == ["OKALA_ADD_CAP"]


def test_other_strategies_still_get_position_open(authed, clock):
    st, aid = _setup(authed, clock)
    h = st.controller.rules
    orb_cfg = h.rules.strategy.conti_orb_cfg.model_copy(update={"one_account_per_trade": False})
    h.rules = h.rules.model_copy(
        update={"strategy": h.rules.strategy.model_copy(update={"conti_orb": True, "conti_orb_cfg": orb_cfg})}
    )
    assert _go(st, _sig(st), aid) == [None]
    _to_be(st)
    orb = _sig(st, mode="CONTI_ORB")
    with st.sessionmaker() as s:
        s.get(Signal, orb).features = {**s.get(Signal, orb).features, "strategy": "CONTI_ORB"}
        s.commit()
    assert _go(st, orb, aid) == ["POSITION_OPEN"]  # never a second position for another strategy


@pytest.mark.parametrize(
    ("k", "stage", "want"),
    [
        (25, "EVAL", ("158.33", [7])), (25, "FUNDED", ("180.00", [8])),
        (50, "EVAL", ("360.00", [16])), (50, "FUNDED", ("360.00", [16])),
        (100, "EVAL", ("540.00", [24])), (100, "FUNDED", ("540.00", [24])),
        (150, "EVAL", ("810.00", [36])), (150, "FUNDED", ("810.00", [36])),
    ],
)  # fmt: skip
def test_pro_plan_fit_table(k, stage, want):
    risk, n = fit(k, stage, "okala_8020_cfg", 3, (10, 10))
    assert (risk, n[:1]) == want
