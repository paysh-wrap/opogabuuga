"""D92: NOISE + AI Duo split-risk button: half size, half the daily loss budget per side, AI Duo paper only."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.models import Account, AuditLog, Trade
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


def test_control_noise_alone_keeps_its_full_size(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], noise=True, ai_duo=True, noise_ai_split=False)
    res = asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[aid]))
    assert res[0].ok and _qty(st, _ext(st, aid)) == 4


@pytest.mark.parametrize("n,expected", [(4, 2), (3, 1), (2, 1), (1, 1)])  # half, rounded down, never below 1 micro
def test_split_halves_noise_size_rounded_down_min_one(authed, clock, n, expected):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], contracts=n, noise=True, ai_duo=True, noise_ai_split=True)
    res = asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[aid]))
    assert res[0].ok and _qty(st, _ext(st, aid)) == expected
    with st.sessionmaker() as s:
        row = s.query(AuditLog).filter_by(action="trade.split_risk").one()
        assert row.payload["strategy"] == "NOISE" and row.payload["contracts"] == expected


def test_split_halves_ai_duo_size_on_the_big_account_too(authed, clock):
    st, (aid,) = _setup(authed, clock, [("big", "150000")], noise=True, ai_duo=True, noise_ai_split=True)
    res = asyncio.run(st.controller.execute(_sig(st, "AI_DUO", "D1"), "automation", only=[aid]))
    assert res[0].ok, res
    split = _qty(st, _ext(st, aid))
    _flat(st, aid)
    _strategy(authed, noise=True, ai_duo=True, noise_ai_split=False)
    clock.set(AT.replace(hour=16))
    res = asyncio.run(st.controller.execute(_sig(st, "AI_DUO", "D2"), "automation", only=[aid]))
    assert res[0].ok, res
    assert split == max(_qty(st, _ext(st, aid)) // 2, 1) and split < _qty(st, _ext(st, aid))


def test_split_needs_both_sides_on(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], noise=True, ai_duo=False, noise_ai_split=True)
    res = asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[aid]))
    assert res[0].ok and _qty(st, _ext(st, aid)) == 4  # AI Duo off: NOISE keeps its normal size


def test_each_side_has_half_the_daily_loss_budget_and_the_sides_do_not_share_it(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], contracts=2, noise=True, ai_duo=True, noise_ai_split=True)
    # NOISE already lost $280 today (half of the $600 DLL is $300) -> a new NOISE trade (1 micro ~ $45 + $40 margin)
    # does not fit its remaining $20, while AI Duo still has its whole $300
    with st.sessionmaker() as s:
        old = _sig(st, "NOISE", "N-old")
        s.add(
            Trade(
                account_id=aid, signal_id=old, symbol="MNQ", direction="LONG", qty=1, entry=D(1), exit=D(1),
                pnl_usd=D(-280), risk_usd=D(280), opened_at=AT, closed_at=AT, trade_ref="OLD",
            )
        )  # fmt: skip
        s.commit()
    res = asyncio.run(st.controller.execute(_sig(st, "NOISE", "N-new"), "automation", only=[aid]))
    assert res[0].ok is False and res[0].reason == "SPLIT_BUDGET_EXCEEDED", res
    res = asyncio.run(st.controller.execute(_sig(st, "AI_DUO", "D-new"), "automation", only=[aid]))
    assert res[0].ok is True, res


def test_a_loss_from_yesterday_does_not_use_todays_budget(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], contracts=2, noise=True, ai_duo=True, noise_ai_split=True)
    yesterday = datetime(2026, 10, 12, 15, 0, tzinfo=UTC)
    with st.sessionmaker() as s:
        old = _sig(st, "NOISE", "N-old")
        s.add(
            Trade(
                account_id=aid, signal_id=old, symbol="MNQ", direction="LONG", qty=1, entry=D(1), exit=D(1),
                pnl_usd=D(-280), risk_usd=D(280), opened_at=yesterday, closed_at=yesterday, trade_ref="OLD",
            )
        )  # fmt: skip
        s.add(  # a trade without a signal link and an open trade never count
            Trade(account_id=aid, symbol="MNQ", direction="LONG", qty=1, entry=D(1), risk_usd=D(1), opened_at=AT,
                  trade_ref="OPEN")
        )  # fmt: skip
        s.commit()
    res = asyncio.run(st.controller.execute(_sig(st, "NOISE", "N-new"), "automation", only=[aid]))
    assert res[0].ok is True, res


def test_ai_duo_never_sends_an_order_to_a_non_paper_account_even_with_the_split_on(authed, clock):
    st, (aid,) = _setup(authed, clock, [("live", "25000")], noise=True, ai_duo=True, noise_ai_split=True)
    with st.sessionmaker() as s:
        s.get(Account, aid).is_sim = False
        s.commit()
    ext = _ext(st, aid)
    res = asyncio.run(st.controller.execute(_sig(st, "AI_DUO", "D1"), "automation", only=[aid]))
    assert res[0].ok is False and res[0].reason == "PAPER_ONLY_STRATEGY" and _qty(st, ext) == 0


def test_noise_on_a_non_paper_account_still_trades_at_half_size(authed, clock):
    st, (aid,) = _setup(authed, clock, [("live", "25000")], noise=True, ai_duo=True, noise_ai_split=True)
    with st.sessionmaker() as s:
        s.get(Account, aid).is_sim = False
        s.commit()
    res = asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[aid]))
    assert res[0].ok and _qty(st, _ext(st, aid)) == 2


def test_hedge_lock_still_applies_with_the_split_on(authed, clock):
    st, (aid,) = _setup(authed, clock, [("big", "150000")], noise=True, ai_duo=True, noise_ai_split=True)
    res = asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[aid]))
    assert res[0].ok, res
    short = (D(20000), D(20020), D(19900), D(20), D(5))
    duo = _sig(st, "AI_DUO", "D1", Direction.SHORT, short)
    res = asyncio.run(st.controller.execute(duo, "automation", only=[aid]))
    assert res[0].ok is False and res[0].reason == "HEDGE_LOCK", res


def test_button_is_default_off_turns_both_strategies_on_and_reflects_the_state(authed):
    body = authed.get("/api/strategies").json()
    card = next(x for x in body["strategies"] if x["key"] == "noise_ai_split")
    assert card["enabled"] is False and card["setting"] == "strategy.noise_ai_split"
    assert card["also"] == ["strategy.noise", "strategy.ai_duo"] and card["status"] == "PAPER ONLY"
    r = authed.put(
        "/api/risk/settings",
        json={
            "changes": {"strategy.noise_ai_split": True, "strategy.noise": True, "strategy.ai_duo": True},
            "note": "t",
        },
    )
    assert r.status_code == 200, r.text
    card = next(x for x in authed.get("/api/strategies").json()["strategies"] if x["key"] == "noise_ai_split")
    assert card["enabled"] is True
    authed.put("/api/risk/settings", json={"changes": {"strategy.ai_duo": False}, "note": "t"})
    card = next(x for x in authed.get("/api/strategies").json()["strategies"] if x["key"] == "noise_ai_split")
    assert card["enabled"] is False  # AI Duo off → no split in effect
