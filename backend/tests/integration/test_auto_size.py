"""D63: NOISE / PM_FADE size each account by its own size (size_table) with the drawdown brake."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.models import Account, AuditLog, Order
from app.signals import strategy_service as SS

AT = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)  # Tue 11:00 ET


def test_noise_trade_sized_per_account(authed, clock):
    st = authed.app.state
    clock.set(AT)
    ids = {}
    for label, bal in (("25K", "25000"), ("50K", "50000"), ("150K", "150000")):
        aid = authed.post("/api/accounts", json={"label": label, "stage": "EVAL", "balance": bal}).json()["id"]
        assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
        ids[label] = aid
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    from app.config import SizeTierCfg

    table = [
        SizeTierCfg(account_size=D(25000), mll=D(1000), contracts=1),
        SizeTierCfg(account_size=D(50000), mll=D(2000), contracts=2, brake_below=D("0.5"), brake_contracts=1),
        SizeTierCfg(account_size=D(150000), mll=D(4500), contracts=4, brake_below=D("0.5"), brake_contracts=2),
    ]
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"size_table": table})})
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s,
            FixedClock(AT),
            symbol="MNQ",
            key="MNQ-NOISE-2026-10-13-1",
            direction=Direction.LONG,
            at=AT,
            gate=(True, "OK", ""),
            features={"reason": "test"},
            plan=("NOISE", D(20000), D(19876), D(20050), D(124), D("0.40")),  # near TP: fits the 40% consistency cap
        )
        s.commit()
        sid = sig.id
    res = asyncio.run(st.controller.execute(sid, "automation", only=list(ids.values())))
    by = {r.account_id: r for r in res}
    with st.sessionmaker() as s:
        sizes = {x.entity: x.payload for x in s.query(AuditLog).filter_by(action="trade.auto_size")}
    assert len(sizes) == 3, (res, sizes)
    got = {
        label: next(v for v in sizes.values() if v["tier"] == t)
        for label, t in (("25K", "25000"), ("50K", "50000"), ("150K", "150000"))
    }
    assert got["25K"]["contracts"] == 1 and not got["25K"]["braked"]
    assert got["50K"]["contracts"] == 2 and not got["50K"]["braked"]  # cushion $1,000 = 50% of $2,000 → no brake
    assert got["150K"]["contracts"] == 2 and got["150K"]["braked"]  # cushion $1,000 < 50% of $4,500 → brake 4 → 2
    assert all(v["profile"] == "REGULAR" for v in sizes.values())
    # the pre-trade checks received exactly that size (the order itself needs a live price feed, not in this test)
    want = {ids["25K"]: "1", ids["50K"]: "2", ids["150K"]: "2"}
    for aid, n in want.items():
        fixed = next(c for c in by[aid].checks if c["check"] == "fixed_size")
        assert fixed["contracts"] == n, (aid, by[aid])


def test_high_risk_profile_switches_table(authed, clock):  # D64
    from app.config import SizeTierCfg

    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "50K", "stage": "EVAL", "balance": "50000"}).json()["id"]
    assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    h = st.controller.rules
    reg = [SizeTierCfg(account_size=D(50000), mll=D(2000), contracts=2)]
    high = [SizeTierCfg(account_size=D(50000), mll=D(2000), contracts=3, brake_below=D("0.4"), brake_contracts=2)]
    h.rules = h.rules.model_copy(
        update={
            "strategy": h.rules.strategy.model_copy(
                update={"size_table": reg, "size_table_high": high, "high_risk": True, "max_trade_risk_usd": None}
            )
        }
    )
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s,
            FixedClock(AT),
            symbol="MNQ",
            key="MNQ-NOISE-2026-10-13-1",
            direction=Direction.LONG,
            at=AT,
            gate=(True, "OK", ""),
            features={"reason": "test"},
            plan=("NOISE", D(20000), D(19876), D(20050), D(124), D("0.40")),
        )
        s.commit()
        sid = sig.id
    res = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    fixed = next(c for c in res[0].checks if c["check"] == "fixed_size")
    assert fixed["contracts"] == "3", res  # high-risk table; cushion $1,000 ≥ 40% of $2,000 → no brake
    with st.sessionmaker() as s:
        assert s.query(AuditLog).filter_by(action="trade.auto_size").one().payload["profile"] == "HIGH"
    # the Strategy page shows both profiles and saves the switch through versioned settings
    body = authed.get("/api/strategies").json()["size_profiles"]
    assert set(body) == {"active", "setting", "regular", "high", "eval_regular", "eval_high"}
    assert body["setting"] == "strategy.high_risk"


def test_eval_mode_uses_eval_table_only_on_eval_accounts(authed, clock):  # D66
    from app.config import SizeTierCfg

    st = authed.app.state
    clock.set(AT)
    ids = {}
    for label, stage in (("E", "EVAL"), ("F", "FUNDED")):
        aid = authed.post("/api/accounts", json={"label": label, "stage": stage, "balance": "50000"}).json()["id"]
        assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
        ids[stage] = aid
    authed.post("/api/attestation", json={"confirm": True})
    r = authed.put("/api/risk/eval-mode", json={"enabled": True, "confirm": "ENABLE EVALUATION MODE"})
    assert r.status_code == 200, r.text
    st.controller.mode = "FULL"
    h = st.controller.rules
    reg = [SizeTierCfg(account_size=D(50000), mll=D(2000), contracts=1)]
    ev = [
        SizeTierCfg(
            account_size=D(50000), mll=D(2000), contracts=3, grow_per=D(400), max_contracts=4, day_lock_pct=D("0.5")
        )
    ]
    h.rules = h.rules.model_copy(
        update={
            "strategy": h.rules.strategy.model_copy(
                update={"size_table": reg, "size_table_eval": ev, "max_trade_risk_usd": None}
            )
        }
    )
    assert h.eval_mode_on
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s,
            FixedClock(AT),
            symbol="MNQ",
            key="MNQ-NOISE-2026-10-13-1",
            direction=Direction.LONG,
            at=AT,
            gate=(True, "OK", ""),
            features={"reason": "test"},
            plan=("NOISE", D(20000), D(19876), D(20050), D(124), D("0.40")),
        )
        s.commit()
        sid = sig.id
    res = {x.account_id: x for x in asyncio.run(st.controller.execute(sid, "automation", only=list(ids.values())))}
    with st.sessionmaker() as s:
        prof = {x.entity: x.payload for x in s.query(AuditLog).filter_by(action="trade.auto_size")}
    by_profile = sorted(v["profile"] for v in prof.values())
    assert by_profile == ["EVAL", "REGULAR"], prof  # FUNDED never gets the eval table (non-negotiable 10)
    ev_fixed = next(c for c in res[ids["EVAL"]].checks if c["check"] == "fixed_size")
    fu_fixed = next(c for c in res[ids["FUNDED"]].checks if c["check"] == "fixed_size")
    assert ev_fixed["contracts"] in ("3", "4") and fu_fixed["contracts"] == "1"


def test_eval_day_lock_in_stops_the_day(authed, clock, monkeypatch):  # D66
    from app.automation import state as stt
    from app.config import SizeTierCfg

    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "E", "stage": "EVAL", "balance": "50000"}).json()["id"]
    assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
    authed.post("/api/attestation", json={"confirm": True})
    assert (
        authed.put("/api/risk/eval-mode", json={"enabled": True, "confirm": "ENABLE EVALUATION MODE"}).status_code
        == 200
    )
    st.controller.mode = "FULL"
    h = st.controller.rules
    ev = [SizeTierCfg(account_size=D(50000), mll=D(2000), contracts=2, day_lock_pct=D("0.5"))]
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"size_table_eval": ev})})
    target = h.rules.eval.profit_target
    orig = stt.day_stats

    def big_day(s, a, now):  # today's realized profit already ≥ 50% of the remaining target
        d = orig(s, a, now)
        d.day_profit = target  # start-of-day profit = balance − today − start = −target → remaining = 2 × target
        return d

    monkeypatch.setattr(stt, "day_stats", big_day)
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s,
            FixedClock(AT),
            symbol="MNQ",
            key="MNQ-NOISE-2026-10-13-1",
            direction=Direction.LONG,
            at=AT,
            gate=(True, "OK", ""),
            features={"reason": "test"},
            plan=("NOISE", D(20000), D(19876), D(20050), D(124), D("0.40")),
        )
        s.commit()
        sid = sig.id
    res = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    assert res[0].reason == "EVAL_DAY_LOCK", res


def _eval_account(authed, clock, balance="25000"):
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "E", "stage": "EVAL", "balance": balance}).json()["id"]
    assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
    authed.post("/api/attestation", json={"confirm": True})
    assert (
        authed.put("/api/risk/eval-mode", json={"enabled": True, "confirm": "ENABLE EVALUATION MODE"}).status_code
        == 200
    )
    authed.app.state.controller.mode = "FULL"
    return aid


def _signal(st):
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s,
            FixedClock(AT),
            symbol="MNQ",
            key="MNQ-NOISE-2026-10-13-1",
            direction=Direction.LONG,
            at=AT,
            gate=(True, "OK", ""),
            features={"reason": "test"},
            plan=("NOISE", D(20000), D(19876), D(20050), D(124), D("0.40")),
        )
        s.commit()
        return sig.id


def test_eval_growth_row_is_applied_by_the_controller(authed, clock):  # D66 — the growth rule must reach the sizing
    from app.config import SizeTierCfg

    st = authed.app.state
    aid = _eval_account(authed, clock, "100000")
    h = st.controller.rules
    ev = [SizeTierCfg(account_size=D(100000), mll=D(3000), contracts=2, grow_per=D(400), max_contracts=4)]
    strat = h.rules.strategy.model_copy(update={"size_table_eval": ev, "max_trade_risk_usd": None})  # D115 cap off
    h.rules = h.rules.model_copy(update={"strategy": strat})
    res = asyncio.run(st.controller.execute(_signal(st), "automation", only=[aid]))
    fixed = next(c for c in res[0].checks if c["check"] == "fixed_size")
    # this test plan's loss limit is $1,000 → cushion $1,000 → 2 + (1,000 // 400 − 1) = 3 micros (was ignored before)
    assert fixed["contracts"] == "3"


def test_high_risk_eval_taper_on_25k(authed, clock, monkeypatch):  # D69 sprint then protect
    from app.config import SizeTierCfg

    st = authed.app.state
    aid = _eval_account(authed, clock, "25000")
    h = st.controller.rules
    hi = [
        SizeTierCfg(
            account_size=D(25000),
            mll=D(1000),
            contracts=3,
            stop_usd=D(150),
            taper_below_remaining=D("0.5"),
            taper_contracts=1,
        )
    ]
    reg = [SizeTierCfg(account_size=D(25000), mll=D(1000), contracts=1)]
    strat = h.rules.strategy.model_copy(update={"size_table_eval": reg, "size_table_eval_high": hi, "high_risk": True})
    h.rules = h.rules.model_copy(update={"strategy": strat})
    sid = _signal(st)
    res = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    first = next(c for c in res[0].checks if c["check"] == "fixed_size")
    # 3 micros × $150 stop would be $448.50, but this test plan has a $600 DLL → room $600 → the live D57 rule
    # tightens it to 60% of the room = $360 (a real Pro 25K eval has no DLL: room $900 → $540 → no tightening)
    assert first["contracts"] == "3" and first["worst"] == "360.00"
    real = st.controller._equity

    async def ahead(a):  # +$700 earned: 44% of the $1,250 target left → below 50% → protect with 1 micro
        bal, opnl = await real(a)
        return bal + D(700), opnl

    monkeypatch.setattr(st.controller, "_equity", ahead)
    with (
        st.sessionmaker() as s
    ):  # the paper broker has no price in this test: the first order failed and paused the account
        s.query(Order).delete()
        acct = s.get(Account, aid)
        acct.paused_reason, acct.armed = None, True
        s.commit()
    res = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    assert next(c for c in res[0].checks if c["check"] == "fixed_size")["contracts"] == "1"
    with st.sessionmaker() as s:
        profiles = [x.payload["profile"] for x in s.query(AuditLog).filter_by(action="trade.auto_size")]
    assert profiles == ["EVAL", "EVAL"]


def test_fast_eval_ladder_eval_only_and_quality_day(authed, clock):  # D87
    from app.config import FastEvalCfg, SizeTierCfg
    from app.models import Trade

    st = authed.app.state
    clock.set(AT)
    ids = {}
    for label, stage in (("E", "EVAL"), ("F", "FUNDED")):
        aid = authed.post("/api/accounts", json={"label": label, "stage": stage, "balance": "25000"}).json()["id"]
        assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
        ids[label] = aid
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    h = st.controller.rules
    fe = FastEvalCfg.model_validate(
        {"ladder": {"enabled": True, "steps": [{"cushion_frac": "0.5", "extra": 1}], "max_contracts": 2},
         "quality_day": {"enabled": True, "mode": "prev_day"}}
    )  # fmt: skip
    table = [SizeTierCfg(account_size=D(25000), mll=D(1000), contracts=1)]
    h.rules = h.rules.model_copy(
        update={"fast_eval": fe, "strategy": h.rules.strategy.model_copy(update={"size_table": table})}
    )

    def fire(key):
        with st.sessionmaker() as s:
            for aid in ids.values():  # a failed paper order (no feed in tests) pauses the account: reset for each fire
                acct = s.get(Account, aid)
                acct.paused_reason, acct.armed = None, True
            s.commit()
            sig = SS._new_signal(
                s, FixedClock(AT), symbol="MNQ", key=key, direction=Direction.LONG, at=AT, gate=(True, "OK", ""),
                features={"reason": "test"}, plan=("NOISE", D(20000), D(19876), D(20050), D(124), D("0.40")),
            )  # fmt: skip
            s.commit()
            sid = sig.id
        return {r.account_id: r for r in asyncio.run(st.controller.execute(sid, "automation", only=list(ids.values())))}

    def fixed(res, label):
        return next(c for c in res[ids[label]].checks if c["check"] == "fixed_size")["contracts"]

    off = fire("MNQ-NOISE-2026-10-13-1")  # Fast Evaluation OFF (default): base size everywhere

    assert fixed(off, "E") == "1" and fixed(off, "F") == "1"
    h.fast_eval_on = True
    on = fire("MNQ-NOISE-2026-10-13-2")
    assert fixed(on, "E") == "2"  # ladder: cushion 100% of the loss limit >= 50% → +1 micro on EVAL
    assert fixed(on, "F") == "1"  # FUNDED never changes
    with st.sessionmaker() as s:
        s.get(Account, ids["E"]).stage_started_at = None  # count history from the start in this test
        # yesterday was a losing day → quality-day filter skips the EVAL account only
        s.add(
            Trade(
                account_id=ids["E"],
                symbol="MNQ",
                direction="LONG",
                qty=1,
                entry=D(20000),
                risk_usd=D(100),
                opened_at=datetime(2026, 10, 12, 15, tzinfo=UTC),
                closed_at=datetime(2026, 10, 12, 16, tzinfo=UTC),
                pnl_usd=D(-50),
                net_r=D("-0.2"),
            )
        )
        s.commit()
    skipped = fire("MNQ-NOISE-2026-10-13-3")
    assert skipped[ids["E"]].reason == "FAST_EVAL_QUALITY_DAY" and not skipped[ids["E"]].ok
    assert skipped[ids["F"]].reason != "FAST_EVAL_QUALITY_DAY"
