"""CANDACE ICT SCALP (D149) end to end: stored bars → signal; controller grade size (tighten-only); Pro fit table."""

from __future__ import annotations

import asyncio
from datetime import UTC, timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.lucid_fit import grade_contracts
from app.engine.trade_plan import Direction
from app.models import AuditLog, Bar, Signal, TradePlanRow
from app.signals import strategy_service as SS
from tests.integration.lucid_fit_helpers import fit
from tests.unit.test_candace_ict import T9, bars

T0 = T9 + timedelta(minutes=30)  # RTH start: live CANDACE is fed regular-hours bars only (09:31 first bar)
AT = (T0 + timedelta(minutes=13)).astimezone(UTC)


def test_signal_from_stored_bars(client, loaded_rules):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    cc = r.strategy.candace_ict_cfg.model_copy(update={"premium_pct": D("0.2")})
    rules = r.model_copy(
        update={"strategy": r.strategy.model_copy(update={"candace_ict": True, "candace_ict_cfg": cc}),
                "instruments": {**r.instruments, "MNQ": mnq}}
    )  # fmt: skip
    with client.app.state.sessionmaker() as s:
        for b in bars(t0=T0):
            s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                      v=b.v, source="tv"))  # fmt: skip
        s.commit()
        out = SS.run(s, rules=rules, clock=FixedClock(AT), calendar=lambda _d: [], symbol="MNQ", tf="1", at=AT)
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.model_key == "MNQ-CAND-2026-10-13-0943" and sig.direction == "SHORT"
        assert sig.features["grade"] == "C" and sig.features["size_mult"] == "0.5"
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "CANDACE_ICT" and plan.stop == D("109.5")
        ex = (T0 + timedelta(minutes=28)).astimezone(UTC)
        s.add(Bar(symbol="MNQ", tf="1", close_time=ex, o=D(101), h=D(101), l=D(101), c=D(101), v=D(1), source="tv"))
        for m in range(14, 28):
            t = (T0 + timedelta(minutes=m)).astimezone(UTC)
            s.add(Bar(symbol="MNQ", tf="1", close_time=t, o=D(101), h=D(101), l=D(101), c=D(101), v=D(1), source="tv"))
        s.commit()
        out = SS.run(s, rules=rules, clock=FixedClock(ex), calendar=lambda _d: [], symbol="MNQ", tf="1", at=ex)
        assert out.exits == [(sig.id, "CAND_TIME_EXIT")]  # B2 about 15 minutes


def test_grade_contracts_is_tighten_only():
    assert [grade_contracts(4, D(x)) for x in ("2.0", "1.0", "0.5", "5")] == [4, 2, 1, 4]


@pytest.mark.parametrize(
    ("mult", "want"), [("2.0", (None, 3)), ("1.0", (None, 1)), ("0.5", ("CAND_GRADE_SIZE_BELOW_1", None))]
)
def test_controller_grade_size(authed, clock, mult, want):
    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "C", "stage": "EVAL", "balance": "25000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MNQ"] = D(20000)
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"candace_ict": True})})
    with st.sessionmaker() as s:
        x = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=f"MNQ-CAND-x-{mult}", direction=Direction.SHORT, at=AT,
            gate=(True, "OK", ""), features={"size_mult": mult},
            plan=("CANDACE_ICT", D(20000), D(20020), D(19960), D(20), D(2)),
        )  # fmt: skip
        s.commit()
        sid = x.id
    [res] = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    assert res.reason == want[0]
    if want[1] is not None:
        assert sum(t.qty for t in st.controller.om.trades.values()) == want[1]
        with st.sessionmaker() as s:
            assert s.query(AuditLog).filter_by(action="trade.cand_size").one().payload["contracts"] == want[1]


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
    assert fit(k, stage, "candace_ict_cfg", 3, (20, 40)) == want


def _cand_rules(loaded_rules):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    cc = r.strategy.candace_ict_cfg.model_copy(update={"premium_pct": D("0.2")})
    return r.model_copy(
        update={"strategy": r.strategy.model_copy(update={"candace_ict": True, "candace_ict_cfg": cc}),
                "instruments": {**r.instruments, "MNQ": mnq}}
    )  # fmt: skip


def test_live_candace_ignores_premarket_bars_like_the_research(client, loaded_rules):
    """C (H1/model_qa 2): the 09:01-09:13 setup that used to trade before the open must not signal live."""
    at = (T9 + timedelta(minutes=13)).astimezone(UTC)
    with client.app.state.sessionmaker() as s:
        for b in bars():  # 09:01..09:13 ET, pre-market
            s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                      v=b.v, source="tv"))  # fmt: skip
        s.commit()
        out = SS.run(s, rules=_cand_rules(loaded_rules), clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ",
                     tf="1", at=at)  # fmt: skip
        assert out.updates == []


def test_live_candace_parity_all_hours_feed_equals_rth_only_research():
    """C: replay on the live all-hours store == replay on RTH-only bars (research); Monday prior day = Friday RTH."""
    import random
    from datetime import date

    from app.config import CandaceIctCfg
    from app.engine import candace_ict as K
    from app.engine.conti_orb import MBar

    rnd = random.Random(7)
    cfg = CandaceIctCfg(premium_pct=D("0.2"))
    px = D(20000)
    allb: list[MBar] = []
    days = [date(2026, 10, 8), date(2026, 10, 9), date(2026, 10, 12)]  # Thu, Fri, MONDAY
    from datetime import datetime as DT

    for d in days:
        start = DT(d.year, d.month, d.day, 0, 0, tzinfo=K.ET)
        if d.weekday() == 0:
            start -= timedelta(hours=6)  # Sunday 18:00 Globex open
        for m in range(1, int((DT(d.year, d.month, d.day, 17, 0, tzinfo=K.ET) - start).total_seconds() // 60)):
            t = start + timedelta(minutes=m)
            o, px = px, px + D(rnd.choice([-1, 0, 1])) * D(rnd.randint(0, 6)) / 4
            allb.append(MBar(t, o, max(o, px) + D("0.25"), min(o, px) - D("0.25"), px, D(10)))
    day0 = DT(2026, 10, 12, 0, 0, tzinfo=K.ET)
    hist_all, today_all = [b for b in allb if b.close_time <= day0], [b for b in allb if b.close_time > day0]
    rth = K.rth_only(allb)
    assert all(DT(2026, 1, 1, 9, 30).time() < b.close_time.astimezone(K.ET).time() <= DT(2026, 1, 1, 16).time()
               for b in rth)  # fmt: skip
    hist_rth = [b for b in rth if b.close_time <= day0]
    today_rth = [b for b in rth if b.close_time > day0]
    research = K.replay_day(hist_rth, today_rth, cfg, D("0.25"))
    live = K.replay_day(K.rth_only(hist_all), K.rth_only(today_all), cfg, D("0.25"))
    assert [(x.time, x.direction, x.entry, x.stop) for x in live.signals] == [
        (x.time, x.direction, x.entry, x.stop) for x in research.signals
    ]
    assert live.gap_levels == research.gap_levels and live.gap_levels != []  # Monday: Friday RTH close, not Sunday
    raw = K.replay_day(hist_all, today_all, cfg, D("0.25"))  # the old live path differs (documents the bug)
    assert raw.gap_levels != research.gap_levels or [x.time for x in raw.signals] != [x.time for x in research.signals]
