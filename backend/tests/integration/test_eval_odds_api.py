"""D137: the Strategy / Risk page APIs serve eval pass / bust from config/eval_odds.yaml (nothing hard-coded)."""

import pytest

from app import eval_odds as E

ERA = {"pass": 70, "bust": 30, "stuck": 0, "open": 0, "days": 40}
ERA2 = {"pass": 50, "bust": 50, "stuck": 0, "open": 0, "days": 40}


def _table(c):
    return {
        "contracts": c,
        "brake": None,
        "eod_on": {"all": ERA, "is": ERA, "j": ERA2},
        "eod_off": {"all": ERA2, "is": ERA2, "j": ERA},
    }


@pytest.fixture
def real_odds(monkeypatch):
    t = {k: _table(1) for k in E.TABLES}
    f = E.OddsFile.model_validate(
        {"version": 1, "study": "test", "source": "x", "plans": {p: t for p in ("lucid_pro_25k", "lucid_daily_25k")}}
    )
    monkeypatch.setattr(E, "load_odds", lambda: f)


def _strategies(authed):
    return authed.get("/api/strategies").json()


def test_not_measured_yet_with_the_placeholder_file(authed):
    d = _strategies(authed)
    noise = next(s for s in d["strategies"] if s["key"] == "noise")
    assert noise["eval_odds"]["text"] == "not measured yet" and noise["pro25k_pass_pct"] is None
    assert all(r["pass_pct"] is None and r["odds_text"] == "not measured yet" for r in d["presets"]["rows"])
    assert "not measured yet" in {t["key"]: t for t in d["toggles"]}["eval_size_s19"]["note"]
    assert authed.get("/api/risk/eval-mode").json()["odds"]["regular"]["text"] == "not measured yet"


def test_numbers_follow_plan_table_and_eod_toggle(authed, real_odds):
    plan = authed.app.state.rules.plan
    assert plan == "lucid_daily_25k"
    d = _strategies(authed)
    noise = next(s for s in d["strategies"] if s["key"] == "noise")
    assert noise["eval_odds"]["plan"] == plan and noise["eval_odds"]["table"] == "regular"
    assert (noise["pro25k_pass_pct"], noise["pro25k_bust_pct"]) == (50, 50)  # toggle OFF cell
    assert noise["eval_odds"]["text"] == "pass 50% / bust 50% · last 12 mo 70/30 · EOD toggle OFF"
    main = next(s for s in d["strategies"] if s["key"] == "pm_fade")
    assert main["eval_odds"]["table"] == "regular_fade_on"
    assert d["size_profiles"]["odds"]["high"]["pass_pct"] == 50
    assert "pass 50% / bust 50%" in {t["key"]: t for t in d["toggles"]}["fade_eval_off"]["note"]
    # presets map to their own plan (lucid_pro_50k is absent from this fixture -> not measured)
    rows = {r["key"]: r for r in d["presets"]["rows"]}
    assert rows["pro25k_s19"]["pass_pct"] == 50 and rows["pro50k_s19"]["odds_text"] == "not measured yet"
    # flip the EOD toggle: every place follows it
    r = authed.put("/api/risk/settings", json={"changes": {"strategy.eod_closed_balance": True}, "note": "t"})
    assert r.status_code == 200
    d = _strategies(authed)
    noise = next(s for s in d["strategies"] if s["key"] == "noise")
    assert (noise["pro25k_pass_pct"], noise["eval_odds"]["eod_on"]) == (70, True)
    assert {r["key"]: r for r in d["presets"]["rows"]}["pro25k_s19"]["pass_pct"] == 70
    assert authed.get("/api/risk/eval-mode").json()["odds"]["regular"]["text"].endswith("EOD toggle ON")
    # size table follows the High-risk / Suggested buttons
    authed.put("/api/risk/settings", json={"changes": {"strategy.high_risk": True}, "note": "t"})
    noise = next(s for s in _strategies(authed)["strategies"] if s["key"] == "noise")
    assert noise["eval_odds"]["table"] == "high"
