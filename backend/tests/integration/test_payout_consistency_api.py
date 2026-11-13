"""D89: Lucid payout consistency (Pro FUNDED): service, API, payout gating, account date, N6 live day stop."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

from app.config import PayoutsCfg, load_rules
from app.models import Account, Payout, Trade
from app.payouts.service import consistency_view, plan_for
from tests.conftest import PASSWORD, REPO_ROOT

PRO = REPO_ROOT / "config" / "rules" / "lucid_pro_25k.yaml"
THU = datetime(2026, 11, 5, 22, 10, tzinfo=UTC)


def _login(authed, clock):
    clock.set(THU)
    r = authed.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    authed.headers["x-csrf-token"] = r.json()["csrf"]


def _pro(authed):
    h = authed.app.state.rules
    rules = load_rules(Path(PRO)).rules
    pc = PayoutsCfg.model_validate(
        {**rules.payouts.model_dump(), "frequency": "every_n_sessions", "mode": "max_eligible"}
    )
    h.rules = rules.model_copy(update={"payouts": pc})
    return h.rules


def _trades(authed, aid, pnls, first_day=2):
    with authed.app.state.sessionmaker() as s:
        s.get(Account, aid).stage_started_at = datetime(2026, 10, 1, tzinfo=UTC)  # FUNDED since before these trades
        for i, pnl in enumerate(pnls):
            day = datetime(2026, 10, first_day + i, 20, 0, tzinfo=UTC)
            s.add(
                Trade(
                    account_id=aid,
                    symbol="MNQ",
                    direction="LONG",
                    qty=1,
                    entry=D(1),
                    exit=D(2),
                    pnl_usd=D(pnl),
                    risk_usd=D(70),
                    opened_at=day,
                    closed_at=day,
                    trade_ref=f"C{first_day}-{i}",
                )
            )
        s.commit()


def test_pro_rules_carry_the_numbers_and_other_plans_do_not():
    cfg = load_rules(PRO).rules.funded.payout_consistency
    assert cfg is not None and cfg.pct == 40 and cfg.legacy_pct == 35
    assert cfg.legacy_cutoff == datetime(2025, 11, 28, 20, 0, tzinfo=UTC)  # 15:00 ET
    for name in ("lucid_daily_25k", "lucid_flex_25k"):
        assert load_rules(REPO_ROOT / "config" / "rules" / f"{name}.yaml").rules.funded.payout_consistency is None


def test_config_rejects_bad_payout_consistency():
    import pytest
    from pydantic import ValidationError

    from app.config import PayoutConsistencyCfg

    with pytest.raises(ValidationError):
        PayoutConsistencyCfg(pct=40, legacy_pct=35, legacy_cutoff=datetime(2025, 11, 28, 15, 0))  # naive time
    with pytest.raises(ValidationError):
        PayoutConsistencyCfg(pct=35, legacy_pct=40, legacy_cutoff=datetime(2025, 11, 28, 20, tzinfo=UTC))


def test_view_unknown_date_is_stricter_and_flagged_then_date_decides(authed, clock):
    _login(authed, clock)
    rules = _pro(authed)
    aid = authed.post("/api/accounts", json={"label": "P1", "stage": "FUNDED", "balance": "27000"}).json()["id"]
    _trades(authed, aid, [380, 310, 310])  # largest 380 / 1,000 = 38%
    st = authed.app.state
    with st.sessionmaker() as s:
        a = s.get(Account, aid)
        v = consistency_view(s, rules, a)
        assert v["pct"] == "38.0" and v["limit"] == "35" and not v["eligible"] and not v["date_known"]
        assert v["verify"] and "Enter it on the Accounts page" in v["verify"]
        assert v["needed_cycle_profit"] == "1086.00" and v["still_needed"] == "86.00" and "$86.00 more" in v["text"]
        assert plan_for(s, rules, a, D(27000), THU).reason == "CONSISTENCY"
    # purchased after the cutoff: 40% limit, eligible, payout planned
    r = authed.patch(f"/api/accounts/{aid}", json={"purchased_at": "2025-12-01T10:00:00-05:00"})
    assert r.status_code == 200, r.text
    with st.sessionmaker() as s:
        a = s.get(Account, aid)
        v = consistency_view(s, rules, a)
        assert v["eligible"] and v["limit"] == "40" and v["date_known"] and v["verify"] is None
        assert plan_for(s, rules, a, D(27000), THU).kind == "max"
    # purchased/reset exactly at the cutoff or before: 35%
    authed.patch(f"/api/accounts/{aid}", json={"purchased_at": "2025-11-28T15:00:00-05:00"})
    with st.sessionmaker() as s:
        v = consistency_view(s, rules, s.get(Account, aid))
        assert v["limit"] == "35" and not v["eligible"]
    # clearing goes back to unknown
    authed.patch(f"/api/accounts/{aid}", json={"clear_purchased_at": True})
    with st.sessionmaker() as s:
        assert s.get(Account, aid).purchased_at is None
    assert authed.patch(f"/api/accounts/{aid}", json={"purchased_at": "2025-12-01T10:00:00"}).status_code == 422


def test_api_lists_and_blocks_submitting_a_payout_while_not_eligible(authed, clock):
    _login(authed, clock)
    _pro(authed)
    aid = authed.post("/api/accounts", json={"label": "P1", "stage": "FUNDED", "balance": "27000"}).json()["id"]
    authed.post("/api/accounts", json={"label": "E1", "stage": "EVAL"})  # not FUNDED: never listed
    _trades(authed, aid, [900, 100])  # 90%
    rows = authed.get("/api/payouts/consistency").json()["accounts"]
    assert [r["label"] for r in rows] == ["P1"] and rows[0]["eligible"] is False
    acc = next(a for a in authed.get("/api/accounts").json()["accounts"] if a["label"] == "P1")
    assert acc["payout_consistency"]["still_needed"] and acc["purchased_at"] is None
    dash = authed.get("/api/dashboard").json()
    assert any((x.get("payout_consistency") or {}).get("eligible") is False for x in dash["accounts"])
    with authed.app.state.sessionmaker() as s:  # a stale 'ready' row must not be submittable while the rule is unmet
        p = Payout(
            account_id=aid, week="2026-11-05", kind="max", amount=D(900), balance_before=D(27000), status="ready"
        )
        s.add(p)
        s.commit()
        pid = p.id
    r = authed.post(f"/api/payouts/{pid}/status", json={"status": "submitted"})
    assert r.status_code == 409 and "consistency not met" in r.text.lower()
    assert authed.post(f"/api/payouts/{pid}/status", json={"status": "cancelled"}).status_code == 200
    # once the rule is met (900 / 2,800 = 32% <= 35%), submitting works
    _trades(authed, aid, [300] * 6, first_day=10)
    with authed.app.state.sessionmaker() as s:
        p = Payout(
            account_id=aid, week="2026-11-06", kind="max", amount=D(900), balance_before=D(27000), status="ready"
        )
        s.add(p)
        s.commit()
        pid = p.id
    assert authed.post(f"/api/payouts/{pid}/status", json={"status": "submitted"}).status_code == 200


def test_cycle_resets_after_a_processed_payout(authed, clock):
    _login(authed, clock)
    rules = _pro(authed)
    aid = authed.post("/api/accounts", json={"label": "P1", "stage": "FUNDED", "balance": "27000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"purchased_at": "2025-12-01T10:00:00-05:00"})
    _trades(authed, aid, [900, 100])
    with authed.app.state.sessionmaker() as s:
        a = s.get(Account, aid)
        assert not consistency_view(s, rules, a)["eligible"]
        s.add(
            Payout(
                account_id=aid,
                week="2026-11-04",
                kind="max",
                amount=D(500),
                balance_before=D(27000),
                status="processed",
                processed_at=datetime(2026, 11, 4, 23, 0, tzinfo=UTC),
            )
        )
        s.commit()
        v = consistency_view(s, rules, a)  # old days belong to the paid-out cycle
        assert v["cycle_profit"] == "0" and v["largest_day"] == "0" and "No profitable day" in v["text"]


def test_rule_does_not_apply_on_live_eval_or_other_plans(authed, clock):
    _login(authed, clock)
    rules = _pro(authed)
    ids = {st: authed.post("/api/accounts", json={"label": st, "stage": st}).json()["id"] for st in ("EVAL", "LIVE")}
    with authed.app.state.sessionmaker() as s:
        assert all(consistency_view(s, rules, s.get(Account, i)) is None for i in ids.values())
    assert authed.get("/api/payouts/consistency").json()["accounts"] == []
    authed.app.state.rules.rules = load_rules(REPO_ROOT / "config" / "rules" / "lucid_flex_25k.yaml").rules
    fid = authed.post("/api/accounts", json={"label": "F", "stage": "FUNDED"}).json()["id"]
    with authed.app.state.sessionmaker() as s:
        assert consistency_view(s, authed.app.state.rules.rules, s.get(Account, fid)) is None


def test_n6_live_day_stop_flattens_strategy_trades_only(authed, clock):
    _login(authed, clock)
    aid = authed.post("/api/accounts", json={"label": "E", "stage": "EVAL"}).json()["id"]
    ctl = authed.app.state.controller
    with authed.app.state.sessionmaker() as s:
        ext = s.get(Account, aid).broker_account_id
    flat: list[str] = []

    async def fake_flatten(s, a, reason):
        flat.append(reason)
        return True

    pnl = {"v": D(100)}

    def tick() -> None:  # one watchdog pass of the monitor (without the commit that snapshots real trade objects)
        async def go() -> None:
            with authed.app.state.sessionmaker() as s:
                await ctl._monitor(s)

        asyncio.run(go())

    async def fake_equity(a):
        return D(25000), pnl["v"]

    ctl._flatten_account = fake_flatten  # type: ignore[method-assign]
    ctl._equity = fake_equity  # type: ignore[method-assign]
    # no strategy trade open: LunqFX trades are fitted to the cap before entry, nothing to watch here
    tick()
    assert "CONSISTENCY_DAY_STOP" not in flat
    ctl.om.trades["t1"] = SimpleNamespace(account=ext, strategy="NOISE")
    tick()  # open profit 100 < day stop 475.00
    assert "CONSISTENCY_DAY_STOP" not in flat
    pnl["v"] = D("475.00")  # exactly the day stop
    tick()
    assert flat == ["CONSISTENCY_DAY_STOP"]
    assert any(n["title"] == "Consistency day stop" for n in ctl.notices)
