"""Shared helpers for controller-level integration tests (moved out of the removed D92 split-risk test, D174)."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.models import Account
from app.signals import strategy_service as SS

AT = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)
PLAN = (D(20000), D(19980), D(20100), D(20), D(5))  # 20-pt stop: ~$45 per micro with fee + slippage


def _strategy(authed, **kw):
    h = authed.app.state.rules
    st = h.rules.strategy
    cfgs = {"noise_cfg": st.noise_cfg.model_copy(update={"contracts": kw.pop("contracts", 4)})}
    h.rules = h.rules.model_copy(update={"strategy": st.model_copy(update={**cfgs, **kw})})


def _setup(authed, clock, balances, **kw):
    st = authed.app.state
    clock.set(AT)
    ids = []
    for label, bal in balances:
        aid = authed.post("/api/accounts", json={"label": label, "stage": "EVAL", "balance": bal}).json()["id"]
        authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
        ids.append(aid)
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MNQ"] = D(20000)
    _strategy(authed, **kw)
    return st, ids


def _sig(st, mode, key, direction=Direction.LONG, plan=PLAN):
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=key, direction=direction, at=AT, gate=(True, "OK", ""), features={},
            plan=(mode, *plan),
        )  # fmt: skip
        s.commit()
        return sig.id


def _qty(st, ext):
    return sum(t.qty for t in st.controller.om.trades.values() if t.account == ext)


def _flat(st, aid):
    asyncio.run(st.controller.flatten(aid, "tester", "MANUAL_FLATTEN"))
    st.controller.om.trades.clear()


def _ext(st, aid):
    with st.sessionmaker() as s:
        return s.get(Account, aid).broker_account_id
