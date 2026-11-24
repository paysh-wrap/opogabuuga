"""D168: every account follows its OWN rule plan (MLL / DLL / target / consistency / payouts / fast pass) while the
household rules (hedge lock, one position per account, news / flatten times, strategy buttons) stay global."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.models import Account
from app.risk.fast_pass import plan_fast_pass
from tests.integration.test_split_risk import _ext, _sig

AT = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)
SHORT = (D(20000), D(20020), D(19900), D(20), D(5))


def _two(authed, clock, **strategy):
    """Active plan = lucid_daily_25k (conftest); account A follows lucid_pro_25k, account B lucid_pro_150k."""
    st = authed.app.state
    clock.set(AT)
    ids = []
    for label, bal, plan in (("small", "25000", "lucid_pro_25k"), ("big", "150000", "lucid_pro_150k")):
        r = authed.post("/api/accounts", json={"label": label, "stage": "EVAL", "balance": bal, "plan": plan})
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])
        authed.patch(f"/api/accounts/{ids[-1]}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MNQ"] = D(20000)
    h = st.rules

    def patch(rules):
        s = rules.strategy
        noise = s.noise_cfg.model_copy(update={"contracts": 2})
        upd = {"noise": True, "noise_cfg": noise, **strategy}
        return rules.model_copy(update={"strategy": s.model_copy(update=upd)})

    h.rules = patch(h.rules)
    h.plan_rules = {k: patch(v) for k, v in h.plan_rules.items()}
    return st, ids


def test_accounts_api_shows_each_accounts_plan_and_creation_uses_it(authed, clock):
    st, (a, b) = _two(authed, clock)
    rows = {x["id"]: x for x in authed.get("/api/accounts").json()["accounts"]}
    assert rows[a]["plan"] == "lucid_pro_25k" and rows[b]["plan"] == "lucid_pro_150k"
    assert rows[a]["plan_explicit"] == "lucid_pro_25k" and rows[a]["plan_error"] is None
    assert {p["id"] for p in authed.get("/api/accounts").json()["plans"]} >= {"lucid_pro_25k", "lucid_pro_150k"}
    with st.sessionmaker() as s:  # MLL at creation = size − that plan's own max loss
        assert s.get(Account, a).mll == D(25000) - D(1000)
        assert s.get(Account, b).mll == D(150000) - D(4500)


def test_dashboard_uses_each_accounts_own_mll_dll_and_target(authed, clock):
    _, (a, b) = _two(authed, clock)
    rows = {x["id"]: x for x in authed.get("/api/dashboard").json()["accounts"]}
    assert (rows[a]["max_loss"], rows[b]["max_loss"]) == ("1000", "4500")
    assert (rows[a]["dll_limit"], rows[b]["dll_limit"]) == ("600", "2700")
    assert (rows[a]["target_left"], rows[b]["target_left"]) == ("1250", "9000")
    assert rows[a]["plan"] == "lucid_pro_25k" and rows[b]["plan"] == "lucid_pro_150k"


def test_controller_mll_state_and_fast_pass_follow_the_account(authed, clock):
    st, (a, b) = _two(authed, clock)
    with st.sessionmaker() as s:
        aa, bb = s.get(Account, a), s.get(Account, b)
        assert st.controller._mll_state(aa).max_loss == D(1000)
        assert st.controller._mll_state(bb).max_loss == D(4500)
        for acct, size in ((aa, 25000), (bb, 150000)):
            r = st.rules.rules_for(acct)
            _, cfg = plan_fast_pass(r.strategy, acct.starting_balance)
            assert cfg is not None and cfg.account_size == size
            assert r.eval.profit_target == (D(1250) if size == 25000 else D(9000))


def test_hedge_lock_still_spans_both_plans(authed, clock):
    st, (a, b) = _two(authed, clock, ai_duo=True)
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[a]))[0].ok
    sig = _sig(st, "AI_DUO", "D1", direction=_short(), plan=SHORT)
    res = asyncio.run(st.controller.execute(sig, "automation", only=[b]))
    assert res[0].ok is False and res[0].reason == "HEDGE_LOCK", res


def _short():
    from app.engine.trade_plan import Direction

    return Direction.SHORT


def test_invalid_plan_blocks_new_entries_with_banner_and_log(authed, clock):
    st, (a, b) = _two(authed, clock)
    with st.sessionmaker() as s:
        s.get(Account, b).plan = "no_such_plan"
        s.commit()
        st.rules.refresh(s)
    assert "no_such_plan" in (st.rules.account_error(_acct(st, b)) or "")
    assert st.rules.error is None  # the active plan is fine: the other account still trades
    res = asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[b]))
    assert res[0].ok is False and res[0].reason == "ACCOUNT_PLAN_INVALID", res
    assert not [t for t in st.controller.om.trades.values() if t.account == _ext(st, b)]
    banner = authed.get("/api/automation").json()["rules_error"]
    assert banner and "no_such_plan" in banner and "new entries blocked" in banner
    assert any(n for n in st.controller.notices if "rule plan" in str(n).lower())
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N2"), "automation", only=[a]))[0].ok


def _acct(st, aid):
    with st.sessionmaker() as s:
        s.expunge_all()
        return s.get(Account, aid)


def test_patch_plan_validates_files_and_reverts_to_inferred(authed, clock):
    st, (a, _) = _two(authed, clock)
    assert authed.patch(f"/api/accounts/{a}", json={"plan": "../etc/passwd"}).status_code == 422
    assert authed.patch(f"/api/accounts/{a}", json={"plan": "nope"}).status_code == 422
    r = authed.patch(f"/api/accounts/{a}", json={"plan": "lucid_pro_100k"})
    assert r.status_code == 200 and r.json()["plan"] == "lucid_pro_100k"
    assert "lucid_pro_100k" in st.rules.plan_rules
    r = authed.patch(f"/api/accounts/{a}", json={"plan": ""})
    assert r.json()["plan"] == "lucid_daily_25k"  # no lucid_daily_25k family sibling: active plan


def test_create_rejects_unknown_plan(authed):
    r = authed.post("/api/accounts", json={"label": "x", "stage": "EVAL", "balance": "25000", "plan": "nope"})
    assert r.status_code == 422


def test_sizes_inferred_when_no_plan_given(authed, clock):
    st = authed.app.state
    st.rules.plan = "lucid_pro_25k"  # pretend the active plan is a Pro plan
    aid = authed.post("/api/accounts", json={"label": "i", "stage": "EVAL", "balance": "100000"}).json()["id"]
    assert st.rules.plan_for(_acct(st, aid)) == "lucid_pro_100k"
    with st.sessionmaker() as s:
        assert s.get(Account, aid).mll == D(100000) - D(3000)


@pytest.mark.parametrize("name", ["lucid_pro_25k", "lucid_pro_150k"])
def test_other_plans_are_loaded_once_and_cached(authed, clock, name):
    st, _ = _two(authed, clock)
    base = st.rules._bases[name]
    with st.sessionmaker() as s:
        st.rules.refresh(s)
    assert st.rules._bases[name] is base  # yaml read once, not per refresh


def test_ensure_account_plan_records_a_missing_file_and_reports_not_loaded(authed, clock):
    st, _ids = _two(authed, clock)
    h = st.rules
    acct = Account(broker_account_id="Z", stage="EVAL", drawdown_type="eod", starting_balance=D(25000), plan="ghost")
    assert h.account_error(acct) == "rule plan 'ghost' is not loaded"  # never silently another plan's numbers
    with st.sessionmaker() as s:
        h.ensure_account_plan(s, acct)
    assert "ghost" in (h.account_error(acct) or "") and "not found" in (h.account_error(acct) or "")
    assert h.rules_for(acct) is h.rules  # display fallback only; trading paths check account_error first
    with st.sessionmaker() as s:
        with pytest.raises(ValueError, match="not found"):
            h.rules_for_name(s, "ghost")
        assert h.rules_for_name(s, "lucid_pro_50k").eval.profit_target == D(3000)
