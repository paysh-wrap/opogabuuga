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


def test_pro_has_eval_consistency_and_25k_eval_dll():
    p = r("lucid_pro_25k")
    assert p.eval.consistency_max_day_pct == D(40) and p.eval.daily_loss_limit == D(600)
    assert p.purchase.consistency_pct == D(40)
    assert stage_rules(p, "EVAL").consistency_pct == D(40) and stage_rules(p, "EVAL").dll_scale_pct == D(60)
    assert max_base_for_stage(p, "EVAL") == D("1475.00")  # MLL + consistency day stop (38 %)
    none = p.model_copy(update={"eval": p.eval.model_copy(update={"consistency_max_day_pct": None})})
    assert max_base_for_stage(none, "EVAL") == D(2250)  # no consistency rule: MLL + target
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
    # D115/D121: per-plan fallback size = D63 regular table (25K 1 · 50K 2 · 100K 2 · 150K 3)
    assert n.contracts == {25: 1, 50: 2, 100: 2, 150: 3}[int(plan.split("_")[-1][:-1])]
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
                (D(100000), 2),  # D63/D64 research table (kept: bigger sizes raised bust risk, session19 refine)
                (D(150000), 3),
            ]
            assert [(t.account_size, t.contracts) for t in st.size_table_high] == [
                (D(25000), 1),
                (D(50000), 2),
                (D(100000), 3),  # D64 high-risk table
                (D(150000), 4),
            ]
            assert all(t.brake_below is not None for t in st.size_table_high if t.contracts > 1)  # brake on every row
            assert not st.high_risk and st.active_size_table() is st.size_table
            if f.stem.startswith("lucid_pro"):  # D66: Evaluation Mode table (Pro only — Flex evals were not studied)
                hi = {t.account_size: t for t in st.size_table_eval_high}  # D69 high-risk evals
                assert hi[D(25000)].contracts == 3 and hi[D(25000)].taper_contracts == 1
                assert hi[D(25000)].stop_usd == D(150)  # D70: 3 micros × $150 = $450 total
                assert hi[D(25000)].taper_below_remaining == D("0.5") and hi[D(150000)].contracts == 4
                raw = st.model_copy(update={"eval_size_s19": False})  # D133 toggle off = the tables as written
                assert raw.active_eval_table() is st.size_table_eval
                assert raw.model_copy(update={"high_risk": True}).active_eval_table() is st.size_table_eval_high
                assert st.eval_size_s19  # D133 default: session-19 caps 100K ≤ 2, 150K ≤ 3
                for tbl in (st.active_eval_table(), st.model_copy(update={"high_risk": True}).active_eval_table()):
                    cap = {t.account_size: t for t in tbl}
                    assert cap[D(150000)].contracts == 3 and cap[D(100000)].contracts == 2
                    assert cap[D(100000)].grow_per is None and cap[D(100000)].max_contracts is None
                    assert cap[D(100000)].day_lock_pct == D("0.33") and cap[D(25000)] in tbl
                # D132: preset-C lock on in every plan, 80 pt alternative behind the toggle, fade off in EVAL
                assert st.noise_profit_lock() == (D(100), D(10)) and st.noise_cfg.skip_weekdays == [0]
                assert st.model_copy(update={"noise_lock_alt": True}).noise_profit_lock() == (D(80), D(10))
                assert st.pm_fade_cfg.eval_off is True and st.noise_lock_alt is False
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


def test_d115_size_validators():
    """D115: every strategy size must be >= 1 and <= the plan's firm max micros; per-trade cap below the MLL."""
    from pathlib import Path

    from pydantic import ValidationError

    from app.config import AiBiasCfg, NoiseCfg, OrderFlowCfg, PmFadeCfg, load_rules

    for cfg in (NoiseCfg, PmFadeCfg, AiBiasCfg, OrderFlowCfg):
        with pytest.raises(ValidationError):
            cfg(contracts=0)
    f = Path(__file__).resolve().parents[3] / "config" / "rules" / "lucid_pro_25k.yaml"
    rules = load_rules(f).rules
    firm = rules.max_contracts.micros
    st = rules.strategy
    with pytest.raises(ValidationError, match="above the firm max"):
        type(rules).model_validate(
            {
                **rules.model_dump(),
                "strategy": {**st.model_dump(), "noise_cfg": {**st.noise_cfg.model_dump(), "contracts": firm + 1}},
            }
        )
    with pytest.raises(ValidationError, match="max_trade_risk_usd"):
        type(rules).model_validate(
            {**rules.model_dump(), "strategy": {**st.model_dump(), "max_trade_risk_usd": D(10**6)}}
        )


