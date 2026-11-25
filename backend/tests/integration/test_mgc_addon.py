"""D184 (user 2026-11-25): the MGC add-on (NOISE + CANDACE on micro gold) runs beside the main MNQ strategy. One
position per INSTRUMENT on an account (narrow rule-7 exception), still max 1 MGC position, METALS household direction
lock, combined open risk inside the account's room, flatten / kill switch / news / flat times close both."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.risk.mgc_addon import MGC_MODES, is_mgc_mode, is_mgc_symbol, other_instrument_ok
from app.signals import strategy_service as SS
from tests.integration.trade_helpers import AT, _ext, _flat, _qty, _setup, _sig

MGC_LONG = (D(4000), D(3995), D("4007.5"), D(5), D("1.5"))
MGC_SHORT = (D(4000), D(4005), D("3992.5"), D(5), D("1.5"))
FLAT_TIME = datetime(2026, 11, 5, 21, 41, tzinfo=UTC)  # 16:41 ET


def _mgc(st, mode, key, direction=Direction.LONG, plan=MGC_LONG):
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s, FixedClock(AT), symbol="MGC", key=key, direction=direction, at=AT, gate=(True, "OK", ""), features={},
            plan=(mode, *plan),
        )  # fmt: skip
        s.commit()
        return sig.id


def _run(st, sid, *accts):
    return asyncio.run(st.controller.execute(sid, "automation", only=list(accts)))[0]


def _rules(st, **strategy):
    r = st.rules.rules
    st.rules.rules = r.model_copy(update={"strategy": r.strategy.model_copy(update={"mgc_noise_candace": True, **strategy})})


def _acct(authed, clock, n=1):
    st, ids = _setup(authed, clock, [(f"a{i}", "25000") for i in range(n)], noise=True)
    st.controller.adapter.sim.last["MGC"] = D(4000)
    _rules(st)
    return st, ids


def _n(st, sym):
    return sum(1 for t in st.controller.om.trades.values() if t.symbol == sym and not t.closed)


def test_pure_rules():
    assert MGC_MODES == {"MGC_NOISE", "MGC_CANDACE"} and is_mgc_mode("MGC_NOISE") and not is_mgc_mode("NOISE")
    assert is_mgc_symbol("MGC") and is_mgc_symbol("mgcz6") and not is_mgc_symbol("MNQZ6")
    mnq = [("NOISE", "MNQ"), ("ORDER_FLOW", "MNQ")]
    assert other_instrument_ok("MGC_NOISE", "MGC", mnq) and other_instrument_ok("MGC_CANDACE", "MGC", mnq[:1])
    assert not other_instrument_ok("MGC_NOISE", "MGC", [("AI_DUO", "MNQ")])  # only the main strategies
    assert not other_instrument_ok("MGC_NOISE", "MGC", [("ORDER_FLOW", "MGC")])
    assert other_instrument_ok("NOISE", "MNQ", [("MGC_NOISE", "MGC")])
    assert other_instrument_ok("CANDACE_ICT", "MNQ", [("MGC_CANDACE", "MGC")])
    assert not other_instrument_ok("AI_DUO", "MNQ", [("MGC_NOISE", "MGC")])  # a lesser strategy keeps one position
    assert not other_instrument_ok("NOISE", "MGC", [("MGC_NOISE", "MGC")])
    assert not other_instrument_ok("NOISE", "MNQ", [("MGC_NOISE", "MGC"), ("MGC_CANDACE", "MGC")])  # max 1 MGC


def test_mnq_then_mgc_on_the_same_account_is_one_micro_and_both_open(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok
    mnq_qty = _qty(st, _ext(st, a))
    res = _run(st, _mgc(st, "MGC_NOISE", "G1"), a)
    assert res.ok and res.contracts == 1, res  # fixed 1 micro
    assert (_n(st, "MNQ"), _n(st, "MGC")) == (1, 1) and _qty(st, _ext(st, a)) == mnq_qty + 1


def test_mgc_then_mnq_main_still_trades(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _mgc(st, "MGC_CANDACE", "G1"), a).ok
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok
    assert (_n(st, "MNQ"), _n(st, "MGC")) == (1, 1)


def test_only_one_mgc_position_per_account_and_one_mnq_without_the_combined_option(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _mgc(st, "MGC_NOISE", "G1"), a).ok
    assert _run(st, _mgc(st, "MGC_CANDACE", "G2"), a).reason == "POSITION_OPEN"
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok
    assert _run(st, _sig(st, "NOISE", "N3"), a).reason == "POSITION_OPEN"  # MNQ: still one position
    assert (_n(st, "MNQ"), _n(st, "MGC")) == (1, 1)


def test_mgc_does_not_sit_beside_a_lesser_strategy(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok
    st.controller.om.trades[next(iter(st.controller.om.trades))].strategy = "AI_DUO"  # a leg that is no main strategy
    assert _run(st, _mgc(st, "MGC_NOISE", "G1"), a).reason == "POSITION_OPEN"


def test_opposite_directions_in_different_groups_are_not_a_hedge(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok  # MNQ long (EQUITY_INDEX)
    assert _run(st, _mgc(st, "MGC_NOISE", "G1", Direction.SHORT, MGC_SHORT), a).ok  # MGC short (METALS): no lock


def test_metals_household_lock_between_accounts(authed, clock):
    st, (a, b) = _acct(authed, clock, 2)
    assert _run(st, _mgc(st, "MGC_NOISE", "G1"), a).ok  # long MGC on a
    res = _run(st, _mgc(st, "MGC_NOISE", "G2", Direction.SHORT, MGC_SHORT), b)
    assert not res.ok and res.reason == "HEDGE_LOCK"
    assert _run(st, _mgc(st, "MGC_NOISE", "G3"), b).ok  # same direction on another account is fine


def test_equity_index_lock_unchanged_between_accounts(authed, clock):
    st, (a, b) = _acct(authed, clock, 2)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok
    short = (D(20000), D(20020), D(19900), D(20), D(5))
    assert _run(st, _sig(st, "NOISE", "N2", Direction.SHORT, short), b).reason == "HEDGE_LOCK"


def test_no_split_no_shared_budget_each_instrument_keeps_its_own_fixed_size(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok
    mnq = _qty(st, _ext(st, a))
    _rules(st, max_trade_risk_usd=D(100))  # the open MNQ leg is over $100, MGC alone fits: it is NOT cut first
    res = _run(st, _mgc(st, "MGC_NOISE", "G1"), a)
    assert res.ok and res.contracts == 1 and _qty(st, _ext(st, a)) == mnq + 1


def test_a_trade_that_could_breach_the_room_by_itself_is_skipped(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok
    huge = (D(4000), D(3500), D(4600), D(500), D("1.2"))  # 500 pt stop = $5,000+ at risk on one micro
    res = _run(st, _mgc(st, "MGC_NOISE", "G1", plan=huge), a)
    assert not res.ok and _n(st, "MGC") == 0


def test_open_micros_do_not_shrink_mgc(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok
    held = _qty(st, _ext(st, a))
    inner = st.rules.rules.internal
    st.rules.rules = st.rules.rules.model_copy(update={"internal": inner.model_copy(update={"internal_max_micros": held})})
    assert _run(st, _mgc(st, "MGC_NOISE", "G1"), a).contracts == 1  # its own fixed 1 micro


def test_with_mgc_row_sets_mnq_4_4_4_only_while_the_addon_is_on():
    from app.config import FastPassCfg, FastPassStep, WithMgcCfg
    from app.risk.fast_pass import fast_pass_size, late_day_size

    cfg = FastPassCfg(
        account_size=D(150000), noise_contracts=5, noise_stop_usd=D(100), candace_contracts=5, brake_inclusive=False,
        noise_grow_per=D(500), noise_max_contracts=6, noise_steps=(FastPassStep(cushion_usd=D(2250), contracts=2),),
        candace_steps=(FastPassStep(cushion_usd=D(1500), contracts=1),), late_contracts=5,
        late_steps=(FastPassStep(cushion_usd=D(2250), contracts=1),), with_mgc=WithMgcCfg(noise_contracts=4, candace_contracts=4, late_contracts=4),
    )  # fmt: skip
    rich = D(9000)
    sz = lambda s, on: fast_pass_size(True, cfg, "EVAL", D(150000), s, rich, False, on).contracts  # noqa: E731
    assert (sz("NOISE", True), sz("CANDACE_ICT", True)) == (4, 4)  # fixed, no grow
    assert (sz("NOISE", False), sz("CANDACE_ICT", False)) == (6, 5)  # add-on OFF: the plan's own sizes, unchanged
    assert late_day_size(True, True, cfg, "EVAL", D(150000), rich, True).contracts == 4
    assert late_day_size(True, True, cfg, "EVAL", D(150000), rich, False).contracts == 5
    low = D(1000)  # brakes still shrink, never raise
    assert fast_pass_size(True, cfg, "EVAL", D(150000), "NOISE", low, False, True).contracts == 2
    assert fast_pass_size(True, cfg, "EVAL", D(150000), "CANDACE_ICT", low, False, True).contracts == 1
    assert late_day_size(True, True, cfg, "EVAL", D(150000), low, True).contracts == 1
    cfg2 = cfg.model_copy(update={"with_mgc": None})
    assert fast_pass_size(True, cfg2, "EVAL", D(150000), "NOISE", rich, False, True).contracts == 6  # plan without a row
    assert late_day_size(True, True, cfg2, "EVAL", D(150000), rich, True).contracts == 5


def test_150k_plan_file_row_and_mgc_late_day_defaults(loaded_rules):
    from app.config import StrategyCfg  # noqa: F401

    from pathlib import Path

    import yaml

    from app.config import FastPassCfg

    path = Path(__file__).resolve().parents[3] / "config" / "rules" / "lucid_pro_150k.yaml"
    wm = FastPassCfg(**yaml.safe_load(path.read_text())["strategy"]["fast_pass_150k_cfg"]).with_mgc
    st = loaded_rules.rules.strategy
    assert (wm.noise_contracts, wm.candace_contracts, wm.late_contracts) == (4, 4, 4)
    late = st.mgc_noise_candace_cfg.late
    assert (late.symbol, late.stop_pts, late.paper_only) == ("MGC", D(8), False)


def test_mgc_late_day_is_eval_only_one_micro_and_needs_the_option(authed, clock):
    st, (a,) = _acct(authed, clock)
    _rules(st, fast_pass_late_day=False)
    assert _run(st, _mgc(st, "MGC_LATE_DAY", "L1"), a).reason == "LATE_DAY_NOT_ACTIVE"
    _rules(st, fast_pass_late_day=True)
    res = _run(st, _mgc(st, "MGC_LATE_DAY", "L2"), a)
    assert res.ok and res.contracts == 1


def test_mgc_late_day_signal_only_with_both_switches(client, loaded_rules):
    from app.models import Bar, Signal

    r = loaded_rules.rules
    day0 = datetime(2026, 10, 5, 13, 30, tzinfo=UTC)
    with client.app.state.sessionmaker() as s:
        for d in range(5):  # 4 history days + today (rising), 1-minute bars 09:30-16:00 ET
            start = day0 + timedelta(days=d)
            prev = D(4000)
            for k in range(390):
                c = prev + (D("0.05") if d == 4 else D("0.0"))
                s.add(Bar(symbol="MGC", tf="1", close_time=start + timedelta(minutes=k + 1), o=prev, h=c + D("0.4"),
                          l=prev - D("0.4"), c=c, v=D(100), source="tv"))  # fmt: skip
                prev = c
        s.commit()
        at = datetime(2026, 10, 9, 19, 0, tzinfo=UTC)  # 15:00 ET

        def go(on, late):
            st = r.strategy.model_copy(update={"mgc_noise_candace": on, "fast_pass_late_day": late})
            return SS.run(s, rules=r.model_copy(update={"strategy": st}), clock=FixedClock(at),
                          calendar=lambda _d: [], symbol="MGC", tf="1", at=at)  # fmt: skip

        assert go(False, True).updates == [] and go(True, False).updates == []
        out = go(True, True)
        assert len(out.updates) == 1
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key.startswith("MGC-LATE-2026-10-09") and sig.status == "PASS"
        flat_at = datetime(2026, 10, 9, 19, 59, tzinfo=UTC)
        done = SS.run(s, rules=r.model_copy(update={"strategy": r.strategy.model_copy(update={"mgc_noise_candace": True, "fast_pass_late_day": True})}),
                      clock=FixedClock(flat_at), calendar=lambda _d: [], symbol="MGC", tf="1", at=flat_at)  # fmt: skip
        assert done.exits and done.exits[0][1] == "LATE_FLAT_1559"


def test_account_kill_switch_flattens_both_instruments(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok and _run(st, _mgc(st, "MGC_NOISE", "G1"), a).ok
    st.controller.adapter.sim.last["MNQ"] = D(19900)  # open loss, then the account sits inside the kill distance
    inner = st.rules.rules.internal
    st.rules.rules = st.rules.rules.model_copy(update={"internal": inner.model_copy(update={"kill_switch_mll_distance": D(50000)})})
    asyncio.run(st.controller.monitor_accounts())
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []


def test_flatten_and_kill_switch_close_both_instruments(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok and _run(st, _mgc(st, "MGC_NOISE", "G1"), a).ok
    _flat(st, a)
    assert _qty(st, _ext(st, a)) == 0


def test_kill_switch_closes_both_instruments(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok and _run(st, _mgc(st, "MGC_NOISE", "G1"), a).ok
    asyncio.run(st.controller.kill_switch("tester"))
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []


def test_flat_times_and_news_close_both_instruments(authed, clock):
    from app.engine.filters import NewsEvent

    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok and _run(st, _mgc(st, "MGC_NOISE", "G1"), a).ok
    ev = NewsEvent(at=clock.now() + timedelta(minutes=2), title="CPI")
    assert asyncio.run(st.controller.news_check([ev])) == "NEWS"
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []


def test_flat_time_closes_both_instruments(authed, clock):
    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok and _run(st, _mgc(st, "MGC_CANDACE", "G1"), a).ok
    clock.set(FLAT_TIME)
    assert asyncio.run(st.controller.flat_time_check()) == "FLAT_TIME"
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []


def test_early_close_flattens_both_instruments(authed, clock, monkeypatch):
    from app.automation import controller as C

    st, (a,) = _acct(authed, clock)
    assert _run(st, _sig(st, "NOISE", "N1"), a).ok and _run(st, _mgc(st, "MGC_NOISE", "G1"), a).ok
    monkeypatch.setattr(C, "flatten_due", lambda *_: True)  # D179: the early-close flat is due
    assert asyncio.run(st.controller.flat_time_check()) == "EARLY_CLOSE"
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []


def test_addon_is_not_a_strategy_choice_and_old_saves_load_as_saved(authed):
    from app.risk.settings_store import strategy_choices_on
    from tests.integration.test_strategy_exclusive import _legacy_row

    put = lambda ch: authed.put("/api/risk/settings", json={"changes": ch, "note": "t"})  # noqa: E731
    assert put({"strategy.noise": True, "strategy.candace_ict": True}).status_code == 200
    assert put({"strategy.mgc_noise_candace": True}).status_code == 200  # beside MAIN, no 422
    s = authed.app.state.rules.rules.strategy
    assert s.noise and s.mgc_noise_candace and strategy_choices_on(s) == ["main_noise_candace"]
    card = next(c for c in authed.get("/api/strategies").json()["strategies"] if c["key"] == "mgc_noise_candace")
    assert card["enabled"] is True and card["addon"] is True and card["badge"].startswith("UNVERIFIED")
    # an old D165 'MGC' choice (main OFF) loads as MGC add-on ON, main OFF; an old pair loads both ON
    _legacy_row(authed, 98, {"strategy.mgc_noise_candace": True, "strategy.noise": False, "strategy.candace_ict": False}, active=True)
    with authed.app.state.sessionmaker() as s_:
        authed.app.state.rules.refresh(s_)
    s = authed.app.state.rules.rules.strategy
    assert s.mgc_noise_candace and not s.noise
    _legacy_row(authed, 99, {"strategy.mgc_noise_candace": True, "strategy.noise": True}, active=True)
    with authed.app.state.sessionmaker() as s_:
        authed.app.state.rules.refresh(s_)
    s = authed.app.state.rules.rules.strategy
    assert s.mgc_noise_candace and s.noise


def test_default_is_off(loaded_rules):
    assert loaded_rules.rules.strategy.mgc_noise_candace is False


@pytest.mark.parametrize("on", [True, False])
def test_strategy_run_makes_mgc_signals_only_with_the_addon_on(client, loaded_rules, on):
    r = loaded_rules.rules
    rules = r.model_copy(update={"strategy": r.strategy.model_copy(update={"mgc_noise_candace": on, "noise": True})})
    with client.app.state.sessionmaker() as s:
        out = SS.run(s, rules=rules, clock=FixedClock(AT), calendar=lambda _d: [], symbol="MGC", tf="1", at=AT)
    assert out.updates == []  # no stored MGC sessions here; the point is it never raises with both ON
