"""GALA PRICE ACTION (D144) end to end: stored 1-minute bars → signal → controller Lucid-fit size and skip codes."""

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
from tests.unit.test_gala_pa import history, today_break_retest

AT = datetime(2026, 10, 13, 13, 45, tzinfo=UTC)  # Tue 09:45 ET: the retest candle closes


def _rules(loaded_rules, **cfg):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    g = r.strategy.gala_pa_cfg.model_copy(update={"pivot_lookback": 1, "trend_swing_lookback": 1, **cfg})
    st = r.strategy.model_copy(update={"gala_pa": True, "gala_pa_cfg": g})
    return r.model_copy(update={"strategy": st, "instruments": {**r.instruments, "MNQ": mnq}})


@pytest.fixture
def db(client):
    return client.app.state.sessionmaker


def _store(s):
    for b in history() + today_break_retest([(117, 117.5, 116.5, 117)] * 13):
        s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                  v=D(100), source="tv"))  # fmt: skip
    s.commit()


def _run(s, rules, at, cal=lambda _d: []):
    return SS.run(s, rules=rules, clock=FixedClock(at), calendar=cal, symbol="MNQ", tf="1", at=at)


def test_signal_from_stored_bars_then_time_exit(db, loaded_rules):
    rules = _rules(loaded_rules)
    with db() as s:
        _store(s)
        assert _run(s, rules, AT - timedelta(minutes=1)).updates == []
        out = _run(s, rules, AT)
        assert len(out.updates) == 1 and out.updates[0].status == "PASS"
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MNQ-GALA-2026-10-13-0945" and sig.direction == "LONG"
        assert sig.features["setup"] == "BREAK_RETEST" and sig.features["level"] == "115"
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "GALA_PA" and (plan.entry, plan.stop, plan.take_profit) == (D(117), D("114.25"), D("122.5"))
        assert _run(s, rules, AT).updates == []  # stored once
        ex = _run(s, rules, AT + timedelta(minutes=60))
        assert ex.exits == [(sig.id, "GALA_TIME_EXIT")]  # B2 about an hour


def test_off_and_news_first_hour(db, loaded_rules):
    rules = _rules(loaded_rules)
    off = rules.model_copy(update={"strategy": rules.strategy.model_copy(update={"gala_pa": False})})
    news = lambda _d: [NewsEvent(AT + timedelta(minutes=30), "FOMC speech")]  # noqa: E731
    with db() as s:
        _store(s)
        assert _run(s, off, AT).updates == []
        assert _run(s, rules, AT, news).updates == []  # A9: high-impact news in the first hour
        assert _run(s, rules, AT, lambda _d: None).updates[0].status == "SKIP"  # CALENDAR_MISSING
        assert _run(s, rules, AT + timedelta(hours=8)).updates == []  # outside RTH


def _setup_accounts(authed, clock, stages):
    st = authed.app.state
    clock.set(AT)
    ids = []
    for i, stage in enumerate(stages):
        aid = authed.post("/api/accounts", json={"label": f"G{i}", "stage": stage, "balance": "25000"}).json()["id"]
        assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
        ids.append(aid)
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"gala_pa": True})})
    return st, ids


def _signal(st, stop_pts, tag):
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=f"MNQ-GALA-2026-10-13-0945-{tag}", direction=Direction.LONG, at=AT,
            gate=(True, "OK", ""), features={"setup": "BREAK_RETEST"},
            plan=("GALA_PA", D(20000), D(20000) - stop_pts, D(20000) + 2 * stop_pts, stop_pts, D(2)),
        )  # fmt: skip
        s.commit()
        return sig.id


def test_controller_lucid_fit_one_account_and_size_skip(authed, clock):
    st, ids = _setup_accounts(authed, clock, ["EVAL", "EVAL"])
    res = asyncio.run(st.controller.execute(_signal(st, D(10), "a"), "automation", only=ids))
    assert len(res) == 1  # one free account per trade, no copy trading
    with st.sessionmaker() as s:
        rows = [x.payload for x in s.query(AuditLog).filter_by(action="trade.gala_size")]
    # 25% of $1,000 = $250, but 3 losses (E2) must fit the $475 consistency day stop → $158.33; 10 pt = $20 + costs
    assert rows and rows[0]["risk_usd"] == "158.33" and rows[0]["contracts"] == 7
    res = asyncio.run(st.controller.execute(_signal(st, D(200), "b"), "automation", only=ids))
    assert [r.reason for r in res] == ["GALA_SIZE_BELOW_1"]


@pytest.mark.parametrize(
    ("k", "stage", "risk", "n10", "n20"),
    [
        (25, "EVAL", "158.33", 7, 3),
        (50, "EVAL", "360.00", 16, 8),
        (100, "EVAL", "540.00", 24, 12),
        (150, "EVAL", "810.00", 36, 19),
        (25, "FUNDED", "180.00", 8, 4),
        (50, "FUNDED", "360.00", 16, 8),
        (100, "FUNDED", "540.00", 24, 12),
        (150, "FUNDED", "810.00", 36, 19),
    ],
)
def test_pro_plan_fit_table(k, stage, risk, n10, n20):
    from app.config import load_rules
    from app.engine.lucid_fit import contracts_for, trade_risk_usd
    from app.phases.phase_engine import firm_max_micros, stage_rules
    from app.settings import REPO_ROOT

    r = load_rules(REPO_ROOT / "config" / "rules" / f"lucid_pro_{k}k.yaml").rules
    c, i = r.strategy.gala_pa_cfg, r.internal
    assert r.strategy.gala_pa is False and c.max_trades_per_day == 3 and c.dll_use_pct == D("0.9")
    sr = stage_rules(r, stage)
    assert sr.drawdown_type == "eod"
    day_stop = D("0.38") * r.eval.profit_target if stage == "EVAL" else None
    got = trade_risk_usd(sr.max_loss, c.risk_pct_of_drawdown, c.max_trades_per_day, sr.dll, c.dll_use_pct,
                         sr.max_loss - i.kill_switch_mll_distance, r.strategy.max_trade_risk_usd, day_stop)  # fmt: skip
    m = r.instrument("MNQ")
    slip = m.slippage_ticks or r.trade_plan.slippage_ticks
    cap = min(firm_max_micros(r, stage, D(0)), i.internal_max_micros)
    n = [min(contracts_for(got, D(x), m.tick, m.tick_value, m.fee_rt, slip), cap) for x in (10, 20)]
    # worst day = 3 losses ≤ DLL x 0.9, ≤ MLL room − kill distance, ≤ the consistency day stop
    assert 3 * got <= (sr.dll or got * 3) * D("0.9") + D("0.01") and 3 * got <= sr.max_loss - i.kill_switch_mll_distance
    assert (str(got), n) == (risk, [n10, n20])
