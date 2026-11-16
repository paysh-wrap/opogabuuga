"""BRUNI STRUCTURE (D148) end to end: stored bars → signal; controller fit, shield and autocorrelation overlays."""

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
from tests.unit.test_bruni_structure import DAY2, hist, m1

AT = (DAY2 + timedelta(minutes=1)).astimezone(UTC)


def test_signal_from_stored_bars(client, loaded_rules):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    bc = r.strategy.bruni_structure_cfg.model_copy(update={"swing_lookback": 1})
    rules = r.model_copy(
        update={"strategy": r.strategy.model_copy(update={"bruni_structure": True, "bruni_structure_cfg": bc}),
                "instruments": {**r.instruments, "MNQ": mnq}}
    )  # fmt: skip
    with client.app.state.sessionmaker() as s:
        for b in [*hist(), m1(1, 112, 112, 108, 110)]:
            s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                      v=b.v, source="tv"))  # fmt: skip
        s.commit()
        out = SS.run(s, rules=rules, clock=FixedClock(AT), calendar=lambda _d: [], symbol="MNQ", tf="1", at=AT)
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MNQ-BRUNI-2026-10-13-0931" and sig.features["context"] == "FOLLOW_A"
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "BRUNI_STRUCTURE" and (plan.stop, plan.take_profit) == (D("96.5"), D(137))


def _setup(authed, clock, n=1, **cfg):
    st = authed.app.state
    clock.set(AT)
    ids = []
    for i in range(n):
        aid = authed.post("/api/accounts", json={"label": f"B{i}", "stage": "EVAL", "balance": "25000"}).json()["id"]
        authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
        ids.append(aid)
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MNQ"] = D(20000)
    h = st.controller.rules
    bc = h.rules.strategy.bruni_structure_cfg.model_copy(update=cfg)
    h.rules = h.rules.model_copy(
        update={"strategy": h.rules.strategy.model_copy(update={"bruni_structure": True, "bruni_structure_cfg": bc})}
    )
    return st, ids


_n = [0]


def _sig(st, stop=D(20)):
    _n[0] += 1
    with st.sessionmaker() as s:
        x = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=f"MNQ-BRUNI-x-{_n[0]}", direction=Direction.LONG, at=AT,
            gate=(True, "OK", ""), features={}, plan=("BRUNI_STRUCTURE", D(20000), D(20000) - stop,
                                                     D(20000) + 2 * stop, stop, D(2)),
        )  # fmt: skip
        s.commit()
        return x.id


def _go(st, sid, ids):
    return [(r.account_id, r.reason) for r in asyncio.run(st.controller.execute(sid, "automation", only=ids))]


def test_controller_fit_and_size_skip(authed, clock):
    st, ids = _setup(authed, clock)
    assert _go(st, _sig(st, D(900)), ids) == [(ids[0], "BRUNI_SIZE_BELOW_1")]
    assert _go(st, _sig(st), ids) == [(ids[0], None)]
    with st.sessionmaker() as s:
        rows = [x.payload for x in s.query(AuditLog).filter_by(action="trade.bruni_size")]
    assert rows[-1]["risk_usd"] == "158.33" and rows[-1]["contracts"] == 3


def test_drawdown_shield_one_account_per_week(authed, clock):
    st, ids = _setup(authed, clock, n=3, drawdown_shield=True)
    first = _go(st, _sig(st), ids)
    assert len(first) == 1 and first[0][1] is None
    st.controller.om.trades.clear()  # flat again — the week's account stays the only one
    again = _go(st, _sig(st), ids)
    assert [a for a, _ in again] == [first[0][0]]
    others = [i for i in ids if i != first[0][0]]
    assert _go(st, _sig(st), others) == [(first[0][0], "BRUNI_SHIELD_ACCOUNT_BUSY")]


def test_autocorrelation_overlay_only_shrinks(authed, clock, monkeypatch):
    st, ids = _setup(
        authed, clock, autocorr_sizing=True, autocorr_conditional_wr=D(42), autocorr_unconditional_wr=D(50)
    )
    monkeypatch.setattr(type(st.controller), "_bruni_last_won", staticmethod(lambda s, a: False))
    cut = {"STRONG": D("0.2")}
    h = st.controller.rules
    bc = h.rules.strategy.bruni_structure_cfg.model_copy(update={"autocorr_cut": cut})
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"bruni_structure_cfg": bc})})
    assert _go(st, _sig(st), ids) == [(ids[0], "BRUNI_AUTOCORR_SKIP")]  # 3 micros x 0.2 → 0
    monkeypatch.setattr(type(st.controller), "_bruni_last_won", staticmethod(lambda s, a: True))
    assert _go(st, _sig(st), ids) == [(ids[0], None)]  # after a win: the plain Lucid-fit size, never more


def test_last_won_and_week_account_from_history(authed, clock):
    st, _ids = _setup(authed, clock)
    with st.sessionmaker() as s:
        from app.models import Account

        a = s.query(Account).first()
        assert st.controller._bruni_last_won(s, a) is None
        assert st.controller._bruni_week_account(s) is None


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
    assert fit(k, stage, "bruni_structure_cfg", 3, (20, 40)) == want
