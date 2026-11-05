"""§21 property tests: hold for thousands of random cases."""

from decimal import Decimal as D

from hypothesis import given, settings
from hypothesis import strategies as st

from app.config import load_rules
from app.engine.trade_plan import Direction, TradePlan, build_trade_plan
from app.management.drawdown_guard import apply_guard, ratchet, runner_stop, split_legs
from app.risk.checks import AccountView, DayLimits, DayState, TradeLimits, dll_remaining, pretrade
from app.risk.consistency import eval_limits
from app.risk.eval_mode import effective_risk_cfg
from app.risk.hedge_lock import OpenPosition, hedge_conflict
from app.risk.tiers import FloorRules, RiskCfg, RiskCtx
from tests.conftest import RULES_PATH

R = load_rules(RULES_PATH).rules
T = D("0.25")
STD, EVM = RiskCfg.standard(R.internal), RiskCfg.evaluation(R.eval_mode)
FL = FloorRules(
    R.internal.day_lockin_r, R.internal.dd_floor_pct, R.internal.streak_floor_losses, R.internal.streak_release_wins
)
LIM = TradeLimits(T, D("0.50"), D("1.00"), 1, 20, 10, 1, D(40), D(500), D(100))

money = st.integers(min_value=0, max_value=600_000).map(lambda c: D(c) / 100)


@settings(max_examples=400, deadline=None)
@given(
    base=st.integers(300, 6000).map(D),
    score=st.integers(40, 100).map(D),
    stage=st.sampled_from(["EVAL", "FUNDED", "LIVE"]),
    override=st.sampled_from(["inherit", "on", "off"]),
    global_on=st.booleans(),
    pnl=st.integers(-700, 600).map(D),
    stop_pts=st.integers(5, 60),
    first=st.booleans(),
    losses=st.integers(0, 3),
    trades=st.integers(0, 40),
    today_profit=st.integers(0, 600).map(D),
    giveback=st.integers(0, 700).map(D),
)
def test_risk_never_exceeds_ceiling_cap_or_dll(
    base, score, stage, override, global_on, pnl, stop_pts, first, losses, trades, today_profit, giveback
):
    cfg = effective_risk_cfg(stage, override, global_on, STD, EVM)
    if stage != "EVAL":
        assert cfg.kind == "standard"  # eval profile never selected unless stage == EVAL
    equity = D(24000) + base
    acct = AccountView("A", stage, True, True, True, True, False, False, None, equity, D(24000), D(600), base)
    plan = build_trade_plan(Direction.LONG, D(20000), D(20000) - stop_pts + 1, D(20000) + 4 * stop_pts, T, 4, 20)
    if not isinstance(plan, TradePlan):
        return
    ctx = RiskCtx(first, False, losses, D(0), D(0), trades, losses, 0, False)
    r = pretrade(
        acct=acct,
        plan=plan,
        score=score,
        rcfg=cfg,
        ctx=ctx,
        floor=FL,
        day=DayState(losses, losses, 0, pnl, today_profit, today_peak_pnl=pnl + giveback),
        day_limits=DayLimits(3, 2),
        consistency=eval_limits(D(1250), D(40), D(5)),
        lim=LIM,
        hedge_conflict=False,
    )
    if r.ok:
        assert r.risk_usd <= cfg.ceiling * base + D("0.005")
        if cfg.max_risk_usd is not None:
            assert r.risk_usd <= cfg.max_risk_usd
        left = dll_remaining(D(600), pnl, pnl + giveback)
        assert left <= D(600) + min(D(0), pnl)  # never more room than the strictest firm reading
        assert r.risk_usd + LIM.dll_safety_margin <= left
        assert r.worst_case_usd + LIM.dll_safety_margin <= left
        assert r.worst_case_usd + LIM.dll_safety_margin <= equity - D(24000) - LIM.kill_switch_distance
        assert r.contracts >= 1


@settings(max_examples=300, deadline=None)
@given(
    ops=st.lists(
        st.tuples(
            st.sampled_from("ABCDE"),
            st.sampled_from(["MNQ", "MES", "MYM", "MGC"]),
            st.sampled_from(["LONG", "SHORT"]),
            st.booleans(),
        ),
        max_size=60,
    )
)
def test_no_opposite_positions_in_a_super_group_ever_coexist(ops):
    open_: list[OpenPosition] = []
    for acct, sym, d, close in ops:
        if close:
            open_ = [p for p in open_ if p.account != acct]
            continue
        if any(p.account == acct for p in open_):
            continue  # 1 open position per account
        if hedge_conflict(R, sym, d, open_) is None:
            open_.append(OpenPosition(acct, sym, "TIGHT", d))
        for sg in ("EQUITY_INDEX", "METALS"):
            dirs = {p.direction for p in open_ if R.super_group_of(p.symbol) == sg}
            assert len(dirs) <= 1


@settings(max_examples=300, deadline=None)
@given(n=st.integers(2, 10), path=st.lists(st.integers(-80, 80), min_size=1, max_size=60), long=st.booleans())
def test_guard_on_post_partial_trailing_cost_at_most_1r(n, path, long):
    """After the partial fills, giving back from the peak never exceeds 1R of the full position."""
    d = Direction.LONG if long else Direction.SHORT
    s = d.sign
    p = build_trade_plan(d, D(20000), D(20000) - s * 19, D(20000) + s * 80, T, 4, 20)
    assert isinstance(p, TradePlan)
    g = apply_guard(p, T, 2)
    a, b = split_legs(n)
    one_r = p.risk_pts * n  # 1R of the full position, in points × contracts
    realised = (g.partial_price - g.entry) * s * a  # leg A done at the partial
    price, best, stop = g.partial_price, g.partial_price, g.breakeven_price
    peak = realised + (price - g.entry) * s * b
    final = None
    for step in path:
        price = price + s * D(step) * T
        if (price - stop) * s <= 0:  # runner stopped out at its stop
            final = realised + (stop - g.entry) * s * b
            break
        if (price - g.take_profit) * s >= 0:
            final = realised + (g.take_profit - g.entry) * s * b
            break
        best = price if (price - best) * s > 0 else best
        stop = ratchet(stop, runner_stop(g, best, D(2), T), d)
        peak = max(peak, realised + (price - g.entry) * s * b)
    if final is None:
        final = realised + (stop - g.entry) * s * b  # worst case: the next tick hits the stop
    peak = max(peak, final)
    assert peak - final <= one_r