def test_suggested_size_table_d127():
    """D127: Pro/Flex plans ship the session-19 lowest-bust table; the toggle switches NOISE sizing to it."""
    for f in sorted((Path(__file__).resolve().parents[3] / "config" / "rules").glob("lucid_*.yaml")):
        st = load_rules(f).rules.strategy
        if not st.size_table:
            continue
        assert [(int(t.account_size), t.contracts) for t in st.size_table_suggested] == [
            (25000, 1),
            (50000, 1),
            (100000, 2),
            (150000, 3),
        ]
        assert not st.suggested_size and st.active_size_table() is st.size_table
        on = st.model_copy(update={"suggested_size": True})
        assert on.active_size_table() is on.size_table_suggested
        assert on.model_copy(update={"high_risk": True}).active_size_table() is on.size_table_suggested


def test_capped_eval_table_only_ever_lowers_sizes():  # D133 / I1
    from app.config import EvalCapCfg, SizeTierCfg, capped_eval_table

    rows = [
        SizeTierCfg(account_size=D(25000), mll=D(1000), contracts=3, taper_below_remaining=D("0.5"), taper_contracts=1),
        SizeTierCfg(account_size=D(50000), mll=D(2000), contracts=2, grow_per=D(500), max_contracts=4),
        SizeTierCfg(account_size=D(100000), mll=D(3000), contracts=2, brake_below=D("0.3"), brake_contracts=1,
                    grow_per=D(1200), max_contracts=4),
        SizeTierCfg(account_size=D(150000), mll=D(4500), contracts=4, brake_below=D("0.5"), brake_contracts=2),
    ]  # fmt: skip
    caps = [
        EvalCapCfg(account_size=D(25000), max_contracts=2),
        EvalCapCfg(account_size=D(50000), max_contracts=3),
        EvalCapCfg(account_size=D(100000), max_contracts=2),
        EvalCapCfg(account_size=D(150000), max_contracts=3),
    ]
    out = {t.account_size: t for t in capped_eval_table(rows, caps)}
    assert (out[D(25000)].contracts, out[D(25000)].taper_contracts) == (2, 1)  # taper still below the new size
    assert (out[D(50000)].contracts, out[D(50000)].grow_per, out[D(50000)].max_contracts) == (2, D(500), 3)
    assert (out[D(100000)].contracts, out[D(100000)].grow_per, out[D(100000)].max_contracts) == (2, None, None)
    assert (out[D(150000)].contracts, out[D(150000)].brake_contracts) == (3, 2)
    tiny = capped_eval_table([rows[0]], [EvalCapCfg(account_size=D(25000), max_contracts=1)])[0]
    assert (tiny.contracts, tiny.taper_contracts, tiny.taper_below_remaining) == (1, None, None)
    assert capped_eval_table(rows, []) == rows


def test_noise_lock_alt_validation():  # D132
    from pydantic import ValidationError

    from app.config import NoiseCfg, StrategyCfg

    with pytest.raises(ValidationError):
        NoiseCfg(profit_lock_trigger_alt_pts=D(80))  # needs the lock distance
    with pytest.raises(ValidationError):
        NoiseCfg(profit_lock_trigger_pts=D(100), profit_lock_pts=D(10), profit_lock_trigger_alt_pts=D(10))
    assert StrategyCfg(noise_lock_alt=True).noise_profit_lock() is None  # no lock configured → none
    nc = NoiseCfg(profit_lock_trigger_pts=D(100), profit_lock_pts=D(10))
    assert StrategyCfg(noise_cfg=nc, noise_lock_alt=True).noise_profit_lock() == (D(100), D(10))  # no alt → 100


@pytest.mark.parametrize("k", (25, 50, 100, 150))
def test_pro_card_fields(k):
    p = r(f"lucid_pro_{k}k")
    assert p.eval.consistency_max_day_pct == D(40) and p.eval.dll_scale_above_lock_pct == D(60)
    assert p.funded.dll_scale_above_lock_pct == D(60) and p.funded.payout.min_profitable_days == 3
    assert p.internal.consistency_day_stop_buffer_pct == D(2)


def test_flex_has_no_lucid_scale():
    f = r("lucid_flex_50k")
    assert f.eval.dll_scale_above_lock_pct is None and f.funded.dll_scale_above_lock_pct is None
    assert stage_rules(f, "FUNDED").dll_scale_pct is None
    assert stage_rules(f, "EVAL", dll_enabled=False).dll_scale_pct is None
    assert stage_rules(f, "LIVE").dll_scale_pct is None
