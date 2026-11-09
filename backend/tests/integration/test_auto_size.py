"""D63: NOISE / PM_FADE size each account by its own size (size_table) with the drawdown brake."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.models import AuditLog
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
                update={"size_table": reg, "size_table_high": high, "high_risk": True}
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
    assert set(body) == {"active", "setting", "regular", "high"} and body["setting"] == "strategy.high_risk"


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
        update={"strategy": h.rules.strategy.model_copy(update={"size_table": reg, "size_table_eval": ev})}
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
