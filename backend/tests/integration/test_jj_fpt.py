"""JJ F.P.T STRAT end to end: stored 1-minute bars → signal (strategy_service) → controller size and account choice."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.filters import NewsEvent
from app.engine.trade_plan import Direction
from app.models import AuditLog, Bar, Signal, TradePlanRow
from app.signals import strategy_service as SS

NY = datetime(2026, 10, 13, 13, 30, tzinfo=UTC)  # Tue 09:30 ET (EDT)


def _rules(loaded_rules, **cfg):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    jj = r.strategy.jj_fpt_cfg.model_copy(update=cfg)
    st = r.strategy.model_copy(update={"jj_fpt": True, "jj_fpt_cfg": jj})
    return r.model_copy(update={"strategy": st, "instruments": {**r.instruments, "MNQ": mnq}})


def _bar(s, close_time, o, h, lo, c):
    s.add(Bar(symbol="MNQ", tf="1", close_time=close_time, o=D(o), h=D(h), l=D(lo), c=D(c), v=D(100), source="tv"))


@pytest.fixture
def db(client):
    return client.app.state.sessionmaker


def _run(s, rules, at, cal=lambda _d: []):
    return SS.run(s, rules=rules, clock=FixedClock(at), calendar=cal, symbol="MNQ", tf="1", at=at)


def test_opening_continuation_signal_25_38(db, loaded_rules):
    rules = _rules(loaded_rules, htf_filter=False)
    with db() as s:
        _bar(s, NY, 20000, 20001, 19999, 20000)  # 09:29 bar
        _bar(s, NY + timedelta(minutes=1), 20000, 20010, 19999.5, 20008)  # opening candle: green, breaks 20001
        s.commit()
        out = _run(s, rules, NY + timedelta(minutes=1))
        assert len(out.updates) == 1 and out.updates[0].status == "PASS"
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MNQ-JJ-2026-10-13-NY-0931" and sig.features["entry_kind"] == "CONTINUATION"
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "JJ_FPT" and (plan.stop, plan.take_profit) == (D(19983), D(20046))
        assert _run(s, rules, NY + timedelta(minutes=1)).updates == []  # same bar again → stored once


def test_off_when_the_button_is_off(db, loaded_rules):
    rules = _rules(loaded_rules)
    rules = rules.model_copy(update={"strategy": rules.strategy.model_copy(update={"jj_fpt": False})})
    with db() as s:
        _bar(s, NY, 20000, 20001, 19999, 20000)
        _bar(s, NY + timedelta(minutes=1), 20000, 20010, 19999.5, 20008)
        s.commit()
        assert _run(s, rules, NY + timedelta(minutes=1)).updates == []


def test_news_session_reverts_to_the_pre_news_price_and_respects_the_blackout(db, loaded_rules):
    rules = _rules(loaded_rules)
    news = NY - timedelta(hours=1)  # 08:30 ET
    cal = lambda _d: [NewsEvent(news, "CPI")]  # noqa: E731
    with db() as s:
        _bar(s, news, 20000, 20001, 19999, 20000)
        _bar(s, news + timedelta(minutes=1), 20000, 20060, 19999, 20050)  # the news candle (no continuation)
        _bar(s, news + timedelta(minutes=2), 20050, 20056, 20049, 20055)  # green
        _bar(s, news + timedelta(minutes=3), 20055, 20055, 20040, 20041)  # red displacement, 41 pt above 20000
        s.commit()
        out = _run(s, rules, news + timedelta(minutes=3), cal)
        assert len(out.updates) == 1
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.features["session"] == "NEWS" and sig.direction == "SHORT" and sig.features["fair"] == "20000"
        # minute 3 is inside the Lucid news window → stored as a SKIP, never traded
        if rules.eval.news_breach_min_after >= 3:
            assert sig.status == "SKIP" and sig.skip_reason == "NEWS_BLACKOUT"
    assert SS.jj_sessions(rules, news + timedelta(minutes=3), lambda _d: []) == []  # no news → no news session


def _setup_accounts(authed, clock, stages):
    st = authed.app.state
    clock.set(NY + timedelta(minutes=10))
    ids = []
    for i, stage in enumerate(stages):
        aid = authed.post("/api/accounts", json={"label": f"A{i}", "stage": stage, "balance": "25000"}).json()["id"]
        assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
        ids.append(aid)
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"jj_fpt": True})})
    return st, ids


def _signal(st, kind, stop_pts=D(25)):
    at = NY + timedelta(minutes=10)
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s, FixedClock(at), symbol="MNQ", key=f"MNQ-JJ-2026-10-13-NY-0940-{kind}", direction=Direction.SHORT, at=at,
            gate=(True, "OK", ""), features={"entry_kind": kind},
            plan=("JJ_FPT", D(20040), D(20040) + stop_pts, D(20002), stop_pts, D("1.52")),
        )  # fmt: skip
        s.commit()
        return sig.id


def test_controller_one_account_per_trade_and_same_dollar_size(authed, clock):
    st, ids = _setup_accounts(authed, clock, ["EVAL", "EVAL"])
    res = asyncio.run(st.controller.execute(_signal(st, "DISPLACEMENT"), "automation", only=ids))
    assert len(res) == 1  # JJ #30: one account, never copy trading
    with st.sessionmaker() as s:
        rows = [x.payload for x in s.query(AuditLog).filter_by(action="trade.jj_size")]
    # D143 (changed assertion, was $250 / 4 micros): 25% of the $1,000 drawdown = $250, but JJ's 3-loss session must
    # fit the $475 consistency day stop → $158.33; 25 pt MNQ = $50 + fee + slippage ($52) → 3 micros
    assert rows and rows[0]["risk_usd"] == "158.33" and rows[0]["contracts"] == 3
    assert rows[0]["drawdown_type"] == "eod"  # EOD account: sized on room above the EOD-trailed MLL


def test_controller_funded_takes_breaks_of_structure_only(authed, clock):
    st, ids = _setup_accounts(authed, clock, ["FUNDED"])
    res = asyncio.run(st.controller.execute(_signal(st, "DISPLACEMENT"), "automation", only=ids))
    assert [r.reason for r in res] == ["JJ_FUNDED_BOS_ONLY"]
    res = asyncio.run(st.controller.execute(_signal(st, "BREAK_OF_STRUCTURE"), "automation", only=ids))
    assert all(r.reason != "JJ_FUNDED_BOS_ONLY" for r in res)


@pytest.mark.parametrize("k", [25, 50, 100, 150])
def test_news_gate_blocks_the_lucid_news_window_on_pro_plans(k):
    from app.config import load_rules
    from app.settings import REPO_ROOT

    r = load_rules(REPO_ROOT / "config" / "rules" / f"lucid_pro_{k}k.yaml").rules
    r = r.model_copy(
        update={"instruments": {**r.instruments, "MNQ": r.instruments["MNQ"].model_copy(update={"enabled": True})}}
    )
    news = NY - timedelta(hours=1)  # 08:30 ET red folder
    cal = lambda _d: [NewsEvent(news, "CPI")]  # noqa: E731
    before = max(r.internal.no_entry_before_news_min, r.funded.news_breach_min_before)
    after = max(r.eval.news_breach_min_after, r.funded.news_breach_min_after)  # funded news = hard breach window
    for at in (news - timedelta(minutes=before), news, news + timedelta(minutes=after)):
        assert SS._jj_gate(r, at, cal)[:2] == (False, "NEWS_BLACKOUT")
    assert SS._jj_gate(r, news + timedelta(minutes=after + 1), cal)[:2] == (True, "OK")
    assert SS._jj_gate(r, news - timedelta(minutes=before + 1), cal)[:2] == (True, "OK")


def test_card_size_row_shows_the_lucid_fit_for_the_active_plan():
    from app.api.dashboard import jj_rules
    from app.config import load_rules
    from app.settings import REPO_ROOT

    r = load_rules(REPO_ROOT / "config" / "rules" / "lucid_pro_50k.yaml").rules
    size = next(x for x in jj_rules(r) if x["key"] == "SIZE")["rule"]
    assert "$360.00 per trade" in size and "6 micros at 25 pt / 13 at 12.5 pt" in size and "max 3 losses" in size
    assert "EOD drawdown" in size
