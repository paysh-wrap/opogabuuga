"""D165 NOISE + CANDACE · MGC button: config, the NOISE / CANDACE paths on MGC bars, controller fixed 1 micro."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.models import Bar, Signal, TradePlanRow
from app.signals import strategy_service as SS
from tests.unit.test_candace_ict import T9, bars

DAY0 = datetime(2026, 10, 12, 13, 30, tzinfo=UTC)  # Monday 09:30 ET
T0 = T9 + timedelta(minutes=30)  # CANDACE is fed regular-hours bars only
AT = (T0 + timedelta(minutes=13)).astimezone(UTC)


def _rules(loaded_rules, on=True, **cand):
    r = loaded_rules.rules
    m = r.strategy.mgc_noise_candace_cfg
    m = m.model_copy(update={"candace": m.candace.model_copy(update=cand)}) if cand else m
    st = r.strategy.model_copy(update={"mgc_noise_candace": on, "mgc_noise_candace_cfg": m})
    return r.model_copy(update={"strategy": st})


def _add_day(s, start, closes, base=D(4000)):
    prev = base
    for k in range(390):
        c = closes.get(k, prev)
        s.add(Bar(symbol="MGC", tf="1", close_time=start + timedelta(minutes=k + 1), o=prev, h=max(prev, c) + D("0.1"),
                  l=min(prev, c) - D("0.1"), c=c, v=D(100), source="tradingview"))  # fmt: skip
        prev = c


def test_config_defaults_and_plan_yaml(loaded_rules):
    r = loaded_rules.rules
    m = r.strategy.mgc_noise_candace_cfg
    assert r.strategy.mgc_noise_candace is False  # default OFF
    assert (m.noise.symbol, m.candace.symbol, m.contracts) == ("MGC", "MGC", 1)
    assert m.noise.emergency_stop_usd == D(250) and m.noise.skip_weekdays == [] and m.noise.profit_lock_pts is None
    assert (m.candace.ny_window, m.candace.ny_max_stop_pts, m.candace.ny_max_hold_minutes) == ("08:20-11:00", D(6), 30)
    assert r.instruments["MGC"].enabled is False and r.instruments["MGC"].super_group == "METALS"


def test_noise_on_mgc_signal_and_switches(client, loaded_rules):
    db = client.app.state.sessionmaker
    days = [DAY0 + timedelta(days=i) for i in (0, 1, 2, 3, 4, 7, 8, 9, 10, 11, 14, 15)]
    hist, today = days[:-1], days[-1]
    at = today + timedelta(minutes=30)
    with db() as s:
        for d in hist:
            _add_day(s, d, {29: D(4008), 30: D(4000), 89: D(3992), 90: D(4000)})
        _add_day(s, today, {k: D(4000) + D("0.6") * k for k in range(30)})
        s.commit()
        args = dict(clock=FixedClock(at), calendar=lambda _d: [], symbol="MGC", tf="1", at=at)
        assert SS.run(s, rules=_rules(loaded_rules, on=False), **args).updates == []  # button OFF
        assert SS.run(s, rules=_rules(loaded_rules), **{**args, "symbol": "MNQ"}).updates == []  # other market
        out = SS.run(s, rules=_rules(loaded_rules), **args)
        assert len(out.updates) == 1 and out.updates[0].status == "PASS"  # MGC stays disabled elsewhere, own switch
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MGC-NOISE-2026-10-27-1" and sig.features["strategy"] == "MGC_NOISE"
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "MGC_NOISE" and plan.entry - plan.stop == D("24.6")  # $250 stop, 1 micro MGC


def test_candace_on_mgc_signal(client, loaded_rules):
    with client.app.state.sessionmaker() as s:
        for b in bars(t0=T0):
            s.add(Bar(symbol="MGC", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                      v=b.v, source="tv"))  # fmt: skip
        s.commit()
        args = dict(clock=FixedClock(AT), calendar=lambda _d: [], symbol="MGC", tf="1", at=AT)
        assert SS.run(s, rules=_rules(loaded_rules, on=False, premium_pct=D("0.2")), **args).updates == []
        out = SS.run(s, rules=_rules(loaded_rules, premium_pct=D("0.2"), ny_max_stop_pts=D(50)), **args)
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MGC-CAND-2026-10-13-0943" and sig.status == "PASS" and sig.direction == "SHORT"
        assert s.query(TradePlanRow).filter_by(signal_id=sig.id).one().mode == "MGC_CANDACE"
        # the default 6-pt stop cap skips this 9.5-pt setup (never widened)
        assert SS.run(s, rules=_rules(loaded_rules, premium_pct=D("0.2")), **args).updates == []


def test_controller_trades_one_micro(authed, clock):
    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "G", "stage": "EVAL", "balance": "25000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MGC"] = D(4000)
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"mgc_noise_candace": True})})
    with st.sessionmaker() as s:
        x = SS._new_signal(
            s, FixedClock(AT), symbol="MGC", key="MGC-NOISE-x-1", direction=Direction.SHORT, at=AT,
            gate=(True, "OK", ""), features={},
            plan=("MGC_NOISE", D(4000), D("4005"), D("3900"), D(5), D(20)),
        )  # fmt: skip
        s.commit()
        sid = x.id
    [res] = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    assert res.reason is None and sum(t.qty for t in st.controller.om.trades.values()) == 1


def test_strategy_card_and_toggle(authed):
    d = authed.get("/api/strategies").json()
    card = next(c for c in d["strategies"] if c["key"] == "mgc_noise_candace")
    assert card["enabled"] is False and card["setting"] == "strategy.mgc_noise_candace"
    assert card["badge"] == "UNVERIFIED · 30-day yfinance test only" and "PF 1.97" in card["note"]
    assert [x["key"] for x in card["strategy_rules"]] == ["NOISE", "CANDACE", "SIZE", "DATA"]
    r = authed.put("/api/risk/settings", json={"changes": {"strategy.mgc_noise_candace": True}, "note": "mgc"})
    assert r.status_code == 200, r.text
    d = authed.get("/api/strategies").json()
    assert next(c for c in d["strategies"] if c["key"] == "mgc_noise_candace")["enabled"] is True
