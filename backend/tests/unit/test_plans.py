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
    """D55 (user 2026-11-09): NOISE (verified noise-area momentum, MNQ) on; Opening-drive is a button, off; the
    verified NOISE parameters ship unchanged. D105: no LunqFX key."""
    s = r(plan).strategy
    assert s.noise and not hasattr(s, "open_drive") and not hasattr(s, "lunqfx")
    n = s.noise_cfg
    assert (n.symbol, n.lookback_days, n.check_minutes, n.first_check, n.flat_at) == ("MNQ", 14, 60, "10:00", "16:00")
    assert n.emergency_stop_pct == D("0.01") and n.emergency_stop_usd == D(250) and n.max_entries_per_day == 3
    assert n.contracts == 1  # fallback; D63 size_table sizes each account
    assert not s.order_flow_cfg.paper_only and not s.ai_duo_cfg.paper_only  # D102: none forced paper-only


def test_legacy_daily_plan_loads_without_lunqfx():
    """D105: the legacy Daily plan still loads (an old strategy.lunqfx / lunqfx_structure key is ignored)."""
    from app.config import StrategyCfg

    s = load_rules(RULES / "lucid_daily_25k.yaml").rules.strategy
    assert not s.noise and not hasattr(s, "open_drive") and not hasattr(s, "lunqfx")
    old = StrategyCfg.model_validate(
        {"lunqfx": True, "lunqfx_structure": {"enabled": True}, "open_drive": True, "open_drive_cfg": {}, "noise": True}
    )
    dumped = old.model_dump()
    assert old.noise and not {"lunqfx", "lunqfx_structure", "open_drive", "open_drive_cfg"} & set(dumped)  # D107


def test_size_table_validation_and_plans():  # D63
    from pathlib import Path

    from pydantic import ValidationError

    from app.config import SizeTierCfg, load_rules

    with pytest.raises(ValidationError):
        SizeTierCfg(account_size=D(0), mll=D(1000), contracts=1)
    with pytest.raises(ValidationError):
        SizeTierCfg(account_size=D(50000), mll=D(2000), contracts=2, brake_below=D("0.5"))
    with pytest.raises(ValidationError):
        SizeTierCfg(account_size=D(50000), mll=D(2000), contracts=2, brake_below=D("0.5"), brake_contracts=2)
    with pytest.raises(ValidationError):
        SizeTierCfg(account_size=D(100000), mll=D(3000), contracts=2, grow_per=D(1200))  # no max_contracts
    with pytest.raises(ValidationError):
        SizeTierCfg(account_size=D(100000), mll=D(3000), contracts=2, day_lock_pct=D(2))
    with pytest.raises(ValidationError):
        SizeTierCfg(account_size=D(25000), mll=D(1000), contracts=3, stop_usd=D(0))
    with pytest.raises(ValidationError):
        SizeTierCfg(account_size=D(25000), mll=D(1000), contracts=4, taper_below_remaining=D("0.5"))  # needs both
    with pytest.raises(ValidationError):
        SizeTierCfg(account_size=D(25000), mll=D(1000), contracts=4, taper_below_remaining=D(2), taper_contracts=1)
    with pytest.raises(ValidationError):
        SizeTierCfg(account_size=D(25000), mll=D(1000), contracts=2, taper_below_remaining=D("0.5"), taper_contracts=2)
    root = Path(__file__).resolve().parents[3] / "config" / "rules"
    for f in sorted(root.glob("lucid_*.yaml")):
        st = load_rules(f).rules.strategy
        if f.stem.startswith(("lucid_pro", "lucid_flex")):
            assert [(t.account_size, t.contracts) for t in st.size_table] == [
                (D(25000), 1),
                (D(50000), 2),
                (D(100000), 2),
                (D(150000), 3),
            ]
            assert [(t.account_size, t.contracts) for t in st.size_table_high] == [
                (D(25000), 1),
                (D(50000), 2),
                (D(100000), 3),
                (D(150000), 4),
            ]
            assert all(t.brake_below is not None for t in st.size_table_high if t.contracts > 1)  # brake on every row
            assert not st.high_risk and st.active_size_table() is st.size_table
            if f.stem.startswith("lucid_pro"):  # D66: Evaluation Mode table (Pro only — Flex evals were not studied)
                hi = {t.account_size: t for t in st.size_table_eval_high}  # D69 high-risk evals
                assert hi[D(25000)].contracts == 3 and hi[D(25000)].taper_contracts == 1
                assert hi[D(25000)].stop_usd == D(150)  # D70: 3 micros × $150 = $450 total
                assert hi[D(25000)].taper_below_remaining == D("0.5") and hi[D(150000)].contracts == 4
                assert st.active_eval_table() is st.size_table_eval
                assert st.model_copy(update={"high_risk": True}).active_eval_table() is st.size_table_eval_high
                ev = {t.account_size: t for t in st.size_table_eval}
                assert ev[D(150000)].contracts == 4 and ev[D(25000)].contracts == 1
                assert ev[D(100000)].grow_per == D(1200) and ev[D(100000)].max_contracts == 4
                assert ev[D(100000)].day_lock_pct == D("0.33")
            else:
                assert st.size_table_eval == []
            hi = st.model_copy(update={"high_risk": True})
            assert hi.active_size_table() is st.size_table_high


def test_pro_plans_pay_out_the_maximum_on_their_cadence():  # D67 / D68
    from pathlib import Path

    from app.config import load_rules

    root = Path(__file__).resolve().parents[3] / "config" / "rules"
    gap = {"lucid_pro_25k": 10, "lucid_pro_50k": 10, "lucid_pro_100k": 5, "lucid_pro_150k": 5}  # trading days
    for stem, n in gap.items():
        pc = load_rules(root / f"{stem}.yaml").rules.payouts
        assert (pc.frequency, pc.mode, pc.min_sessions_between, pc.min_pct_of_cap) == (
            "every_n_sessions",
            "max_eligible",
            n,
            None,
        ), stem


def test_pro_plans_freeze_with_50_left_to_the_loss_limit():  # D71
    from pathlib import Path

    from app.config import load_rules

    root = Path(__file__).resolve().parents[3] / "config" / "rules"
    for stem in ("lucid_pro_25k", "lucid_pro_50k", "lucid_pro_100k", "lucid_pro_150k"):
        assert load_rules(root / f"{stem}.yaml").rules.internal.kill_switch_mll_distance == D(50), stem
    assert load_rules(root / "lucid_daily_25k.yaml").rules.internal.kill_switch_mll_distance == D(
        100
    )  # others keep $100
