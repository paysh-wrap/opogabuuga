"""D175: MAIN and Order Flow are mutually exclusive (also through the Order Flow options); the ONLY way they run
together is the combined choice "MAIN FAST PASS + ORDER FLOW (separate accounts)" (ar_side_by_side ON, 2+ eligible
accounts). Iceberg proxy (zone_atr) is forced OFF."""

import asyncio

from app.risk.settings_store import COMBINED_CHOICE, strategy_choices_on
from tests.integration.test_ar_side_by_side import _on
from tests.integration.trade_helpers import _setup, _sig

SBS = "strategy.order_flow_cfg.ar_side_by_side"
MAIN = {"strategy.noise": True, "strategy.candace_ict": True}


def _put(authed, changes):
    return authed.put("/api/risk/settings", json={"changes": changes, "note": "t"})


def _accounts(authed, n):
    for i in range(n):
        aid = authed.post("/api/accounts", json={"label": f"x{i}", "stage": "EVAL", "balance": "25000"}).json()["id"]
        authed.patch(f"/api/accounts/{aid}", json={"selected": True})


def _on_now(authed):
    return strategy_choices_on(authed.app.state.rules.rules.strategy)


def test_plain_main_and_plain_order_flow_are_exclusive(authed):
    assert _put(authed, MAIN).status_code == 200
    assert _put(authed, {"strategy.order_flow": True}).status_code == 422
    for k in ("amt", "zone_atr", "auction"):  # Order Flow options count as Order Flow ON
        assert _put(authed, {"strategy.order_flow": True, f"strategy.order_flow_cfg.{k}.enabled": True}).status_code == 422
    assert _put(authed, {**{k: False for k in MAIN}, "strategy.order_flow": True}).status_code == 200
    assert _put(authed, {"strategy.noise": True}).status_code == 422  # main cannot join plain Order Flow
    assert _put(authed, {"strategy.candace_ict": True}).status_code == 422
    assert _on_now(authed) == ["order_flow"]


def test_ar_toggle_alone_never_makes_plain_main_plus_order_flow_legal(authed):
    _accounts(authed, 2)
    assert _put(authed, {**MAIN}).status_code == 200
    r = _put(authed, {"strategy.order_flow": True})  # no combined switch: refused
    assert r.status_code == 422 and "combined" in str(r.json()) or "one strategy" in str(r.json())


def test_combined_is_a_legal_third_choice_with_two_accounts(authed):
    _accounts(authed, 2)
    assert _put(authed, MAIN).status_code == 200
    assert _put(authed, {"strategy.order_flow": True, SBS: True}).status_code == 200
    assert _on_now(authed) == [COMBINED_CHOICE]
    assert _put(authed, {"strategy.jj_fpt": True}).status_code == 422  # a 3rd choice is still refused
    # turning main off leaves plain Order Flow, one choice
    assert _put(authed, {k: False for k in MAIN}).status_code == 200
    assert _on_now(authed) == ["order_flow"]


def test_combined_blocked_with_fewer_than_two_eligible_accounts(authed):
    _accounts(authed, 1)
    assert _put(authed, MAIN).status_code == 200
    r = _put(authed, {"strategy.order_flow": True, SBS: True})
    assert r.status_code == 422 and "at least 2 eligible accounts" in str(r.json())
    assert _on_now(authed) == ["main_noise_candace"]  # no silent fallback to anything else: nothing changed


def test_old_saves_with_main_and_order_flow_load_as_main_only_with_a_banner(authed):
    from tests.integration.test_strategy_exclusive import _legacy_row

    _legacy_row(authed, 95, {**MAIN, "strategy.order_flow": True}, active=True)
    with authed.app.state.sessionmaker() as s:
        authed.app.state.rules.refresh(s)
    assert _on_now(authed) == ["main_noise_candace"]
    assert "strategy.order_flow" not in str(authed.app.state.rules.notice) and "order_flow" in str(authed.app.state.rules.notice)
    d = authed.get("/api/strategies").json()
    assert d["notice"] and next(x for x in d["strategies"] if x["key"] == "order_flow")["enabled"] is False


def test_old_d160_save_main_plus_order_flow_plus_sbs_is_the_combined_choice(authed):
    from tests.integration.test_strategy_exclusive import _legacy_row

    _legacy_row(authed, 96, {**MAIN, "strategy.order_flow": True, SBS: True}, active=True)
    with authed.app.state.sessionmaker() as s:
        authed.app.state.rules.refresh(s)
    assert _on_now(authed) == [COMBINED_CHOICE]


def test_iceberg_proxy_cannot_be_turned_on_and_old_saves_load_off(authed):
    from tests.integration.test_strategy_exclusive import _legacy_row

    z = "strategy.order_flow_cfg.zone_atr.enabled"
    r = _put(authed, {z: True})
    assert r.status_code == 422 and "Iceberg" in str(r.json())
    _legacy_row(authed, 97, {"strategy.order_flow": True, z: True}, active=True)
    with authed.app.state.sessionmaker() as s:
        authed.app.state.rules.refresh(s)
    st = authed.app.state.rules.rules.strategy
    assert st.order_flow_cfg.zone_atr.enabled is False
    card = next(x for x in authed.get("/api/strategies").json()["strategies"] if x["key"] == "order_flow_zone")
    assert card["enabled"] is False and card["disabled"] is True and card["off_for_now"] == "OFF for now"


def test_runtime_one_eligible_account_refuses_ar_side_by_side(authed, clock):
    st, (a,) = _setup(authed, clock, [("a", "25000")], noise=True)
    _on(st, ar_side_by_side=True)
    r = st.rules.rules
    st.rules.rules = r.model_copy(update={"strategy": r.strategy.model_copy(update={"order_flow": True})})
    res = asyncio.run(st.controller.execute(_sig(st, "ORDER_FLOW", "O1"), "automation", only=[a]))
    assert not any(x.ok for x in res) and res[-1].reason == "SBS_NEEDS_2_ACCOUNTS"


def test_size_card_fast_pass_rows_come_from_the_plan_yamls(authed):
    import yaml
    from pathlib import Path

    rows = authed.get("/api/strategies").json()["size_profiles"]["fast_pass_plans"]
    assert [r["key"] for r in rows] == [f"fast_pass_{n}k" for n in (25, 50, 100, 150)]
    root = Path(__file__).resolve().parents[3] / "config" / "rules"
    for r in rows:
        n = int(float(r["account_size"])) // 1000
        cfg = yaml.safe_load((root / f"lucid_pro_{n}k.yaml").read_text())["strategy"][f"fast_pass_{n}k_cfg"]
        assert r["noise_contracts"] == cfg["noise_contracts"] and float(r["noise_stop_usd"]) == float(cfg["noise_stop_usd"])
        assert r["candace_contracts"] == cfg["candace_contracts"]
