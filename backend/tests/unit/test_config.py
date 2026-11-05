from decimal import Decimal

import pytest
import yaml

from app.config import RulesConfig, find_verify_paths, load_yaml_decimal


def _walk(o):  # yields every leaf
    if isinstance(o, dict):
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _walk(v)
    else:
        yield o


def test_no_floats_anywhere(loaded_rules):
    raw = load_yaml_decimal(loaded_rules.source_text)
    assert not any(isinstance(x, float) for x in _walk(raw))
    assert not any(isinstance(x, float) for x in _walk(loaded_rules.rules.model_dump()))


def test_exact_spec_values(loaded_rules):
    r = loaded_rules.rules
    assert r.instruments["MNQ"].tick == Decimal("0.25") and r.instruments["MNQ"].tick_value == Decimal("0.50")
    assert r.eval.profit_target == 1250 and r.eval.daily_loss_limit == 600
    assert r.eval.lock_trigger == 26100 and r.eval.lock_level == 25100
    assert r.internal.risk_pct_by_score == {60: Decimal("0.07"), 75: Decimal("0.09"), 90: Decimal("0.11")}
    assert r.eval_mode.risk_pct_by_score == {60: Decimal("0.10"), 75: Decimal("0.12"), 90: Decimal("0.14")}
    assert r.eval_mode.max_risk_usd == 140 and r.eval_mode.warmup_trades == 10
    assert r.eval_mode.applies_to_stages == ["EVAL"] and r.eval_mode.pace_escalation is False
    assert r.trade_plan.rr_min == 2 and r.trade_plan.rr_max == 3
    assert r.payouts.sweep_above == r.internal.cushion_target_balance == 28100
    assert r.automation.default_mode == "OFF"
    assert r.behavior.max_open_positions_per_account == 1


def test_user_changes_d1_d2(loaded_rules):
    r = loaded_rules.rules
    assert r.internal.windows == [("06:45", "09:30"), ("09:35", "11:30"), ("13:30", "15:30")]
    assert r.instruments["MYM"].tick == Decimal("1.0") and r.instruments["MYM"].tick_value == Decimal("0.50")
    assert r.instruments["MGC"].tick == Decimal("0.10") and r.instruments["MGC"].tick_value == Decimal("1.00")
    assert not r.instruments["MYM"].enabled and not r.instruments["MGC"].enabled  # §16.6 gate first
    assert r.super_group_of("MYM") == r.super_group_of("MNQ") == r.super_group_of("ES") == "EQUITY_INDEX"
    assert r.super_group_of("MGC") == "METALS"
    assert r.schedule.preflight < "06:45" and r.schedule.bias < r.schedule.preflight
    assert r.bias.proxy["YM"] == "DIA" and r.bias.proxy["GC"] == "GLD"
    assert r.bias.pinned_version == "0.7.1"


def test_verify_paths(loaded_rules):
    p = set(loaded_rules.verify_paths)
    for k in (
        "purchase",
        "eval.max_loss_limit",
        "eval.lock_trigger",
        "funded.drawdown_type",
        "funded.payout",
        "live",
        "session",
        "instruments.MNQ",
        "instruments.MGC",
        "instruments.MYM",
    ):
        assert k in p
    assert "eval.profit_target" not in p


def test_verify_parser_nesting():
    text = "a:\n  b: 1   # VERIFY\n  c:\n    d: 2  # VERIFY\ne: 3\n"
    assert find_verify_paths(text) == ["a.b", "a.c.d"]


@pytest.mark.parametrize(
    "path,value",
    [
        (("trade_plan", "rr_min"), 4),
        (("internal", "risk_pct_floor"), 0.5),
        (("eval_mode", "risk_pct_ceiling"), 0.2),
        (("drawdown_guard", "runner_trail_r"), 2.5),
        (("eval_mode", "pace_escalation"), True),
        (("eval_mode", "applies_to_stages"), ["EVAL", "FUNDED"]),
        (("behavior", "min_hold_seconds"), 5),
        (("one_to_one_mode", "rr"), 2),
        (("one_to_one_mode", "max_consecutive_losses_per_day"), 4),
        (("one_to_one_mode", "extended_max_trades_per_day"), 6),
        (("one_to_one_mode", "partial_at_fraction_of_tp"), 1.2),
        (("one_to_one_mode", "single_contract_lock_r"), 0.5),
        (("one_to_one_mode", "single_contract_lock_r"), 0.2),
        (("behavior", "rapid_trade_warn_pct"), 60),
    ],
)
def test_structural_rejects(loaded_rules, path, value):
    raw = load_yaml_decimal(loaded_rules.source_text)
    raw[path[0]][path[1]] = load_yaml_decimal(yaml.safe_dump({"v": value}))["v"]
    with pytest.raises(ValueError):
        RulesConfig.model_validate(raw)


