"""D166 late-day momentum (3rd edge of the fast pass) end to end: stored bars -> signal -> flat exit; controller size
only with the option AND the plan's fast pass ON (EVAL, own size); every later check still shrinks / skips."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.config import FastPassCfg
from app.engine.trade_plan import Direction
from app.models import Account, AuditLog, Bar, Signal, TradePlanRow
from app.signals import strategy_service as SS
from tests.unit.test_late_day import ET, history, session

DAY = date(2026, 10, 13)  # Tuesday
AT = datetime(2026, 10, 13, 15, 0, tzinfo=ET).astimezone(UTC)
FLAT = datetime(2026, 10, 13, 15, 59, tzinfo=ET).astimezone(UTC)
CFG100 = FastPassCfg(
    account_size=D(100000), noise_contracts=3, noise_stop_usd=D(100), candace_contracts=3, brake_inclusive=False,
    late_contracts=3, late_steps=[{"cushion_usd": 1000, "contracts": 1}],
)  # fmt: skip
CFG25 = FastPassCfg(account_size=D(25000), noise_contracts=1, noise_stop_usd=D(75), candace_contracts=2)  # no late size


def _store(s, bars):
    for b in bars:
        s.add(Bar(symbol="MNQ", tf="1", close_time=b.close_time.astimezone(UTC), o=b.o, h=b.h, l=b.l, c=b.c,
                  v=b.v, source="tv"))  # fmt: skip
    s.commit()


def _rules(loaded_rules, on=True):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True})
    return r.model_copy(
        update={"strategy": r.strategy.model_copy(update={"fast_pass_late_day": on}),
                "instruments": {**r.instruments, "MNQ": mnq}}
    )  # fmt: skip


def test_signal_then_flat_exit(client, loaded_rules):
    rules = _rules(loaded_rules)
    with client.app.state.sessionmaker() as s:
        _store(s, history() + [b for b in session(DAY, D(20000), D(20)) if b.close_time.astimezone(UTC) <= AT])
        out = SS.run(s, rules=rules, clock=FixedClock(AT), calendar=lambda _d: [], symbol="MNQ", tf="1", at=AT)
        [u] = out.updates
        sig = s.get(Signal, u.signal_id)
        assert sig.model_key == "MNQ-LATE-2026-10-13-1500" and sig.direction == "LONG" and sig.passed
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "LATE_DAY" and plan.entry - plan.stop == D(60) and plan.rr == D(3)
        again = SS.run(s, rules=rules, clock=FixedClock(AT), calendar=lambda _d: [], symbol="MNQ", tf="1", at=AT)
        assert again.updates == []  # one entry per bar key (replay-safe)
        ex = SS.run(s, rules=rules, clock=FixedClock(FLAT), calendar=lambda _d: [], symbol="MNQ", tf="1", at=FLAT)
        assert ex.exits == [(sig.id, "LATE_FLAT_1559")]
        s.refresh(sig)
        assert sig.features["exit_reason"] == "LATE_FLAT_1559" and sig.features["state"] == "CLOSED"


def test_option_off_or_exits_only_no_signal(client, loaded_rules):
    with client.app.state.sessionmaker() as s:
        _store(s, history() + [b for b in session(DAY, D(20000), D(20)) if b.close_time.astimezone(UTC) <= AT])
        kw = {"clock": FixedClock(AT), "calendar": lambda _d: [], "symbol": "MNQ", "tf": "1", "at": AT}
        assert SS.run(s, rules=_rules(loaded_rules, on=False), **kw).updates == []
        assert SS.run(s, rules=_rules(loaded_rules), exits_only=True, **kw).updates == []  # a stale bar never enters


def test_no_signal_when_trend_too_small(client, loaded_rules):
    with client.app.state.sessionmaker() as s:
        _store(s, history() + [b for b in session(DAY, D(20000), D(3)) if b.close_time.astimezone(UTC) <= AT])
        out = SS.run(
            s, rules=_rules(loaded_rules), clock=FixedClock(AT), calendar=lambda _d: [], symbol="MNQ", tf="1", at=AT
        )
        assert out.updates == []


def _setup(
    authed, clock, *, stage="EVAL", balance="100000", cushion=D(3000), late=True, fast=True, cfg=CFG100, internal=None
):
    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "L", "stage": stage, "balance": balance}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MNQ"] = D(20000)
    with st.sessionmaker() as s:
        a = s.get(Account, aid)
        a.mll, a.mll_peak = D(balance) - cushion, D(balance)
        s.commit()
    h = st.controller.rules
    upd = {"fast_pass_late_day": late, "fast_pass_100k": fast, "fast_pass_100k_cfg": cfg, "fast_pass_25k_cfg": CFG25}
    rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update=upd)})
    if internal:
        rules = rules.model_copy(update={"internal": rules.internal.model_copy(update=internal)})
    h.rules = rules
    return st, aid


def _run(st, aid, key="1", direction=Direction.LONG):
    s_ = D(1) if direction is Direction.LONG else D(-1)
    with st.sessionmaker() as s:
        x = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=f"MNQ-LATE-t-{key}", direction=direction, at=AT,
            gate=(True, "OK", ""), features={},
            plan=("LATE_DAY", D(20000), D(20000) - s_ * 60, D(20000) + s_ * 180, D(60), D(3)),
        )  # fmt: skip
        s.commit()
        sid = x.id
    [res] = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    with st.sessionmaker() as s:
        sz = [x.payload for x in s.query(AuditLog).filter_by(action="trade.late_day_size")]
    return res, sz


@pytest.mark.parametrize(("cushion", "want", "braked"), [(D(3000), 3, False), (D(1000), 3, False), (D(999), 1, True)])
def test_size_and_brake(authed, clock, cushion, want, braked):
    st, aid = _setup(authed, clock, cushion=cushion)
    res, sz = _run(st, aid)
    assert sz and sz[-1]["contracts"] == want and sz[-1]["braked"] is braked
    if res.ok:  # the later checks (DLL / MLL room, D57 drawdown shrink ...) may only shrink or skip
        assert 1 <= res.contracts <= want
        [t] = st.controller.om.trades.values()
        assert t.plan.entry - t.plan.stop == D(60) and t.qty == res.contracts
    else:
        assert res.reason


@pytest.mark.parametrize(
    "kw", [{"late": False}, {"fast": False}, {"stage": "FUNDED"}, {"balance": "25000", "cfg": CFG25}, {"cfg": CFG25}]
)
def test_inert_unless_option_fast_pass_eval_and_own_size(authed, clock, kw):
    st, aid = _setup(authed, clock, **kw)
    res, sz = _run(st, aid)
    assert not res.ok and res.reason == "LATE_DAY_NOT_ACTIVE" and sz == []
    assert not st.controller.om.trades


def test_internal_max_still_shrinks(authed, clock):
    st, aid = _setup(authed, clock, internal={"internal_max_micros": 2})
    res, sz = _run(st, aid)
    # internal max shrinks 3 -> 2 before the consistency fit; the late leg has a real TP (B / M2), so the 100K eval
    # cap then fits it further (to 1 micro) instead of waiving the fit as NOISE does
    cap = next(c for c in res.checks if c["check"] == "consistency_cap")
    assert sz[-1]["contracts"] == 3 and res.ok and cap["contracts"] == "2" and res.contracts == int(cap["fitted"]) == 1, res


def test_one_position_per_account_and_hedge_lock(authed, clock):
    st, aid = _setup(authed, clock)
    res, _ = _run(st, aid, key="a")
    assert res.ok, res
    res2, _ = _run(st, aid, key="b")  # a position (NOISE / CANDACE / this leg) is already open -> skip
    assert not res2.ok and res2.reason == "POSITION_OPEN"
    # opposite side on another account while the first is open: household equity-index lock
    aid2 = authed.post("/api/accounts", json={"label": "L2", "stage": "EVAL", "balance": "100000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid2}", json={"armed": True, "selected": True})
    res3, _ = _run(st, aid2, key="c", direction=Direction.SHORT)
    assert not res3.ok and "HEDGE" in (res3.reason or ""), res3


def test_card_option_and_setting(authed):
    h = authed.app.state.rules
    cfgs = {"fast_pass_100k_cfg": CFG100, "fast_pass_25k_cfg": CFG25}
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update=cfgs)})
    tg = {t["key"]: t for t in authed.get("/api/strategies").json()["toggles"]}
    late = tg["fast_pass_100k"]["late"]
    assert late["setting"] == "strategy.fast_pass_late_day" and late["value"] is False
    assert "3rd edge: late-day momentum (UNVERIFIED, held-out PF 1.10)" in late["label"]
    assert "3 micro(s)" in late["detail"] and "< $1,000: 1" in late["detail"] and "60 pt stop" in late["detail"]
    assert tg["fast_pass_25k"]["late"] is None  # a plan without a late size shows no option
    put = authed.put("/api/risk/settings", json={"changes": {"strategy.fast_pass_late_day": True}, "note": "t"})
    assert put.status_code == 200 and authed.app.state.rules.rules.strategy.fast_pass_late_day is True
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.fast_pass_late_day": "maybe"}, "note": "t"})
    assert bad.status_code in (400, 422)


def test_listed_as_active_strategy(loaded_rules):
    from app.api.live import active_strategies

    assert "LATE_DAY" not in active_strategies(_rules(loaded_rules, on=False))
    assert "LATE_DAY" in active_strategies(_rules(loaded_rules, on=True))


def _fast_eval_early(st, extra=2):
    from app.config import FastEarlyCfg

    h = st.controller.rules
    fe = h.rules.fast_eval.model_copy(update={"early": FastEarlyCfg(enabled=True, first_trades=10, extra_contracts=extra,
                                                                    cushion_frac=D("0.05"))})  # fmt: skip
    h.rules = h.rules.model_copy(update={"fast_eval": fe})
    h.fast_eval_on = True


def test_fast_evaluation_never_lifts_the_braked_late_size(authed, clock):
    """F (M3): D87 early extras must not raise the late leg above late_contracts / the late_steps brake."""
    st, aid = _setup(authed, clock, cushion=D(999))  # brake: 1 micro
    _fast_eval_early(st)
    res, sz = _run(st, aid)
    assert sz[-1]["contracts"] == 1 and sz[-1]["braked"] is True
    assert res.ok and res.contracts == 1, res


def test_paper_only_applies_to_late_day_and_mgc_strategies(authed, clock):
    """F (nit): the plan file's paper_only opt-in was ignored for LATE_DAY, MGC_NOISE and MGC_CANDACE."""
    st, aid = _setup(authed, clock)
    h = st.controller.rules
    s_ = h.rules.strategy
    mc = s_.mgc_noise_candace_cfg
    for mode, upd in (
        ("LATE_DAY", {"late_day_cfg": s_.late_day_cfg.model_copy(update={"paper_only": True})}),
        ("MGC_NOISE", {"mgc_noise_candace_cfg": mc.model_copy(update={"noise": mc.noise.model_copy(update={"paper_only": True})})}),
        ("MGC_CANDACE", {"mgc_noise_candace_cfg": mc.model_copy(update={"candace": mc.candace.model_copy(update={"paper_only": True})})}),
    ):  # fmt: skip
        h.rules = h.rules.model_copy(update={"strategy": s_.model_copy(update=upd)})
        with st.sessionmaker() as s:
            a = s.get(Account, aid)
            a.is_sim = False
            s.commit()
        sym = "MGC" if mode.startswith("MGC") else "MNQ"
        with st.sessionmaker() as s:
            x = SS._new_signal(
                s, FixedClock(AT), symbol=sym, key=f"{sym}-{mode}-po", direction=Direction.LONG, at=AT,
                gate=(True, "OK", ""), features={},
                plan=(mode, D(20000), D(19940), D(20180), D(60), D(3)),
            )  # fmt: skip
            s.commit()
            sid = x.id
        [res] = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
        assert not res.ok and res.reason == "PAPER_ONLY_STRATEGY", (mode, res)
