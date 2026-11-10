"""§21 Phase-4 cases (MNQ tick 0.25 = $0.50, fee_rt $1.50 placeholder, buffer 4, min stop 20) + D7/D8/D16."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.config import load_rules
from app.engine.trade_plan import Direction, TradePlan, build_one_to_one_plan, build_trade_plan, fee_cover_ticks
from app.management.drawdown_guard import (
    GuardCfgView,
    apply_guard,
    guard_active,
    min_contracts,
    one_to_one_on_partial,
    ratchet,
    runner_stop,
    split_legs,
)
from app.management.exits import early_exit_allowed, exit_allowed_now, rapid_profit_share
from app.phases.mll_tracker import breached, mll_distance, update_mll
from app.phases.phase_engine import eval_progress, funded_live_move_triggered, inactivity_alert, new_mll, stage_rules
from app.phases.transitions import plan_transition
from app.risk.checks import AccountView, DayLimits, DayState, TradeLimits, day_stop_reason, dll_remaining, pretrade
from app.risk.consistency import ConsistencyLimits, eval_limits, fit_contracts, funded_limits, largest_day_ok
from app.risk.eval_mode import effective_risk_cfg, eval_mode_effective
from app.risk.hedge_lock import OpenPosition, account_has_position, hedge_conflict
from app.risk.risk_base import money, risk_base
from app.risk.sizing import profile_for_base, size_contracts
from app.risk.tiers import FloorRules, RiskCfg, RiskCtx, ceiling_allowed, force_floor, risk_usd, select_risk_pct
from app.risk.validation import dll_two_loss_test, max_base_for_stage, validate
from tests.conftest import RULES_PATH

R = load_rules(RULES_PATH).rules
T, TV, FEE = D("0.25"), D("0.50"), D("1.50")
STD, EVM = RiskCfg.standard(R.internal), RiskCfg.evaluation(R.eval_mode)
FL = FloorRules(
    R.internal.day_lockin_r, R.internal.dd_floor_pct, R.internal.streak_floor_losses, R.internal.streak_release_wins
)
FRESH = RiskCtx(
    first_trade_today=True,
    last_closed_was_loss=False,
    losses_today=0,
    today_net_r=D(0),
    dd_from_peak_base_pct=D(0),
    trades_in_stage=50,
    consecutive_losses=0,
    wins_since_streak_floor=0,
    in_streak_floor=False,
)


def ctx(**k):
    from dataclasses import replace

    return replace(FRESH, **k)


# ---------- plan + guard (§21) ----------
def test_guard_on_partial_and_breakeven():
    p = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
    g = apply_guard(p, T, fee_cover_ticks(FEE, TV))
    assert (g.partial_price, g.breakeven_price) == (D(20030), D("20000.75"))
    p2 = apply_guard(build_trade_plan(Direction.LONG, D(20000), D(19981), D(20050), T, 4, 20), T, 3)
    assert (p2.take_profit, p2.partial_price) == (D(20050), D(20025))


def test_runner_trail_2r():
    g = apply_guard(build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20), T, 3)
    assert runner_stop(g, D(20055), D(2), T) == D(20015)
    assert runner_stop(g, D(20035), D(2), T) == D("20000.75")  # stays at BE
    s = apply_guard(build_trade_plan(Direction.SHORT, D(20000), D(20019), D(19930), T, 4, 20), T, 3)
    assert runner_stop(s, D(19945), D(2), T) == D(19985) and runner_stop(s, D(19970), D(2), T) == D("19999.25")
    assert ratchet(D(20015), D(20010), Direction.LONG) == D(20015)  # never loosens


def test_guard_decision():
    auto = GuardCfgView("auto")
    assert guard_active("eod", False, auto) is False  # eval EOD
    assert guard_active("intraday", False, auto) is True  # funded intraday unlocked
    assert guard_active("intraday", True, auto) is False  # funded locked
    assert guard_active("eod", True, auto) is False  # live EOD
    assert guard_active("eod", False, GuardCfgView("on")) and not guard_active("intraday", False, GuardCfgView("off"))
    assert split_legs(5) == (3, 2) and split_legs(2) == (1, 1) and min_contracts(True, 2, 1) == 2


# ---------- sizing + tiers (§21) ----------
def test_sizing_spec():
    assert size_contracts(D(70), D(64), TV, FEE, 1, 20, 10, 2) == 2  # 16-pt stop → 34/contract → 2 (guard ON ok)
    assert size_contracts(D(70), D(80), TV, FEE, 1, 20, 10, 2) == 0  # 20-pt → 42 → 1 → guard ON skip
    assert size_contracts(D(70), D(80), TV, FEE, 1, 20, 10, 1) == 1  # guard OFF → 1
    assert size_contracts(D(10_000), D(20), TV, FEE, 1, 20, 10, 1) == 10  # internal max wins


def test_tiers_spec():
    assert [risk_usd(STD.tier(D(s)), D(1000), STD) for s in (60, 75, 90)] == [D(70), D(90), D(110)]
    assert [risk_usd(STD.tier(D(s)), D(3000), STD) for s in (60, 75, 90)] == [D(210), D(270), D(330)]
    assert STD.tier(D("59.99")) is None
    assert [risk_usd(EVM.tier(D(s)), D(1000), EVM) for s in (60, 75, 90)] == [D(100), D(120), D(140)]
    assert risk_usd(EVM.tier(D(90)), D(1400), EVM) == D(140)  # capped at $140


def test_ceiling_and_floor_rules():
    assert select_risk_pct(D(95), FRESH, STD, FL) == D("0.11")
    assert select_risk_pct(D(95), ctx(first_trade_today=False), STD, FL) == D("0.09")  # ceiling → middle
    assert select_risk_pct(D(95), ctx(last_closed_was_loss=True), STD, FL) == D("0.09")
    assert select_risk_pct(D(80), ctx(losses_today=1), STD, FL) == D("0.07")
    assert select_risk_pct(D(80), ctx(dd_from_peak_base_pct=D(20)), STD, FL) == D("0.07")
    assert select_risk_pct(D(95), ctx(trades_in_stage=19), STD, FL) == D("0.07")  # warmup 20
    assert select_risk_pct(D(95), ctx(trades_in_stage=10), EVM, FL) == D("0.14")  # eval warmup 10
    assert select_risk_pct(D(95), ctx(consecutive_losses=4), STD, FL) == D("0.07")
    assert select_risk_pct(D(95), ctx(in_streak_floor=True, wins_since_streak_floor=1), STD, FL) == D("0.07")
    assert select_risk_pct(D(95), ctx(in_streak_floor=True, wins_since_streak_floor=2), STD, FL) == D("0.11")
    assert select_risk_pct(D(95), ctx(low_expectancy_cap=True), STD, FL) == D("0.07")
    assert select_risk_pct(D(50), FRESH, STD, FL) is None
    assert not ceiling_allowed(ctx(consecutive_losses=4), STD, FL) and not force_floor(FRESH, STD, FL)


def test_day_lockin():
    assert select_risk_pct(D(80), ctx(today_net_r=D("2.0")), STD, FL) == D("0.07")
    assert select_risk_pct(D(80), ctx(today_net_r=D("1.9")), STD, FL) == D("0.09")


# ---------- day + streak math (§21) ----------
def test_standard_day_spec():
    base, dll = D(3000), D(600)
    l1 = risk_usd(STD.tier(D(95)), base, STD)
    assert l1 == D(330)
    left = dll_remaining(dll, -l1)
    l2 = risk_usd(STD.floor, base - l1, STD)
    assert (base - l1, left, l2) == (D(2670), D(270), D("186.90")) and l2 + 40 <= left
    assert day_stop_reason(DayState(2, 2, 0, -(l1 + l2), D(0)), DayLimits(3, 2), None) == "CONSECUTIVE_LOSSES"
    assert l1 + l2 == D("516.90") < dll


def test_eval_mode_day_spec():
    l1 = risk_usd(EVM.tier(D(95)), D(1000), EVM)
    l2 = risk_usd(EVM.floor, D(1000) - l1, EVM)
    assert (l1, l2, dll_remaining(D(600), -l1), l1 + l2) == (D(140), D(86), D(460), D(226))


def _streak(base, first, then, n):
    base -= money(first * base)
    for _ in range(n):
        base -= money(then * base)
    return base


def test_streak_specs():
    assert (
        abs(_streak(D(1000), D("0.11"), D("0.07"), 7) - D(535)) < 1 and _streak(D(1000), D("0.11"), D("0.07"), 7) >= 500
    )
    assert _streak(D(1000), D("0.14"), D("0.10"), 5) == D("507.82")
    assert _streak(D(1000), D("0.14"), D("0.10"), 6) == D("457.04")  # → below $500 pause floor


# ---------- MLL (§21) ----------
def test_mll_eval_eod():
    sr = stage_rules(R, "EVAL")
    st = new_mll(sr, D(25000))
    assert st.mll == D(24000)
    update_mll(st, D(25400))  # intraday: unchanged on EOD accounts
    assert st.mll == D(24000)
    update_mll(st, D(25400), eod=True)
    assert st.mll == D(24400)
    update_mll(st, D(26100), eod=True)
    assert (st.mll, st.locked) == (D(25100), True)
    update_mll(st, D(30000), eod=True)
    assert st.mll == D(25100)  # locked stays
    st2 = new_mll(sr, D(25000))
    assert breached(st2, D(24000)) and not breached(st2, D("24000.01"))  # intraday touch = breach
    assert mll_distance(st2, D(24100)) == D(100)


def test_mll_funded_intraday():
    st = new_mll(stage_rules(R, "FUNDED", drawdown_override="intraday"), D(25000))
    update_mll(st, D(25600))
    assert st.mll == D(24600) and risk_base(D(25600), st.mll) == D(1000)
    update_mll(st, D(26100))
    assert (st.mll, st.locked) == (D(25100), True)
    assert risk_base(D(27100), st.mll) == D(2000)
    assert stage_rules(R, "FUNDED").drawdown_type == "intraday"  # D20: Lucid says funded is always intraday
    assert stage_rules(R, "LIVE").dll is None and stage_rules(R, "EVAL", dll_enabled=False).dll is None
    with pytest.raises(ValueError):
        stage_rules(R, "NOPE")


# ---------- Evaluation Mode scope (§21, §1.11) ----------
@pytest.mark.parametrize(
    "stage,override,global_on,expect",
    [
        ("EVAL", "inherit", True, True),
        ("EVAL", "inherit", False, False),
        ("EVAL", "on", False, True),
        ("EVAL", "off", True, False),
        ("FUNDED", "on", True, False),
        ("LIVE", "on", True, False),
    ],
)
def test_eval_mode_scope(stage, override, global_on, expect):
    assert eval_mode_effective(stage, override, global_on) is expect
    assert effective_risk_cfg(stage, override, global_on, STD, EVM).kind == ("evaluation" if expect else "standard")


def test_stage_change_forces_eval_mode_off():
    t = plan_transition("EVAL", "FUNDED", "on", False, False)
    assert t.allowed and "eval_mode_off" in t.actions and "eval_mode_override_reset" in t.actions
    assert "block_household_sim_accounts" in plan_transition("FUNDED", "LIVE", "inherit", False, False).actions
    assert not plan_transition("EVAL", "FUNDED", "inherit", False, True).allowed  # closed by firm
    assert not plan_transition(None, "MOON", "inherit", False, False).allowed
    assert "eval_mode_off" not in plan_transition(None, "EVAL", "inherit", False, False).actions


# ---------- consistency (§21 + D16) ----------
def test_consistency_eval_spec():
    lim = eval_limits(D(1250), D(40), D(5))
    assert (lim.cap, lim.day_stop) == (D(500), D("437.50"))
    reward = D(420)  # one 3R win at $140 risk
    assert fit_contracts(1, D(0), reward, lim, 1) == 1  # $420 < $437.50 → trading continues
    assert fit_contracts(1, D(100), reward, lim, 1) == 0  # 100 + 420 = 520 > 500 → CONSISTENCY_CAP
    assert fit_contracts(3, D(100), D(140), lim, 1) == 2  # reduce contracts to fit
    assert fit_contracts(3, D(600), D(140), lim, 1) == 0 and fit_contracts(2, D(0), D(0), lim, 1) == 2
    assert day_stop_reason(DayState(1, 0, 1, D("437.50"), D("437.50")), DayLimits(3, 2), lim) == "CONSISTENCY_DAY_STOP"
    p = eval_progress([D(400), D(450), D(450)], D(1250), D(40), 3)  # largest 450/1300 = 34.6%
    assert p.passed and p.profitable_days == 3
    assert not eval_progress([D(300), D(400), D(600)], D(1250), D(40), 3).largest_day_ok  # 600/1300 = 46%
    assert not eval_progress([D(700), D(600)], D(1250), D(40), 3).passed  # 2 days, largest 53.8%
    q = eval_progress([D(700), D(300), D(300)], D(1250), D(40), 3)
    assert not q.largest_day_ok and q.extra_profit_needed == D(450)  # needs total 1,750
    assert not largest_day_ok([], D(40)) and not largest_day_ok([D(-5)], D(40))


def test_consistency_funded_d16():
    assert funded_limits(D(0), D(1250), D(40), D(5)) == ConsistencyLimits(D(500), D("437.50"))
    assert funded_limits(D(3000), D(1250), D(40), D(5)) == ConsistencyLimits(D(1200), D(1050))


# ---------- 1:1 mode day rules (D7) ----------
def test_one_to_one_day_rules():
    lim = DayLimits(3, 3, one_to_one=True, extended_max_trades=5, extend_after_win_streak=3)
    assert day_stop_reason(DayState(2, 2, 0, D(-200), D(0)), lim, None) is None  # 3 losses allowed
    assert day_stop_reason(DayState(3, 3, 0, D(-300), D(0)), lim, None) == "CONSECUTIVE_LOSSES"
    assert day_stop_reason(DayState(3, 0, 3, D(300), D(300)), lim, None) is None  # W W W → 4th ok
    assert day_stop_reason(DayState(4, 0, 4, D(400), D(400)), lim, None) is None  # W W W W → 5th ok
    assert day_stop_reason(DayState(4, 1, 0, D(200), D(200)), lim, None) == "MAX_TRADES"  # 4th lost → stop
    assert day_stop_reason(DayState(5, 0, 5, D(500), D(400)), lim, None) == "MAX_TRADES"  # never > 5
    assert day_stop_reason(DayState(3, 0, 3, D(300), D(300)), DayLimits(3, 2), None) == "MAX_TRADES"  # normal mode


def test_one_to_one_management():
    p = build_one_to_one_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20, D("0.75"), D("0.30"), 2)
    a = one_to_one_on_partial(p, 3)
    assert (a.close_qty, a.new_stop) == (2, D("20000.50"))
    b = one_to_one_on_partial(p, 1)
    assert (b.close_qty, b.new_stop) == (0, D(20006))


# ---------- hedge lock (§21) ----------
def test_hedge_lock_spec():
    opn = [OpenPosition("A", "MNQ", "TIGHT", "LONG")]
    assert hedge_conflict(R, "MNQ", "SHORT", opn) is not None  # STD SHORT on another account
    assert hedge_conflict(R, "MES", "SHORT", opn) is not None  # MES short → same EQUITY_INDEX super-group
    assert hedge_conflict(R, "MYM", "SHORT", opn) is not None
    assert hedge_conflict(R, "MNQ", "LONG", opn) is None
    assert hedge_conflict(R, "MGC", "SHORT", opn) is None  # METALS is a different super-group
    assert account_has_position("A", opn) and not account_has_position("B", opn)


# ---------- exits (§8, D8) ----------
def test_exits():
    p = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
    assert early_exit_allowed(p, D(20019), False, D(1)) and not early_exit_allowed(p, D(20020), False, D(1))
    assert not early_exit_allowed(p, D(20005), True, D(1))
    t0 = datetime(2026, 11, 5, 15, tzinfo=UTC)
    assert not exit_allowed_now("EARLY_EXIT", t0, t0 + timedelta(seconds=5), 6)
    assert exit_allowed_now("EARLY_EXIT", t0, t0 + timedelta(seconds=6), 6)
    assert exit_allowed_now("STOP", t0, t0 + timedelta(seconds=1), 6)  # protective never waits
    assert rapid_profit_share([(D(100), 3.0), (D(300), 60.0), (D(-50), 2.0)], 5) == D(25)
    assert rapid_profit_share([(D(-1), 1.0)], 5) == 0


# ---------- phase engine misc ----------
def test_phase_misc():
    assert funded_live_move_triggered(D(6000), R) and not funded_live_move_triggered(D(5999), R)
    now = datetime(2026, 11, 5, tzinfo=UTC)
    assert inactivity_alert(now - timedelta(days=21), now, 21) and not inactivity_alert(None, now, 21)
    assert profile_for_base(D(1499), D(1500)) == "TIGHT" and profile_for_base(D(1500), D(1500)) == "STD"


# ---------- validation + DLL test (§11) ----------
def test_validation_defaults_and_dll_spec():
    v = validate(R)
    assert v.ok, v.errors
    assert v.dll_tests["funded"]["total"] == "596.90" and v.dll_tests["eval_standard"]["total"] == "327.69"
    assert v.dll_tests["eval_mode"]["total"] == "349.75"
    assert v.needs_second_confirmation  # Evaluation Mode tiers > 11%
    assert max_base_for_stage(R, "EVAL") == D("1437.50") and max_base_for_stage(R, "FUNDED") == D(3000)
    assert dll_two_loss_test(D(3000), D("0.11"), D("0.07"), None, D(40)) == (D(330), D("186.90"), D("596.90"))


@pytest.mark.parametrize(
    "path,value,msg",
    [
        (("internal", "risk_pct_ceiling"), D("0.13"), "DLL test funded"),
        (("internal", "day_lockin_r"), D("0.5"), "day lock-in"),
        (("internal", "internal_max_micros"), 25, "firm maximum"),
        (("internal", "windows"), [("06:45", "17:30")], "window"),
        (("internal", "auto_flatten"), "16:50", "auto-flatten"),
        (("internal", "cushion_target_balance"), D(26000), "cushion"),
        (("internal", "kill_switch_mll_distance"), D(0), "kill switch"),
        (("internal", "max_consecutive_losses_per_day"), 0, "consecutive"),
        (("internal", "consistency_day_stop_buffer_pct"), D(0), "consistency day stop"),
    ],
)
def test_validation_rejects(path, value, msg):
    sect = getattr(R, path[0]).model_copy(update={path[1]: value})
    v = validate(R.model_copy(update={path[0]: sect}))
    assert not v.ok and any(msg in e for e in v.errors), v.errors


def test_validation_warns_over_11_and_bounds():
    sect = R.internal.model_copy(
        update={"risk_pct_ceiling": D("0.12"), "risk_pct_by_score": {60: D("0.07"), 75: D("0.09"), 90: D("0.20")}}
    )
    v = validate(R.model_copy(update={"internal": sect}))
    assert any("> 11%" in w for w in v.warnings) and any("absolute" in e for e in v.errors)
    bad = R.internal.model_copy(update={"risk_pct_floor": D("0.10"), "risk_pct_middle": D("0.08")})
    assert any("floor ≤ middle" in e for e in validate(R.model_copy(update={"internal": bad})).errors)
    gm = R.drawdown_guard.model_copy(update={"runner_trail_r": D("2.5")})
    assert any("runner" in e for e in validate(R.model_copy(update={"drawdown_guard": gm})).errors)
    lo = R.internal.model_copy(update={"risk_pct_floor": D("0.005")})
    assert any("outside" in e for e in validate(R.model_copy(update={"internal": lo})).errors)


# ---------- pre-trade (§9) ----------
ACCT = AccountView("A", "EVAL", True, True, True, True, False, False, None, D(25000), D(24000), D(600), D(1000))
LIM = TradeLimits(T, TV, FEE, 1, 20, 10, 1, D(40), D(500), D(100))
PLAN = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)  # 20-pt stop, 3R


def run(**over):
    from dataclasses import replace

    args = dict(
        acct=ACCT,
        plan=PLAN,
        score=D(80),
        rcfg=STD,
        ctx=FRESH,
        floor=FL,
        day=DayState(0, 0, 0, D(0), D(0)),
        day_limits=DayLimits(3, 2),
        consistency=eval_limits(D(1250), D(40), D(5)),
        lim=LIM,
        hedge_conflict=False,
    )
    acct_over = {k[5:]: v for k, v in over.items() if k.startswith("acct_")}
    args.update({k: v for k, v in over.items() if not k.startswith("acct_")})
    if acct_over:
        args["acct"] = replace(ACCT, **acct_over)
    return pretrade(**args)


def test_pretrade_ok_logs_values():
    r = run()
    assert r.ok and r.contracts == 2 and r.risk_usd == D(90) and r.worst_case_usd == D(84)
    names = [c["check"] for c in r.checks]
    assert names[:3] == ["account_ready", "attestation", "not_paused"] and "worst_case" in names


@pytest.mark.parametrize(
    "over,reason",
    [
        ({"acct_armed": False}, "ACCOUNT_NOT_READY"),
        ({"acct_attested": False}, "ATTESTATION_MISSING"),
        ({"acct_paused_reason": "KILL"}, "ACCOUNT_PAUSED"),
        ({"acct_payout_pending": True}, "PAYOUT_PENDING"),
        ({"acct_has_open_position": True}, "POSITION_OPEN"),
        ({"hedge_conflict": True}, "HEDGE_LOCK"),
        ({"acct_base": D(499)}, "RISK_BASE_BELOW_PAUSE"),
        ({"acct_equity": D(24100)}, "NEAR_MLL"),
        ({"day": DayState(2, 2, 0, D(-150), D(0))}, "CONSECUTIVE_LOSSES"),
        ({"score": D(55)}, "SCORE_BELOW_MIN"),
        ({"day": DayState(1, 1, 0, D(-530), D(0))}, "DLL_LIMIT"),
        ({"plan": build_trade_plan(Direction.LONG, D(20000), D(19900), D(20300), T, 4, 20)}, "STOP_TOO_WIDE"),
        ({"day": DayState(1, 0, 1, D(400), D(400))}, "CONSISTENCY_CAP"),  # room $100 < $118.50 per contract
    ],
)
def test_pretrade_failures(over, reason):
    r = run(**over)
    assert not r.ok and r.reason == reason, (r.reason, r.checks[-1])


def test_pretrade_worst_case_vs_mll_room():
    r = run(acct_equity=D(24200), acct_base=D(1000), consistency=None)  # room 200 − kill 100 = 100 < 84 + 40
    assert not r.ok and r.reason == "WORST_CASE_EXCEEDS_LIMITS"


def test_pretrade_consistency_reduces_contracts():
    r = run(day=DayState(1, 0, 1, D(300), D(300)))  # room $200 → 1 contract of $118.50
    assert r.ok and r.contracts == 1


def test_pretrade_without_dll_and_consistency():
    r = run(acct_dll=None, consistency=None)
    assert r.ok and r.contracts == 2


def test_dll_room_safe_under_both_firm_readings_d18():
    assert dll_remaining(D(600), D(0)) == D(600)
    assert dll_remaining(D(600), D(-330)) == D(270)  # losses use room up
    assert dll_remaining(D(600), D(200), D(200)) == D(600)  # profits never ADD room
    assert dll_remaining(D(600), D(100), D(500)) == D(200)  # gave back $400 from today's high → $200 left
    assert dll_remaining(D(600), D(-100), D(300)) == D(200)  # high +300, now −100 → $400 used
    assert dll_remaining(D(600), D(50)) == D(600)  # peak unknown → at least the current P&L


def test_pretrade_blocks_after_giving_back_profit():
    # high +$600, now +$100 → $100 room; $90 risk + $40 margin = $130 > $100 → blocked
    r = run(day=DayState(1, 0, 1, D(100), D(100), today_peak_pnl=D(600)), consistency=None)
    assert not r.ok and r.reason == "DLL_LIMIT"
    # high +$300, now +$100 → $400 room → allowed
    assert run(day=DayState(1, 0, 1, D(100), D(100), today_peak_pnl=D(300)), consistency=None).ok


def test_low_risk_min_qty_floor_d36():
    from dataclasses import replace

    wide = build_trade_plan(Direction.LONG, D(20000), D(19900), D(20300), T, 4, 20)
    base = run(plan=wide)
    assert not base.ok and base.reason == "STOP_TOO_WIDE"
    need = (wide.risk_pts / T) * TV + FEE + 1 * TV  # one micro, incl. fees + 1 tick slippage
    mult = (need / base.risk_usd).quantize(D("0.01")) + D("0.01")
    ok = run(plan=wide, lim=replace(LIM, min_qty_cap_mult=mult), consistency=None)
    assert ok.ok and ok.contracts == 1 and ok.risk_usd == need
    assert any(c["check"] == "low_risk_min_qty" for c in ok.checks)
    # never above the cap (normal-mode risk)
    small = run(plan=wide, lim=replace(LIM, min_qty_cap_mult=D(1)))
    assert not small.ok and small.reason == "STOP_TOO_WIDE"
    # DLL room still enforced
    tight = run(plan=wide, lim=replace(LIM, min_qty_cap_mult=mult), day=DayState(0, 0, 0, D(-500), D(0)))
    assert not tight.ok
    # firm/internal max below min_qty
    capped = run(plan=wide, lim=replace(LIM, min_qty_cap_mult=mult, internal_max=0))
    assert not capped.ok and capped.reason == "STOP_TOO_WIDE"
    # no DLL on the account (Flex funded): only the cap applies
    nodll = run(plan=wide, lim=replace(LIM, min_qty_cap_mult=mult), acct_dll=None, consistency=None)
    assert nodll.ok and nodll.contracts == 1


# ---------- D55 fixed-size strategies (NOISE / OPEN_DRIVE, 1 micro) ----------
NOISE_PLAN = TradePlan(Direction.LONG, D(20000), D(19800), D(22000), D(200), D(10), mode="NOISE")  # 1% stop


def _fixed(n=1, **lim_over):
    from dataclasses import replace

    return replace(LIM, fixed_contracts=n, **lim_over)


def test_fixed_size_ignores_score_and_dollar_cap_but_keeps_worst_case():
    # 1 micro, 800 ticks × $0.50 + fee + 1 tick slip = $402 worst case; score/tier and the $ cap do not apply
    r = run(plan=NOISE_PLAN, score=D(0), lim=_fixed(), consistency=None, acct_dll=None)
    assert r.ok and r.contracts == 1 and r.risk_usd == r.worst_case_usd == D("402.00") and r.risk_pct is None
    assert any(c["check"] == "fixed_size" for c in r.checks)
    assert run(plan=PLAN, lim=_fixed(5), consistency=None, acct_dll=None).contracts == 5  # 20-pt stop
    assert run(plan=PLAN, lim=_fixed(50), consistency=None, acct_dll=None).contracts == 10  # internal max


def test_fixed_size_blocked_by_dll_and_mll_room():
    r = run(plan=NOISE_PLAN, lim=_fixed(), consistency=None)  # DLL $600: 402 + 40 ≤ 600 → ok
    assert r.ok
    r = run(plan=NOISE_PLAN, lim=_fixed(), consistency=None, day=DayState(1, 1, 0, D(-200), D(0)))  # $400 left
    assert not r.ok and r.reason == "WORST_CASE_EXCEEDS_LIMITS"
    r = run(plan=NOISE_PLAN, lim=_fixed(), consistency=None, acct_dll=None, acct_equity=D(24500))  # 500−100 room
    assert not r.ok and r.reason == "WORST_CASE_EXCEEDS_LIMITS"
    r = run(plan=NOISE_PLAN, lim=_fixed(0), consistency=None, acct_dll=None)
    assert not r.ok and r.reason == "STOP_TOO_WIDE"
    r = run(plan=NOISE_PLAN, lim=_fixed(), acct_dll=None, day=DayState(1, 0, 1, D(400), D(400)))  # consistency
    assert not r.ok and r.reason == "CONSISTENCY_CAP"


def test_fixed_size_scales_stop_down_with_drawdown_instead_of_pausing():  # D57
    sh = _fixed(shrink_fraction=D("0.6"))
    # base $460 (< $500 pause floor): old rule → RISK_BASE_BELOW_PAUSE; D57 → tighter emergency stop, trade goes on
    low = dict(acct_equity=D(24460), acct_base=D(460), acct_dll=None)
    assert run(plan=NOISE_PLAN, lim=_fixed(), consistency=None, **low).reason == "RISK_BASE_BELOW_PAUSE"
    r = run(plan=NOISE_PLAN, lim=sh, consistency=None, **low)
    assert r.ok and r.contracts == 1 and r.new_stop is not None
    assert (NOISE_PLAN.entry - r.new_stop) * NOISE_PLAN.direction.sign < NOISE_PLAN.risk_pts
    assert r.worst_case_usd <= D("360") * D("0.6")  # ≤ 60% of the room (equity − MLL − kill distance)
    assert any(c["check"] == "drawdown_scale" and c["ok"] is True for c in r.checks)
    # fresh account: the plan's own stop fits 60% of the room → untouched
    ok = run(plan=NOISE_PLAN, lim=sh, consistency=None, acct_dll=None)
    assert ok.ok and ok.new_stop is None
    # too deep: the scaled stop would be < min % of price → skip with its own reason
    deep = run(plan=NOISE_PLAN, lim=_fixed(shrink_fraction=D("0.6"), shrink_min_pct=D("0.05")), consistency=None, **low)
    assert not deep.ok and deep.reason == "DRAWDOWN_TOO_DEEP"


def test_pretrade_fast_eval_early_tier_raises_pct_and_eval_only():
    """D87: early tier raises the risk % only for EVAL inside the window; DLL checks still run."""
    from app.config import FastEvalCfg
    from app.risk.fast_eval import FastCtx

    fc = FastEvalCfg.model_validate({"early": {"enabled": True, "first_trades": 10, "risk_pct": "0.11"}})
    fx = FastCtx(D(1000), D(1000), False, 0, 2)
    plain = run()
    r = run(fast=(fc, fx))
    assert r.ok and r.risk_pct == D("0.11") and r.risk_usd == D(110)
    assert next(c for c in r.checks if c["check"] == "fast_eval_early_tier")["after"] == "0.11"
    assert plain.risk_usd == D(90)  # unchanged without it
    funded = run(fast=(fc, fx), acct_stage="FUNDED")
    assert funded.risk_usd == D(90) and not any(c["check"] == "fast_eval_early_tier" for c in funded.checks)
    dll = run(fast=(fc, fx), day=DayState(1, 1, 0, D(-500), D(0)))  # DLL room still binds
    assert not dll.ok and dll.reason == "DLL_LIMIT"
