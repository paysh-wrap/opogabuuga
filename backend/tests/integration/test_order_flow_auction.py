"""ORDER FLOW · AUCTION (IMRE) (D150) end to end: stored bars → signal; controller split-risk fit; Pro fit table."""

from __future__ import annotations

import asyncio
from datetime import UTC
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.models import AuditLog, Bar, Signal, TradePlanRow
from app.signals import strategy_service as SS
from tests.integration.lucid_fit_helpers import fit
from tests.unit.test_auction_imre import BG, day, hist


def _on(r, **kw):
    ofc = r.strategy.order_flow_cfg
    au = ofc.auction.model_copy(update={"enabled": True, **kw})
    st = r.strategy.model_copy(update={"order_flow": True, "order_flow_cfg": ofc.model_copy(update={"auction": au})})
    return r.model_copy(update={"strategy": st})


def test_signal_from_stored_bars(client, loaded_rules):
    r = loaded_rules.rules
    rules = _on(r.model_copy(update={"instruments": {**r.instruments, "MNQ": r.instruments["MNQ"].model_copy(
        update={"enabled": True})}}))  # fmt: skip
    rows = [*hist(), *day(13, [*BG, (97, 97, 95, 95.25, 100), (95.25, 96.75, 95, 96.5, 100)])]
    with client.app.state.sessionmaker() as s:
        for b in rows:
            s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                      v=b.v, source="tv"))  # fmt: skip
        s.commit()
        at = rows[-1].close_time.astimezone(UTC)
        out = SS.run(s, rules=rules, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MNQ-OFA-2026-10-13-0952" and sig.features["setup"] == "FAILED_AUCTION_V"
        assert sig.features["delta"] == "ESTIMATED" and sig.features["regime"] == "BALANCE"
        assert sig.features["advisor"]["verdict"] == "NO_CALL" and sig.status == "PASS"  # D151 end to end
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "ORDER_FLOW_AUCTION" and plan.take_profit == D(104)
        off = rules.model_copy(update={"strategy": rules.strategy.model_copy(update={"order_flow": False})})
        assert (
            SS.run(s, rules=off, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at).updates
            == []
        )
        assert SS.run_order_flow_auction(s, rules, FixedClock(at), lambda _d: [], at, exits_only=True).updates == []


@pytest.mark.parametrize(("share", "want"), [("1", 8), ("0.5", 4)])
def test_controller_split_risk_and_two_legs(authed, clock, share, want):
    st = authed.app.state
    at = st.clock.now()
    aid = authed.post("/api/accounts", json={"label": "I", "stage": "EVAL", "balance": "25000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MNQ"] = D(20000)
    h = st.controller.rules
    h.rules = _on(h.rules)
    with st.sessionmaker() as s:
        x = SS._new_signal(
            s, FixedClock(at), symbol="MNQ", key=f"MNQ-OFA-x-{share}", direction=Direction.LONG, at=at,
            gate=(True, "OK", ""), features={"risk_share": share, "tp1": "20012", "be_cover_pts": "0"},
            plan=("ORDER_FLOW_AUCTION", D(20000), D(19992), D(20024), D(8), D(3)),
        )  # fmt: skip
        s.commit()
        sid = x.id
    [res] = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    assert res.reason is None, res.reason
    with st.sessionmaker() as s:
        assert s.query(AuditLog).filter_by(action="trade.ofa_size").one().payload["contracts"] == want
    t = next(iter(st.controller.om.trades.values()))
    assert t.guard_on and t.plan.partial_price == D(20012) and t.plan.breakeven_price == D(20000)  # F1 stop to entry


@pytest.mark.parametrize(
    ("k", "stage", "want"),
    [
        (25, "EVAL", ("158.33", [8, 4])), (25, "FUNDED", ("180.00", [10, 5])),
        (50, "EVAL", ("360.00", [20, 10])), (50, "FUNDED", ("360.00", [20, 10])),
        (100, "EVAL", ("540.00", [30, 15])), (100, "FUNDED", ("540.00", [30, 15])),
        (150, "EVAL", ("810.00", [45, 23])), (150, "FUNDED", ("810.00", [45, 23])),
    ],
)  # fmt: skip
def test_pro_plan_fit_table(k, stage, want):
    assert fit(k, stage, "order_flow_cfg.auction", 3, (8, 16)) == want
