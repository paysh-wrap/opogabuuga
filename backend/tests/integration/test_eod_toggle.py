"""D137: strategy.eod_closed_balance — kill switch watches the closed balance on EOD accounts only (default OFF)."""

import asyncio
from decimal import Decimal as D

from app.models import Account
from tests.integration.test_payout_consistency_api import _login

_N = [0]


def _run(authed, clock, *, dd, on, bal, opnl, dll=False):
    _N[0] += 1
    _login(authed, clock)
    aid = authed.post("/api/accounts", json={"label": f"E{_N[0]}", "stage": "EVAL", "balance": "25000"}).json()["id"]
    st = authed.app.state
    ctl = st.controller
    with st.sessionmaker() as s:
        a = s.get(Account, aid)
        a.drawdown_type, a.dll_enabled = dd, dll
        s.commit()
    h = st.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"eod_closed_balance": on})})
    calls: list[str] = []

    async def fake_flatten(s, a, reason):
        calls.append(reason)
        return True

    async def fake_equity(a):
        return bal, opnl

    ctl._flatten_account = fake_flatten  # type: ignore[method-assign]
    ctl._equity = fake_equity  # type: ignore[method-assign]

    async def go():
        with st.sessionmaker() as s:
            await ctl._monitor(s)
            s.commit()

    asyncio.run(go())
    with st.sessionmaker() as s:
        return calls, s.get(Account, aid).paused_reason


def test_eod_open_loss_inside_kill_distance_kills_only_when_off(authed, clock):
    # balance 25,000, open loss -950 -> equity 24,050 is 50 above the 24,000 floor (kill distance 100)
    assert _run(authed, clock, dd="eod", on=False, bal=D(25000), opnl=D(-950)) == (["KILL_SWITCH"], "KILL_SWITCH")


def test_eod_open_loss_ignored_when_on(authed, clock):
    assert _run(authed, clock, dd="eod", on=True, bal=D(25000), opnl=D(-950)) == ([], None)


def test_closed_balance_inside_distance_kills_in_both_modes(authed, clock):
    for on in (False, True):
        calls, reason = _run(authed, clock, dd="eod", on=on, bal=D(24050), opnl=D(-10))
        assert calls == ["KILL_SWITCH"] and reason == "KILL_SWITCH"


def test_intraday_account_still_kills_on_open_pnl_with_toggle_on(authed, clock):
    assert _run(authed, clock, dd="intraday", on=True, bal=D(25000), opnl=D(-950)) == (["KILL_SWITCH"], "KILL_SWITCH")


def test_toggle_listed_saved_and_versioned(authed):
    got = {t["key"]: t for t in authed.get("/api/strategies").json()["toggles"]}
    t = got["eod_closed_balance"]
    assert t["setting"] == "strategy.eod_closed_balance" and t["value"] is False
    assert t["title"] == "EOD drawdown: open losses don't stop the account"
    assert "does not breach by itself" in t["note"] and "closed balance only" in t["on_label"]
    v0 = authed.get("/api/risk/settings").json()["version"]
    assert (
        authed.put(
            "/api/risk/settings", json={"changes": {"strategy.eod_closed_balance": True}, "note": "t"}
        ).status_code
        == 200
    )
    assert authed.get("/api/risk/settings").json()["version"] == v0 + 1
    assert authed.app.state.rules.rules.strategy.eod_closed_balance is True
    assert authed.put(
        "/api/risk/settings", json={"changes": {"strategy.eod_closed_balance": "maybe"}, "note": "t"}
    ).status_code in (400, 422)


def test_dll_flatten_still_applies_with_the_toggle_on(authed, clock):
    calls, _ = _run(authed, clock, dd="eod", on=True, bal=D(25000), opnl=D(-950), dll=True)
    assert calls == ["DLL_LIMIT"]  # D137 never touches the daily loss limit
