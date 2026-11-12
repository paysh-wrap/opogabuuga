"""B5 (session 20): the household hedge lock also sees orders still in flight - trades the order manager tracks and
trades persisted in the last `reliability.hedge_inflight_s` seconds - when the broker (CrossTrade polling) has not
reported the position yet."""

import asyncio
from datetime import timedelta
from decimal import Decimal as D

from app.engine.trade_plan import Direction
from tests.integration.test_split_risk import AT, _ext, _setup, _sig

SHORT = (D(20000), D(20020), D(19900), D(20), D(5))


def _lagging(st):
    async def none(_s):
        return []  # the broker has not reported any position yet

    st.controller.open_positions = none


def test_order_in_flight_on_another_account_blocks_the_opposite_side(authed, clock):
    st, (a, b) = _setup(authed, clock, [("a", "25000"), ("b", "25000")], noise=True, ai_duo=True)
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[a]))[0].ok
    _lagging(st)
    res = asyncio.run(st.controller.execute(_sig(st, "AI_DUO", "D1", Direction.SHORT, SHORT), "automation", only=[b]))
    assert res[0].ok is False and res[0].reason == "HEDGE_LOCK", res
    # the same side is never blocked by the lock
    res = asyncio.run(st.controller.execute(_sig(st, "AI_DUO", "D2"), "automation", only=[b]))
    assert res[0].reason != "HEDGE_LOCK", res


def test_recent_persisted_trade_counts_until_the_window_ends(authed, clock):
    st, (a, b) = _setup(authed, clock, [("a", "25000"), ("b", "25000")], noise=True, ai_duo=True)
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[a]))[0].ok
    _lagging(st)
    st.controller.om.trades.clear()  # e.g. a restart before recovery: only the DB row is left
    with st.sessionmaker() as s:
        got = st.controller.inflight_positions(s)
        assert [(p.account, p.direction) for p in got] == [(_ext(st, a), "LONG")]
    res = asyncio.run(st.controller.execute(_sig(st, "AI_DUO", "D1", Direction.SHORT, SHORT), "automation", only=[b]))
    assert res[0].reason == "HEDGE_LOCK", res
    clock.set(AT + timedelta(seconds=st.rules.rules.reliability.hedge_inflight_s + 1))
    with st.sessionmaker() as s:
        assert st.controller.inflight_positions(s) == []
