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
    # the pre-trade checks received exactly that size (the order itself needs a live price feed, not in this test)
    want = {ids["25K"]: "1", ids["50K"]: "2", ids["150K"]: "2"}
    for aid, n in want.items():
        fixed = next(c for c in by[aid].checks if c["check"] == "fixed_size")
        assert fixed["contracts"] == n, (aid, by[aid])
