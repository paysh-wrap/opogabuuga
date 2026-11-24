from pathlib import Path

import pytest

from app.risk import household as h

LIM = h.HouseholdLimits(max_active_funded=5, max_active_live=5, max_total_real=10, status="CONFIRMED", source="s")


def test_shipped_file_is_confirmed_and_loads():
    lim = h.load_limits()
    assert (lim.max_active_funded, lim.max_active_live, lim.max_total_real) == (5, 5, 10)
    assert lim.status == "CONFIRMED" and "help center" in lim.source


def test_load_bad_or_missing_file_falls_back_to_strict_defaults(tmp_path: Path):
    for p in (tmp_path / "nope.yaml", tmp_path / "bad.yaml"):
        if p.name == "bad.yaml":
            p.write_text("max_active_funded: [", encoding="utf-8")
        got = h.load_limits(p)
        assert (got.max_active_funded, got.max_active_live, got.max_total_real) == (5, 5, 10)
    q = tmp_path / "x.yaml"
    q.write_text("max_active_funded: 3\n", encoding="utf-8")  # a missing key -> defaults for all (never half-loaded)
    assert h.load_limits(q).max_active_funded == 5


def test_eval_not_counted_by_funded_or_live_limits():
    cur = [("FUNDED", False)] * 5 + [("LIVE", False)] * 5
    assert h.refusal(LIM, "EVAL", cur) is not None  # only the TOTAL (10) stops it
    assert h.refusal(LIM, "EVAL", [("EVAL", False)] * 9) is None
    assert h.refusal(LIM, "EVAL", [("FUNDED", False)] * 5 + [("LIVE", False)] * 4) is None


def test_sixth_funded_and_sixth_live_refused_with_message():
    five = [("FUNDED", False)] * 5
    m = h.refusal(LIM, "FUNDED", five)
    assert m is not None and "5 active funded" in m and "all funded plan types" in m
    assert h.refusal(LIM, "FUNDED", five[:4]) is None
    m = h.refusal(LIM, "LIVE", [("LIVE", False)] * 5)
    assert m is not None and "5 active live" in m
    assert h.refusal(LIM, "LIVE", five) is None  # funded do not eat live slots: 5 + 5 = 10


def test_closed_accounts_are_not_active():
    cur = [("FUNDED", True)] * 3 + [("FUNDED", False)] * 5
    assert h.refusal(LIM, "FUNDED", cur) is not None
    assert h.refusal(LIM, "FUNDED", [("FUNDED", True)] * 9 + [("FUNDED", False)] * 4) is None  # closed ones leave the total
    assert h.counts(cur) == {"FUNDED": 5, "LIVE": 0, "EVAL": 0}


def test_total_limit():
    m = h.refusal(LIM, "EVAL", [("EVAL", False)] * 10)
    assert m is not None and "at most 10" in m


def test_unknown_stage_rejected():
    with pytest.raises(ValueError):
        h.refusal(LIM, "X", [])


# ---------- 10 accounts: selector + household-wide hedge lock ----------
def test_selector_takes_up_to_ten_and_clamps():
    from app.automation.account_selector import Candidate, select

    c = [Candidate(i, i, True, True, False, "FUNDED" if i < 5 else "LIVE", False) for i in range(12)]
    assert [x.id for x in select(c, 10, False)] == list(range(10))
    assert len(select(c, 99, False)) == 10 and len(select(c, 0, False)) == 1


def test_hedge_lock_spans_all_ten_accounts():
    from app.config import load_rules
    from app.risk.hedge_lock import OpenPosition, hedge_conflict

    from tests.conftest import RULES_PATH

    R = load_rules(RULES_PATH).rules
    opn = [OpenPosition(f"ACC{i}", "MNQ", "STD", "LONG") for i in range(10)]
    assert hedge_conflict(R, "MNQ", "SHORT", opn) is not None
    assert hedge_conflict(R, "MNQ", "LONG", opn) is None
    only_last = [OpenPosition("ACC9", "MES", "STD", "SHORT")]  # the 10th account alone locks the other direction
    assert hedge_conflict(R, "MNQ", "LONG", only_last).account == "ACC9"


def test_household_api_five_funded_plus_five_live_then_refused(authed):
    def add(stage, i):
        return authed.post("/api/accounts", json={"label": f"{stage}{i}", "stage": stage, "tradovate_account": f"{stage}{i}"})

    for i in range(5):
        assert add("EVAL", i).status_code == 200  # eval accounts are not counted by the funded / live limits
    # 5 evals + 5 funded would be 10; remove the evals' share by closing them at the firm
    from app.models import Account

    with authed.app.state.sessionmaker() as s:
        for a in s.query(Account):
            a.closed_by_firm = True
        s.commit()
    for i in range(5):
        assert add("FUNDED", i).status_code == 200
        assert add("LIVE", i).status_code == 200
    r = add("FUNDED", 6)
    assert r.status_code == 409 and "5 active funded" in r.text
    r = add("LIVE", 6)
    assert r.status_code == 409 and "5 active live" in r.text
    r = add("EVAL", 6)
    assert r.status_code == 409 and "at most 10" in r.text
    assert authed.put("/api/accounts/selection", json={"count": 10}).status_code == 200
    assert authed.put("/api/accounts/selection", json={"count": 11}).status_code == 422


def test_accounts_list_reports_household_limits(authed):
    authed.post("/api/accounts", json={"label": "F", "stage": "FUNDED", "tradovate_account": "LF1"})
    authed.post("/api/accounts", json={"label": "P", "stage": "FUNDED"})  # paper: not a Lucid account, not counted
    h = authed.get("/api/accounts").json()["household"]
    assert (h["max_active_funded"], h["max_active_live"], h["max_total"]) == (5, 5, 10)
    assert h["active"] == {"FUNDED": 1, "LIVE": 0, "EVAL": 0} and h["status"] == "CONFIRMED"
