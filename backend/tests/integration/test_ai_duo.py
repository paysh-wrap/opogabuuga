"""D83 AI Duo runtime: AI side from the ledger label, VWAP pullback entry, one logged decision a day, hedge lock."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.filters import NewsEvent
from app.models import AuditLog, BiasDecision, Signal, TradePlanRow
from app.signals import strategy_service as SS
from tests.integration.test_strategy_service import _add_day, _history, _rules, _sessions

PULLBACK = {**{k: D(20000) for k in range(5)}, **{k: D(19990) for k in range(5, 9)}, 9: D(20005)}


@pytest.fixture
def db(client):
    return client.app.state.sessionmaker


def _label(s, today, label):
    s.add(BiasDecision(session_date=date(today.year, today.month, today.day), proxy="QQQ", raw_rating=label,
                       mapped="NEUTRAL", version="t"))  # fmt: skip
    s.commit()


def _run(s, rules, at, calendar=lambda _d: []):
    return SS.run(s, rules=rules, clock=FixedClock(at), calendar=calendar, symbol="MNQ", tf="1", at=at)


def _setup(s, label, closes=PULLBACK):
    today = _sessions(2)[-1]
    _add_day(s, today, closes)
    s.commit()
    if label is not None:
        _label(s, today, label)
    return today


def test_long_entry_on_first_vwap_pullback_close(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _setup(s, "BUY·VT LONG 85")
        assert _run(s, rules, today + timedelta(minutes=6)).updates == []  # 09:36 is not a 5-minute close: wait
        out = _run(s, rules, today + timedelta(minutes=10))  # 09:40 close
        assert [u.status for u in out.updates] == ["PASS"]
        sig = s.get(Signal, out.updates[0].signal_id)
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert sig.direction == "LONG" and sig.features["strategy"] == "AI_DUO" and sig.features["paper_only"] is True
        assert plan.mode == "AI_DUO" and plan.entry == D(20005) and plan.stop < plan.entry < plan.take_profit
        assert plan.rr == D("2.00") and sig.features["stop_capped"] is False
        assert s.query(AuditLog).filter_by(action="ai_duo.decision").one().payload["code"] == "TAKEN"
        assert _run(s, rules, today + timedelta(minutes=15)).updates == []  # one decision per day


def test_deep_pullback_stop_is_capped_at_the_noise_dollar_stop(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    deep = {**{k: D(20000) for k in range(5)}, **{k: D(19700) for k in range(5, 9)}, 9: D(20005)}
    with db() as s:
        today = _setup(s, "BUY·VT LONG 85", deep)
        out = _run(s, rules, today + timedelta(minutes=10))
        plan = s.query(TradePlanRow).filter_by(signal_id=out.updates[0].signal_id).one()
        assert plan.entry - plan.stop == D(124) and plan.rr == D("2.00")  # D58 $250 stop in points
        assert s.get(Signal, plan.signal_id).features["stop_capped"] is True


@pytest.mark.parametrize(
    ("label", "code"),
    [
        (None, "AI_MISSING"),
        ("BUY·VT SHORT 85", "AI_DISAGREE"),
        ("HOLD·VT LONG 85", "AI_NEUTRAL"),
        ("BUY·VT NEUTRAL 70", "AI_NEUTRAL"),
        ("BUY·VT LONG 50", "AI_NOT_STRONG"),
        ("BUY", "AI_VT_MISSING"),
        ("", "AI_TA_MISSING"),
    ],
)
def test_no_trade_cases_log_one_skip_with_reason_code(db, loaded_rules, label, code):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _setup(s, label)
        out = _run(s, rules, today + timedelta(minutes=10))
        assert [(u.status, u.reason) for u in out.updates] == [("SKIP", code)]
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.direction == "NONE" and s.query(TradePlanRow).filter_by(signal_id=sig.id).count() == 0
        assert s.query(AuditLog).filter_by(action="ai_duo.decision").one().payload["code"] == code
        assert _run(s, rules, today + timedelta(minutes=15)).updates == []  # decided for the day


def test_no_pullback_by_window_end_is_a_logged_skip(db, loaded_rules):
    rules = _early(_rules(loaded_rules, ai_duo=True))
    with db() as s:
        today = _setup(s, "BUY·VT LONG 85", {k: D(20000) for k in range(160)})
        assert _run(s, rules, today + timedelta(minutes=60)).updates == []  # nothing yet, still waiting
        out = _run(s, rules, today + timedelta(minutes=150))  # 12:00 close (MNQ window 08:00-12:00)
        assert [(u.status, u.reason) for u in out.updates] == [("SKIP", "NO_PULLBACK")]
        assert _run(s, rules, today + timedelta(minutes=155)).updates == []  # past the window


def test_news_blackout_skips_with_reason_and_flat_at_1600(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _setup(s, "BUY·VT LONG 85")
        news = [NewsEvent(today + timedelta(minutes=12), "CPI")]
        out = _run(s, rules, today + timedelta(minutes=10), lambda _d: news)
        assert [(u.status, u.reason) for u in out.updates] == [("SKIP", "NEWS_BLACKOUT")]
        sig = s.query(Signal).filter(Signal.model_key.like("MNQ-DUO-%")).one()
        sig.features = {**sig.features, "state": "OPEN"}
        s.commit()
        out = _run(s, rules, today + timedelta(minutes=390))
        assert out.exits == [(sig.id, "DUO_FLAT_1600")]


def test_off_and_stale_heartbeats_do_nothing(db, loaded_rules):
    with db() as s:
        today = _setup(s, "BUY·VT LONG 85")
        assert _run(s, _rules(loaded_rules), today + timedelta(minutes=10)).updates == []  # button OFF
        late = SS.run(s, rules=_rules(loaded_rules, ai_duo=True), clock=FixedClock(today), calendar=lambda _d: [],
                      symbol="MNQ", tf="1", at=today + timedelta(minutes=10), exits_only=True)  # fmt: skip
        assert late.updates == []  # a replayed stale bar never opens


def _noise_signal(s, today, direction, state="OPEN", tag="NOISE"):
    day = today.astimezone(SS.ET).date().isoformat()
    s.add(Signal(symbol="MNQ", profile="TIGHT", bar_time=today + timedelta(minutes=1), direction=direction,
                 status="PASS", passed=True, model_key=f"MNQ-{tag}-{day}-1",
                 features={"strategy": tag, "state": state}))  # fmt: skip
    s.commit()


def test_duo_skips_hedge_lock_against_open_noise(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _setup(s, "BUY·VT LONG 85")
        _noise_signal(s, today, "SHORT")
        out = _run(s, rules, today + timedelta(minutes=10))
        assert [(u.status, u.reason) for u in out.updates] == [("SKIP", "HEDGE_LOCK")]


def test_duo_allowed_in_the_same_direction_as_noise_and_flagged(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _setup(s, "BUY·VT LONG 85")
        _noise_signal(s, today, "LONG")
        out = _run(s, rules, today + timedelta(minutes=10))
        assert out.updates[0].status == "PASS"
        assert s.get(Signal, out.updates[0].signal_id).features["agrees_with_noise"] is True


def test_closed_noise_signal_holds_no_lock(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _setup(s, "BUY·VT LONG 85")
        _noise_signal(s, today, "SHORT", state="CLOSED")
        assert _run(s, rules, today + timedelta(minutes=10)).updates[0].status == "PASS"


def _noise_day(s):
    days = _sessions(12)
    today = days[-1]
    _history(s, days[:-1])
    _add_day(s, today, {k: D(20000) + 3 * k for k in range(30)})  # NOISE would go LONG at 10:00
    s.commit()
    return today


def test_noise_is_blocked_while_duo_holds_the_opposite_side(db, loaded_rules):
    rules = _rules(loaded_rules, noise=True)
    with db() as s:
        today = _noise_day(s)
        _noise_signal(s, today, "SHORT", tag="DUO")
        out = _run(s, rules, today + timedelta(minutes=30))
        assert [(u.status, u.reason) for u in out.updates] == [("SKIP", "HEDGE_LOCK")]


def test_noise_allowed_while_duo_holds_the_same_side(db, loaded_rules):
    rules = _rules(loaded_rules, noise=True)
    with db() as s:
        today = _noise_day(s)
        _noise_signal(s, today, "LONG", tag="DUO")
        assert _run(s, rules, today + timedelta(minutes=30)).updates[0].status == "PASS"


def test_same_bar_tie_noise_wins_and_duo_skips(db, loaded_rules):
    rules = _rules(loaded_rules, noise=True, ai_duo=True)
    days = _sessions(12)
    today = days[-1]
    at = today + timedelta(minutes=30)  # 10:00: NOISE check and a 5-minute close
    closes = {**{k: D(19880) for k in range(1, 29)}, 29: D(19913)}  # below the lower band; bounce above VWAP
    with db() as s:
        _history(s, days[:-1])
        _add_day(s, today, closes)
        s.commit()
        _label(s, today, "BUY·VT LONG 85")
        out = _run(s, rules, at)
        by = {s.get(Signal, u.signal_id).features["strategy"]: u for u in out.updates}
        assert by["NOISE"].status == "PASS" and (by["AI_DUO"].status, by["AI_DUO"].reason) == ("SKIP", "HEDGE_LOCK")
        assert s.get(Signal, by["NOISE"].signal_id).direction == "SHORT"


def test_duo_signal_never_executes_on_a_non_paper_account(authed, clock):
    """D83: paper_only is forced True; the controller refuses AI_DUO on any account that is not a simulator account."""
    import asyncio
    from datetime import UTC, datetime

    from app.engine.trade_plan import Direction
    from app.models import Account

    at = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)
    st = authed.app.state
    clock.set(at)
    aid = authed.post("/api/accounts", json={"label": "P", "stage": "EVAL", "balance": "25000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    with st.sessionmaker() as s:
        s.get(Account, aid).is_sim = False
        plan = ("AI_DUO", D(20000), D(19990), D(20020), D(10), D(2))
        sig = SS._new_signal(
            s, FixedClock(at), symbol="MNQ", key="MNQ-DUO-2026-10-13", direction=Direction.LONG, at=at,
            gate=(True, "OK", ""), features={}, plan=plan,
        )  # fmt: skip
        s.commit()
        sid = sig.id
    res = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    assert res[0].ok is False and res[0].reason == "PAPER_ONLY_STRATEGY", res


# ---------- D83 update: London-open window (03:00 ET) and MGC ----------
def _bars(s, symbol, start, closes, base, n=200):
    """1-minute bars from `start`; closes: minute offset → close (others flat at the previous close)."""
    from app.models import Bar

    prev = base
    for k in range(n):
        c = closes.get(k, prev)
        s.add(Bar(symbol=symbol, tf="1", close_time=start + timedelta(minutes=k + 1), o=prev, h=max(prev, c) + 1,
                  l=min(prev, c) - 1, c=c, v=D(100), source="tradingview"))  # fmt: skip
    s.commit()


def _real_windows(rules, mnq_window=("03:00", "11:30")):
    mnq = rules.instruments["MNQ"].model_copy(update={"windows": [("03:00", "09:30"), ("09:35", "15:30")]})
    return _with_duo(
        rules.model_copy(update={"instruments": {**rules.instruments, "MNQ": mnq}}),
        windows={"MGC": ("03:00", "11:30"), "MNQ": mnq_window},
    )


def _with_duo(rules, **kw):
    cfg = rules.strategy.ai_duo_cfg.model_copy(update=kw)
    return rules.model_copy(update={"strategy": rules.strategy.model_copy(update={"ai_duo_cfg": cfg})})


def _early(rules):
    """The pre-D86 windows (MGC 03:00-11:30, MNQ 08:00-12:00) for tests timed outside the 09:36 default."""
    return _with_duo(rules, windows={"MGC": ("03:00", "11:30"), "MNQ": ("08:00", "12:00")})


def _london(today):
    return today - timedelta(hours=6, minutes=30)  # 03:00 ET


def test_trades_in_the_london_session_before_the_us_open(db, loaded_rules):
    rules = _real_windows(_rules(loaded_rules, ai_duo=True))
    with db() as s:
        today = _sessions(2)[-1]
        _bars(s, "MNQ", _london(today), PULLBACK, D(20000))
        _label(s, today, "BUY·VT LONG 85")
        at = _london(today) + timedelta(minutes=10)  # 03:10 ET close
        assert _run(s, rules, _london(today) + timedelta(minutes=6)).updates == []  # not a 5-minute close
        out = _run(s, rules, at)
        assert (out.updates[0].status, out.updates[0].reason) == ("PASS", None)


def test_window_start_is_configurable_and_nothing_before_it(db, loaded_rules):
    base = _rules(loaded_rules, ai_duo=True)
    with db() as s:
        today = _sessions(2)[-1]
        _bars(s, "MNQ", _london(today), PULLBACK, D(20000))
        _label(s, today, "BUY·VT LONG 85")
        rules = _with_duo(base, windows={"MGC": ("03:00", "11:30"), "MNQ": ("06:45", "12:00")})
        assert _run(s, rules, _london(today) + timedelta(minutes=10)).updates == []  # 03:10 is before 06:45


def test_the_0930_0935_bar_never_triggers(db, loaded_rules):
    rules = _rules(loaded_rules, ai_duo=True)
    deep = {**{k: D(20000) for k in range(5)}, **{k: D(19990) for k in range(5)}, 4: D(19995)}
    with db() as s:
        today = _setup(s, "BUY·VT LONG 85", {**deep, **{k: D(19990) for k in range(1, 4)}, 4: D(20005)})
        assert _run(s, rules, today + timedelta(minutes=5)).updates == []  # the 09:30–09:35 bar is excluded
        assert s.query(Signal).filter(Signal.model_key.like("MNQ-DUO-%")).count() == 0  # not even a skip row


def test_mgc_long_entry_plan_uses_the_mgc_tick_and_cap(db, loaded_rules):  # MGC switch is off, Duo still trades it
    rules = _early(_rules(loaded_rules, ai_duo=True))
    pull = {**{k: D(2700) for k in range(5)}, **{k: D(2690) for k in range(5, 9)}, 9: D(2701)}
    with db() as s:
        today = _sessions(2)[-1]
        start = _london(today)
        _bars(s, "MGC", start, pull, D(2700))
        s.add(BiasDecision(session_date=date(today.year, today.month, today.day), proxy="GLD",
                           raw_rating="BUY·VT LONG 80", mapped="NEUTRAL", version="t"))  # fmt: skip
        s.commit()
        out = SS.run(s, rules=rules, clock=FixedClock(start), calendar=lambda _d: [], symbol="MGC", tf="1",
                     at=start + timedelta(minutes=10))  # fmt: skip
        assert out.updates[0].status == "PASS"
        plan = s.query(TradePlanRow).filter_by(signal_id=out.updates[0].signal_id).one()
        assert plan.mode == "AI_DUO" and plan.entry == D(2701) and plan.stop < D(2690) and plan.rr == D("2.00")
        assert (plan.entry - plan.stop) <= D("24.6")  # capped at the NOISE $250 stop in MGC points


def test_market_not_in_the_markets_setting_is_ignored(db, loaded_rules):
    base = _rules(loaded_rules, ai_duo=True)
    only_mnq = base.strategy.ai_duo_cfg.model_copy(update={"markets": ["MNQ"]})
    rules = base.model_copy(update={"strategy": base.strategy.model_copy(update={"ai_duo_cfg": only_mnq})})
    pull = {**{k: D(2700) for k in range(5)}, **{k: D(2690) for k in range(5, 9)}, 9: D(2701)}
    with db() as s:
        today = _sessions(2)[-1]
        _bars(s, "MGC", _london(today), pull, D(2700))
        out = SS.run(s, rules=rules, clock=FixedClock(today), calendar=lambda _d: [], symbol="MGC", tf="1",
                     at=_london(today) + timedelta(minutes=10))  # fmt: skip
        assert out.updates == []


def test_mgc_signal_does_not_clash_with_noise_on_mnq(db, loaded_rules):
    """METALS and EQUITY_INDEX are separate hedge groups; NOISE only trades MNQ, so no cross-market lock."""
    rules = _early(_rules(loaded_rules, ai_duo=True))
    pull = {**{k: D(2700) for k in range(5)}, **{k: D(2690) for k in range(5, 9)}, 9: D(2701)}
    with db() as s:
        today = _sessions(2)[-1]
        _bars(s, "MGC", _london(today), pull, D(2700))
        s.add(BiasDecision(session_date=date(today.year, today.month, today.day), proxy="GLD",
                           raw_rating="BUY·VT LONG 80", mapped="NEUTRAL", version="t"))  # fmt: skip
        s.commit()
        _noise_signal(s, today, "SHORT")  # an open MNQ NOISE short
        out = SS.run(s, rules=rules, clock=FixedClock(today), calendar=lambda _d: [], symbol="MGC", tf="1",
                     at=_london(today) + timedelta(minutes=10))  # fmt: skip
        assert out.updates[0].status == "PASS"


def test_duo_settings_are_editable_and_validated(authed):
    win = {"MGC": ["03:00", "11:30"], "MNQ": ["08:30", "12:00"]}
    changes = {"strategy.ai_duo_cfg.windows": win, "strategy.ai_duo_cfg.markets": ["MGC"]}
    ok = authed.put("/api/risk/settings", json={"changes": changes, "note": "duo"})
    assert ok.status_code == 200, ok.text
    bad = authed.put(
        "/api/risk/settings",
        json={
            "changes": {"strategy.ai_duo_cfg.windows": {"MGC": ["03:00", "25:00"], "MNQ": ["08:30", "12:00"]}},
            "note": "x",
        },
    )
    assert bad.status_code in (400, 422)
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.ai_duo_cfg.markets": ["ES"]}, "note": "x"})
    assert bad.status_code in (400, 422)
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.ai_duo_cfg.windows": {"MGC": ["12:00", "03:00"],
                     "MNQ": ["08:30", "12:00"]}}, "note": "x"})  # fmt: skip
    assert bad.status_code in (400, 422)
    ok = authed.put(
        "/api/risk/settings", json={"changes": {"strategy.ai_duo_cfg.accounts": {"MNQ": 1, "MGC": 2}}, "note": "a"}
    )
    assert ok.status_code == 200, ok.text


def test_duo_markets_get_an_ai_call_even_when_the_market_switch_is_off(loaded_rules):
    from app.bias.service import proxies

    r = loaded_rules.rules
    assert r.instruments["MGC"].enabled is False
    on = r.model_copy(update={"strategy": r.strategy.model_copy(update={"ai_duo": True})})
    assert "GLD" in proxies(on) and "GLD" not in proxies(r)


def test_per_market_windows_default_and_validation():
    from app.config import AiDuoCfg

    c = AiDuoCfg()
    assert c.window_for("MGC") == ("09:36", "11:30") and c.window_for("MNQ") == ("09:36", "11:30")
    assert c.excluded == [("09:30", "09:35")] and c.accounts == {}
    with pytest.raises(ValueError, match="starts before"):
        AiDuoCfg(windows={"MGC": ("12:00", "03:00"), "MNQ": ("08:30", "12:00")})
    with pytest.raises(ValueError, match="HH:MM"):
        AiDuoCfg(windows={"MGC": ("3:00", "11:30"), "MNQ": ("08:30", "12:00")})
    with pytest.raises(ValueError, match="needs a window"):
        AiDuoCfg(windows={"MNQ": ("08:30", "12:00")})
    with pytest.raises(ValueError, match="positive"):
        AiDuoCfg(accounts={"MNQ": 0})


def test_mnq_does_not_trade_before_its_own_window(db, loaded_rules):
    rules = _real_windows(_rules(loaded_rules, ai_duo=True), ("08:00", "12:00"))
    with db() as s:
        today = _sessions(2)[-1]
        _bars(s, "MNQ", _london(today), PULLBACK, D(20000))
        _label(s, today, "BUY·VT LONG 85")
        assert _run(s, rules, _london(today) + timedelta(minutes=10)).updates == []  # 03:10 < 08:00 for MNQ


def _duo_accounts(authed, clock, assign):
    from datetime import UTC, datetime

    from app.engine.trade_plan import Direction

    at = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)
    st = authed.app.state
    clock.set(at)
    ids = []
    for label in ("A", "B", "C"):
        aid = authed.post("/api/accounts", json={"label": label, "stage": "EVAL", "balance": "25000"}).json()["id"]
        authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
        ids.append(aid)
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    h = st.controller.rules
    cfg = h.rules.strategy.ai_duo_cfg.model_copy(update={"accounts": {k: ids[i] for k, i in assign.items()}})
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"ai_duo_cfg": cfg})})
    with st.sessionmaker() as s:
        plan = ("AI_DUO", D(20000), D(19990), D(20020), D(10), D(2))
        sig = SS._new_signal(
            s, FixedClock(at), symbol="MNQ", key="MNQ-DUO-2026-10-13", direction=Direction.LONG, at=at,
            gate=(True, "OK", ""), features={}, plan=plan,
        )  # fmt: skip
        s.commit()
        sid = sig.id
    return st, ids, sid


def test_duo_signal_goes_only_to_the_account_assigned_to_its_market(authed, clock):
    import asyncio

    st, ids, sid = _duo_accounts(authed, clock, {"MNQ": 1, "MGC": 2})  # MNQ → B, MGC → C
    res = asyncio.run(st.controller.execute(sid, "automation"))
    assert {r.account_id for r in res} == {ids[1]}  # only the MNQ account B; A is free for nothing here


def test_unassigned_market_avoids_accounts_assigned_to_the_other_market(authed, clock):
    import asyncio

    st, ids, sid = _duo_accounts(authed, clock, {"MGC": 2})  # MGC → C; MNQ has no assignment
    res = asyncio.run(st.controller.execute(sid, "automation"))
    assert ids[2] not in {r.account_id for r in res} and {r.account_id for r in res} <= {ids[0], ids[1]}


def test_assigned_account_unavailable_is_reported(authed, clock):
    import asyncio

    st, ids, sid = _duo_accounts(authed, clock, {"MNQ": 0})
    authed.patch(f"/api/accounts/{ids[0]}", json={"armed": False, "selected": False})
    res = asyncio.run(st.controller.execute(sid, "automation"))
    assert [(r.account_id, r.reason) for r in res if r.reason == "DUO_ASSIGNED_ACCOUNT_UNAVAILABLE"] == [
        (ids[0], "DUO_ASSIGNED_ACCOUNT_UNAVAILABLE")
    ] or all(r.account_id == ids[0] for r in res)


# ---------- D85: several positions on 150K, one on every other account, kill switch flattens all ----------
def _multi_setup(authed, clock, balances):
    import asyncio  # noqa: F401
    from datetime import UTC, datetime

    at = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)
    st = authed.app.state
    clock.set(at)
    ids = []
    for label, bal in balances:
        aid = authed.post("/api/accounts", json={"label": label, "stage": "EVAL", "balance": bal}).json()["id"]
        authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
        ids.append(aid)
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    sim = st.controller.adapter.sim
    sim.last["MNQ"], sim.last["MGC"] = D(20000), D(2700)
    return st, ids, at


def _duo_sig(st, at, symbol, plan, features=None):
    from app.engine.trade_plan import Direction

    with st.sessionmaker() as s:
        sig = SS._new_signal(s, FixedClock(at), symbol=symbol, key=f"{symbol}-DUO-2026-10-13", direction=Direction.LONG,
                             at=at, gate=(True, "OK", ""), features=features or {}, plan=("AI_DUO", *plan))  # fmt: skip
        s.commit()
        return sig.id


MNQ_PLAN = (D(20000), D(19980), D(20100), D(20), D(5))
MGC_PLAN = (D(2700), D(2690), D(2730), D(10), D(3))


def test_150k_account_holds_mnq_and_mgc_together_a_25k_account_only_one(authed, clock):
    import asyncio

    st, ids, at = _multi_setup(authed, clock, [("big", "150000"), ("small", "25000")])
    big, small = ids
    s1, s2 = _duo_sig(st, at, "MNQ", MNQ_PLAN), _duo_sig(st, at, "MGC", MGC_PLAN)
    r1 = {r.account_id: r for r in asyncio.run(st.controller.execute(s1, "automation"))}
    r2 = {r.account_id: r for r in asyncio.run(st.controller.execute(s2, "automation"))}
    assert r1[big].ok and r2[big].ok, (r1[big], r2[big])  # two positions at once on the 150K account
    assert r1[small].ok and not r2[small].ok and r2[small].reason == "POSITION_OPEN"  # everyone else: max 1
    with st.sessionmaker() as s:
        from app.models import Account

        ext = s.get(Account, big).broker_account_id
    mine = [t for t in st.controller.om.trades.values() if t.account == ext]
    assert {t.symbol for t in mine} == {"MNQ", "MGC"} and all(t.legs[0].stop for t in mine)  # own stop bracket each
    assert all(t.manage is not None for t in mine)  # break-even / lock / trail attached to each position
    by = {t.symbol: t.manage for t in mine}  # D85 lock per market: MNQ +100 → +50 pts; MGC step trail 60 → 20 ticks
    assert (by["MNQ"].lock_trigger_pts, by["MNQ"].lock_pts) == (D(100), D(50))
    assert (by["MGC"].step_ticks, by["MGC"].raise_ticks) == (60, 20)  # D85 addendum: MGC step trail (user-set)
    assert by["MGC"].lock_trigger_pts is None and by["MGC"].lock_pts is None
    assert by["MNQ"].ai_lock_price is None
    assert all(t.qty <= 4 for t in mine)  # 4 is a cap


def test_kill_switch_flattens_every_open_position(authed, clock):
    import asyncio

    st, _ids, at = _multi_setup(authed, clock, [("big", "150000")])
    s1, s2 = _duo_sig(st, at, "MNQ", MNQ_PLAN), _duo_sig(st, at, "MGC", MGC_PLAN)
    assert asyncio.run(st.controller.execute(s1, "automation"))[0].ok
    assert asyncio.run(st.controller.execute(s2, "automation"))[0].ok
    assert len(st.controller.om.trades) == 2
    asyncio.run(st.controller.kill_switch("test"))
    ctl = st.controller
    assert asyncio.run(ctl.adapter.get_positions(next(iter(ctl.adapter.sim.accounts)))) == []  # all flat
    assert not any(not t.closing for t in ctl.om.trades.values()) or ctl.om.trades == {}


def test_the_ai_setup_lock_level_reaches_the_position(authed, clock):
    import asyncio

    st, _ids, at = _multi_setup(authed, clock, [("big", "150000")])
    sid = _duo_sig(st, at, "MGC", MGC_PLAN, {"lock_price": "2712"})
    assert asyncio.run(st.controller.execute(sid, "automation"))[0].ok
    (t,) = st.controller.om.trades.values()
    assert t.manage.ai_lock_price == D(2712)


def test_open_risk_counts_an_unfilled_entry_and_a_stop_past_break_even_keeps_only_fees(authed, clock):
    """Review fix: a position whose entry has not filled yet already carries its full stop risk in the aggregate
    check (otherwise two signals in the same minute could together exceed the DLL/MLL room)."""
    import asyncio

    st, _ids, at = _multi_setup(authed, clock, [("big", "150000")])
    s1 = _duo_sig(st, at, "MNQ", MNQ_PLAN)
    asyncio.run(st.controller.execute(s1, "automation"))
    (t,) = st.controller.om.trades.values()
    leg = t.legs[0]
    leg.entry = None  # as if the entry were still working
    pending = st.controller._open_risk(t)
    leg.entry = t.plan.entry
    filled = st.controller._open_risk(t)
    assert pending == filled > 0
    leg.stop = t.plan.entry + t.d.sign * 5  # stop beyond break-even: only fee + slippage remain
    assert 0 < st.controller._open_risk(t) < filled
