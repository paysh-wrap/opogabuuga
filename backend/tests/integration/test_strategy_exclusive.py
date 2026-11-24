"""D167: one strategy button ON at a time (API rejects two-on with 422); fast-pass plans stay independent; the
dashboard shows all four fast-pass cards."""

from app.risk.settings_store import strategy_choices_on


def _put(authed, changes):
    return authed.put("/api/risk/settings", json={"changes": changes, "note": "t"})


def test_two_strategy_buttons_on_is_rejected(authed):
    assert _put(authed, {"strategy.jj_fpt": True}).status_code == 200
    r = _put(authed, {"strategy.gala_pa": True})
    assert r.status_code == 422 and "only one strategy button" in str(r.json())
    # turning the old one off in the same save is the allowed way to switch
    assert _put(authed, {"strategy.jj_fpt": False, "strategy.gala_pa": True}).status_code == 200
    assert _put(authed, {"strategy.gala_pa": False}).status_code == 200  # everything off is allowed


def test_main_pair_is_one_choice_and_split_is_one_choice(authed):
    assert _put(authed, {"strategy.noise": True, "strategy.candace_ict": True}).status_code == 200
    assert _put(authed, {"strategy.order_flow": True}).status_code == 422
    assert _put(authed, {"strategy.ai_duo": True}).status_code == 422
    r = _put(authed, {"strategy.candace_ict": False, "strategy.noise_ai_split": True, "strategy.ai_duo": True})
    assert r.status_code == 200  # NOISE + AI Duo split = the one choice that uses both
    assert _put(authed, {"strategy.candace_ict": True}).status_code == 422


def test_fast_pass_plans_are_independent_and_late_day_is_a_sub_option(authed):
    ch = {"strategy.noise": True, "strategy.candace_ict": True, "strategy.fast_pass_late_day": True}
    assert _put(authed, ch).status_code == 200
    on = {f"strategy.fast_pass_{n}k": True for n in (25, 50, 100, 150)}
    assert _put(authed, on).status_code == 200


def test_dashboard_returns_four_fast_pass_cards(authed):
    cards = [t for t in authed.get("/api/strategies").json()["toggles"] if t["key"].startswith("fast_pass_")]
    assert [c["key"] for c in cards] == [f"fast_pass_{n}k" for n in (25, 50, 100, 150)]
    for c in cards:
        assert c["weekly"] is not None and c["on_label"]


def test_choices_on_helper(authed):
    s = authed.app.state.rules.rules.strategy
    assert strategy_choices_on(s) == []


def _legacy_row(authed, version, settings, active):
    from app.models import RiskProfile

    with authed.app.state.sessionmaker() as s:
        s.add(
            RiskProfile(
                kind="standard", version=version, settings=settings, author="legacy",
                note="pre-D167 save", diff={}, active=active,
            )
        )
        s.commit()


def test_rollback_to_two_on_version_leaves_at_most_one_choice_on(authed):
    _legacy_row(authed, 90, {"strategy.jj_fpt": True, "strategy.gala_pa": True}, active=False)
    r = authed.post("/api/risk/rollback/90")
    assert r.status_code == 200, r.text
    assert len(strategy_choices_on(authed.app.state.rules.rules.strategy)) <= 1


def test_loading_pre_d167_settings_with_two_on_keeps_at_most_one_choice(authed):
    from app.risk.settings_store import effective

    _legacy_row(authed, 91, {"strategy.jj_fpt": True, "strategy.gala_pa": True}, active=True)
    with authed.app.state.sessionmaker() as s:
        eff = effective(s, authed.app.state.rules.base)
    assert len(strategy_choices_on(eff.rules.strategy)) <= 1