def test_unknown_key_rejected(loaded_rules):
    raw = load_yaml_decimal(loaded_rules.source_text)
    raw["internal"]["surprise"] = 1
    with pytest.raises(ValueError):
        RulesConfig.model_validate(raw)


def test_lucid_symbols_and_fees(loaded_rules):
    i = loaded_rules.rules.instruments
    assert {s: (x.exchange, x.tv_symbol, x.fee_rt) for s, x in i.items()} == {
        "MNQ": ("CME", "MNQ1!", Decimal("1.00")),
        "MES": ("CME", "MES1!", Decimal("1.00")),
        "MYM": ("CBOT", "MYM1!", Decimal("1.00")),
        "MGC": ("COMEX", "MGC1!", Decimal("1.60")),
    }


def test_lucid_microscalp_rule(loaded_rules):
    b = loaded_rules.rules.behavior
    assert (b.firm_microscalp_hold_seconds, b.firm_microscalp_pct, b.min_hold_seconds, b.rapid_trade_warn_pct) == (
        5,
        50,
        7.5,
        20,
    )
    assert "behavior.firm_microscalp_hold_seconds" in loaded_rules.verify_paths


def test_one_to_one_mode_d7(loaded_rules):
    o = loaded_rules.rules.one_to_one_mode
    assert o.enabled is False  # off until the user turns it on
    assert (o.rr, o.partial_at_fraction_of_tp, o.partial_qty_fraction) == (1, Decimal("0.75"), Decimal("0.5"))
    assert (o.max_consecutive_losses_per_day, o.max_trades_per_day, o.extended_max_trades_per_day) == (3, 3, 5)
    assert o.extend_after_win_streak == 3
    assert loaded_rules.rules.internal.max_consecutive_losses_per_day == 2  # normal mode unchanged


def test_one_to_one_answers_and_d9(loaded_rules):
    r = loaded_rules.rules
    o = r.one_to_one_mode
    assert o.breakeven_after_partial is True
    assert o.single_contract_lock_r == Decimal("0.30")
    assert o.single_contract_lock_bounds == (Decimal("0.25"), Decimal("0.35"))
    assert o.stages == ["EVAL", "FUNDED", "LIVE"]
    assert o.gate.min_trades >= 100 and o.gate.min_e_net_r >= Decimal("0.20")
    assert r.funded.drawdown_type == "intraday" and r.eval.drawdown_type == "eod"  # D20
    assert "funded.drawdown_type" in loaded_rules.verify_paths


def test_d16_approvals(loaded_rules):
    r = loaded_rules.rules
    f = r.one_to_one_mode.filters
    assert (f.target_within_t1, f.require_choch, f.require_bias_and_htf) == (True, True, True)
    assert (f.t1_rate_min, f.t1_rate_min_samples, f.min_score) == (Decimal("0.65"), 30, 75)
    assert f.atr_pct_band == (Decimal(10), Decimal(90)) and f.news_after_min == 5
    assert r.internal.consistency_on_funded and r.internal.funded_consistency_pct == 40
    assert r.internal.funded_consistency_reference_min == 1250


def test_one_to_one_filters_can_only_be_stricter(loaded_rules):
    raw = load_yaml_decimal(loaded_rules.source_text)
    raw["one_to_one_mode"]["filters"]["min_score"] = 50
    with pytest.raises(ValueError):
        RulesConfig.model_validate(raw)
    raw = load_yaml_decimal(loaded_rules.source_text)
    raw["one_to_one_mode"]["filters"]["news_after_min"] = 0
    with pytest.raises(ValueError):
        RulesConfig.model_validate(raw)
