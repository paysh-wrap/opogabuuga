"""D132 (session 20): fade off on EVAL accounts (I3) and the NOISE profit-lock trigger toggle (100 / 80 pt)."""

import asyncio
from decimal import Decimal as D

from app.models import Account
from tests.integration.test_split_risk import _ext, _setup, _sig, _strategy


def test_fade_is_skipped_on_eval_accounts_only_while_the_toggle_is_on(authed, clock):
    st, (ev, fu) = _setup(authed, clock, [("eval", "25000"), ("funded", "25000")], noise=True, pm_fade=True)
    with st.sessionmaker() as s:
        s.get(Account, fu).stage = "FUNDED"
        s.commit()
    assert st.rules.rules.strategy.pm_fade_cfg.eval_off is True  # plan default
    res = asyncio.run(st.controller.execute(_sig(st, "PM_FADE", "F1"), "automation", only=[ev]))
    assert res[0].ok is False and res[0].reason == "FADE_OFF_IN_EVAL", res
    res = asyncio.run(st.controller.execute(_sig(st, "PM_FADE", "F2"), "automation", only=[fu]))
    assert res[0].reason != "FADE_OFF_IN_EVAL", res  # FUNDED keeps the fade
    fade = st.rules.rules.strategy.pm_fade_cfg.model_copy(update={"eval_off": False})
    _strategy(authed, noise=True, pm_fade=True, pm_fade_cfg=fade)
    res = asyncio.run(st.controller.execute(_sig(st, "PM_FADE", "F3"), "automation", only=[ev]))
    assert res[0].reason != "FADE_OFF_IN_EVAL", res


def test_noise_trade_gets_the_chosen_lock_trigger(authed, clock):
    st, (aid,) = _setup(authed, clock, [("a", "25000")], contracts=1, noise=True)
    nc = st.rules.rules.strategy.noise_cfg.model_copy(
        update={"contracts": 1, "profit_lock_trigger_pts": D(100), "profit_lock_pts": D(10),
                "profit_lock_trigger_alt_pts": D(80)}
    )  # fmt: skip
    st.rules.rules = st.rules.rules.model_copy(
        update={"strategy": st.rules.rules.strategy.model_copy(update={"noise_cfg": nc})}
    )
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[aid]))[0].ok
    (t,) = [t for t in st.controller.om.trades.values() if t.account == _ext(st, aid)]
    assert t.profit_lock == (D(100), D(10))
    st.controller.om.trades.clear()
    st.rules.rules = st.rules.rules.model_copy(
        update={"strategy": st.rules.rules.strategy.model_copy(update={"noise_lock_alt": True})}
    )
    asyncio.run(st.controller.flatten(aid, "tester", "MANUAL_FLATTEN"))
    clock.set(clock.now().replace(hour=16))
    res = asyncio.run(st.controller.execute(_sig(st, "NOISE", "N2"), "automation", only=[aid]))
    assert res[0].ok, res
    (t,) = [t for t in st.controller.om.trades.values() if t.account == _ext(st, aid)]
    assert t.profit_lock == (D(80), D(10))  # lock distance unchanged


def test_strategy_page_lists_the_session20_toggles_and_saves_are_versioned(authed):
    got = {t["key"]: t for t in authed.get("/api/strategies").json()["toggles"]}
    assert got["fade_eval_off"]["setting"] == "strategy.pm_fade_cfg.eval_off" and got["fade_eval_off"]["value"] is True
    assert got["noise_lock_alt"]["value"] is False and "80 pt" in got["noise_lock_alt"]["on_label"]
    assert "100 pt" in got["noise_lock_alt"]["off_label"] and got["eval_size_s19"]["value"] is True
    v0 = authed.get("/api/risk/settings").json()["version"]
    for key, setting, new in (
        ("fade_eval_off", "strategy.pm_fade_cfg.eval_off", False),
        ("noise_lock_alt", "strategy.noise_lock_alt", True),
        ("eval_size_s19", "strategy.eval_size_s19", False),
    ):
        r = authed.put("/api/risk/settings", json={"changes": {setting: new}, "note": "toggle"})
        assert r.status_code == 200, r.text
        assert {t["key"]: t for t in authed.get("/api/strategies").json()["toggles"]}[key]["value"] is new
    assert authed.get("/api/risk/settings").json()["version"] == v0 + 3  # each save is a new version
    st = authed.app.state.rules.rules.strategy
    assert st.noise_profit_lock() == (D(80), D(10)) and not st.eval_size_s19 and not st.pm_fade_cfg.eval_off
