from decimal import Decimal as D
from pathlib import Path

import pytest

from app.config import load_rules
from app.phases.phase_engine import firm_max_micros, funded_live_move_triggered, stage_rules
from app.risk.validation import max_base_for_stage, validate

RULES = Path(__file__).resolve().parents[3] / "config" / "rules"


def r(name):
    return load_rules(RULES / f"{name}.yaml").rules


@pytest.mark.parametrize("plan", [f"lucid_{p}_{k}k" for p in ("pro", "flex") for k in (25, 50, 100, 150)])
def test_every_plan_validates(plan):
    v = validate(r(plan))
    assert v.ok, v.errors


def test_flex_funded_scaling_by_profit():
    f = r("lucid_flex_50k")
    assert firm_max_micros(f, "FUNDED", D(0)) == 20
    assert firm_max_micros(f, "FUNDED", D(1500)) == 30
    assert firm_max_micros(f, "FUNDED", D(9999)) == 40
    assert firm_max_micros(f, "FUNDED", D(-300)) == 20  # below the first tier → smallest
    assert firm_max_micros(f, "EVAL", D(0)) == 40  # eval: full size
    assert firm_max_micros(r("lucid_pro_50k"), "FUNDED", D(0)) == 40  # Pro: no scaling


def test_pro_has_no_eval_consistency_and_25k_no_eval_dll():
    p = r("lucid_pro_25k")
    assert p.eval.consistency_max_day_pct is None and p.eval.daily_loss_limit is None
    assert max_base_for_stage(p, "EVAL") == D(2250)  # MLL + target
    assert not funded_live_move_triggered(D(99999), p)  # no $-per-day trigger on Pro/Flex
    assert stage_rules(p, "FUNDED").news_hard_breach is False  # news allowed on Pro/Flex


def test_flex_payout_rules():
    pr = r("lucid_flex_100k").funded.payout
    assert (pr.max_pct_of_profit, pr.min_profitable_days, pr.min_day_profit, pr.lock_mll_on_payout) == (
        D("0.5"),
        5,
        D(200),
        True,
    )


def test_gold_market_settings():
    from datetime import UTC, datetime

    from app.engine.filters import in_windows

    g = r("lucid_flex_25k").instruments["MGC"]
    assert g.min_stop_ticks == 16 and g.news_after_min == 15 and g.tick_value == D(1)
    assert in_windows(datetime(2026, 11, 5, 8, 30, tzinfo=UTC), g.windows)  # 03:30 ET London open
    assert in_windows(datetime(2026, 11, 5, 17, 0, tzinfo=UTC), g.windows)  # 12:00 ET (D36: 03:00–15:30)
    assert not in_windows(datetime(2026, 11, 5, 21, 0, tzinfo=UTC), g.windows)  # 16:00 ET


@pytest.mark.parametrize("plan", [f"lucid_{p}_{k}k" for p in ("pro", "flex") for k in (25, 50, 100, 150)])
def test_main_strategy_d49(plan):
    """D49 (user 2026-11-06: "1.5-2.5"): trend-aligned 1.5–2.5R on MGC + MNQ + MES in every Pro/Flex plan."""
    p = r(plan)
    assert p.trade_plan.rr_min == D("1.5") and p.trade_plan.rr_max == D("2.5")  # targets 1.5–2.5R
    assert p.filters.no_break_rr_cap is None  # no 1R targets
    t = p.filters.trend
    assert t.utbot_5m and t.ema200_5m and not t.vwap and not t.squeeze_5m_15m  # Squeeze failed on 7 years (D45)
    for sym in ("MGC", "MNQ"):  # D50 (user): MGC + MNQ only
        assert p.instruments[sym].intraday_windows is None, sym
    assert p.instruments["MNQ"].enabled and not p.instruments["MGC"].enabled  # D55: every gold test failed → MGC off
    assert "MES" not in p.instruments and not p.instruments["MYM"].enabled  # D51: MES eliminated
    assert p.instruments["MGC"].trend_filters and not p.instruments["MNQ"].trend_filters  # D52: MNQ every setup
    assert p.internal.max_trades_per_day == 3 and p.internal.low_risk_max_trades_per_day == 7  # normal 3, low risk 7
    rm = p.bias.rating_map  # D50: TradingAgents blocks a side only on strong calls
    assert rm["BUY"] == "LONG_ONLY" and rm["SELL"] == "SHORT_ONLY"
    assert rm["OVERWEIGHT"] == rm["HOLD"] == rm["UNDERWEIGHT"] == "NEUTRAL"


def test_no_plan_can_aim_below_15r():
    """D48/D49: a plan with rr_min < 1.5 (like D36's 1.0) is refused at load time — no more 1R trades."""
    import yaml

    from app.config import RulesConfig

    raw = yaml.safe_load((RULES / "lucid_flex_25k.yaml").read_text())
    raw["trade_plan"]["rr_min"] = 1.0
    with pytest.raises(ValueError, match=r"1\.5 <= rr_min"):
        RulesConfig.model_validate(raw)
    for f in sorted(RULES.glob("*.yaml")):  # every shipped plan, incl. the legacy Daily file
        assert load_rules(f).rules.trade_plan.rr_min >= D("1.5"), f.name


@pytest.mark.parametrize("plan", [f"lucid_{p}_{k}k" for p in ("pro", "flex") for k in (25, 50, 100, 150)])
def test_strategy_buttons_d55(plan):
    """D55 (user 2026-11-09): NOISE (verified noise-area momentum, MNQ) on; LunqFX and Opening-drive are buttons, off;
    Opening-drive is paper-only; the verified NOISE parameters ship unchanged."""
    s = r(plan).strategy
    assert s.noise and not s.lunqfx and not s.open_drive
    n = s.noise_cfg
    assert (n.symbol, n.lookback_days, n.check_minutes, n.first_check, n.flat_at) == ("MNQ", 14, 60, "10:00", "16:00")
    assert n.emergency_stop_pct == D("0.01") and n.emergency_stop_usd == D(250) and n.max_entries_per_day == 3
    assert n.contracts == {"lucid_pro_150k": 6, "lucid_pro_100k": 4}.get(plan, 1)  # D62b: user sizing
    assert s.open_drive_cfg.paper_only


def test_legacy_daily_plan_keeps_lunqfx_only():
    s = load_rules(RULES / "lucid_daily_25k.yaml").rules.strategy
    assert s.lunqfx and not s.noise and not s.open_drive


def test_big_pro_plans_size_main_strategy_per_user():  # D62b: 150K = 6 micros, 100K = 4
    from pathlib import Path

    from app.config import load_rules

    root = Path(__file__).resolve().parents[3] / "config" / "rules"
    st = load_rules(root / "lucid_pro_150k.yaml").rules.strategy
    assert st.noise_cfg.contracts == 6 and st.pm_fade_cfg.contracts == 6 and st.noise and st.pm_fade
    assert st.noise_cfg.emergency_stop_usd == D(250)  # per contract → $1,500 worst case at 6 micros
    hundred = load_rules(root / "lucid_pro_100k.yaml").rules
    assert hundred.strategy.noise_cfg.contracts == 4 and hundred.strategy.pm_fade_cfg.contracts == 4
    assert (
        hundred.internal.internal_max_micros >= 4
        and load_rules(root / "lucid_pro_150k.yaml").rules.internal.internal_max_micros >= 6
    )
    small = load_rules(root / "lucid_pro_25k.yaml").rules.strategy
    assert small.noise_cfg.contracts == 1 and small.pm_fade_cfg.contracts == 1
