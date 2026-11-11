"""D99 rule-compliance matrix: every strategy button x every plan file x stage (EVAL, FUNDED).

Every limit is read from the plan's own yaml (config/rules/lucid_*.yaml) or its strategy config; no rule number is
written in this file. The trades go through the REAL controller path (`Controller.execute` -> pretrade -> order
manager -> sim broker), the same code live and paper use. A violation is collected as a message so ONE run lists
every finding (the test then fails with the whole list).

Asserted per cell:
- contracts never exceed the firm plan cap, the internal cap or the strategy's own cap (Order Flow: 1 micro);
- worst-case stop loss of the trade (qty x (stop ticks x tick value + fee + slippage)) + the DLL safety margin fits
  the DLL room and the MLL room (distance to the MLL minus the kill-switch distance), also with an absurdly wide stop;
- max open positions: 1 per account (AI Duo only up to its own config on its big accounts, paper only);
- household hedge lock: EQUITY_INDEX (also across instruments) and METALS;
- strategy flat time is not after the plan's auto flatten / hard flat / session flat; news margins are not smaller
  than the firm's; consistency cap/day-stop present exactly where the plan states a consistency rule;
- unverified strategies (Open-drive, AI Duo, split's AI side, Order Flow MNQ + MGC) are PAPER-only: a non-paper
  account is refused (PAPER_ONLY_STRATEGY) in EVAL and FUNDED.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal as D
from functools import cache
from typing import Any

import pytest

from app.clock import FixedClock, parse_hhmm
from app.config import RulesConfig, load_rules
from app.engine.noise import stop_pts_for_usd
from app.engine.trade_plan import Direction
from app.models import Account
from app.phases.phase_engine import firm_max_micros, stage_rules
from app.risk.split_risk import split_contracts
from app.settings import REPO_ROOT
from app.signals import strategy_service as SS

PLAN_FILES = sorted((REPO_ROOT / "config" / "rules").glob("lucid_*.yaml"))
PLAN_IDS = [p.stem for p in PLAN_FILES]
STAGES = ("EVAL", "FUNDED")
AT = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)  # Tuesday 11:00 ET
PRICE = {"MNQ": D(20000), "MYM": D(40000), "MGC": D(2650)}  # test inputs only (not rules)


@cache
def rules_of(stem: str) -> RulesConfig:
    return load_rules(REPO_ROOT / "config" / "rules" / f"{stem}.yaml").rules


@dataclass(frozen=True)
class Spec:
    name: str
    mode: str  # TradePlan mode the strategy writes
    symbol: str
    flags: dict[str, Any]  # StrategyCfg switches turned on for this cell
    paper_only: bool


SPECS = [
    Spec("NOISE", "NOISE", "MNQ", {"noise": True}, False),
    Spec("LUNQFX", "STANDARD", "MNQ", {"lunqfx": True}, False),
    Spec("OPEN_DRIVE", "OPEN_DRIVE", "MNQ", {"open_drive": True}, True),
    Spec("AI_DUO_MNQ", "AI_DUO", "MNQ", {"ai_duo": True}, True),
    Spec("AI_DUO_MGC", "AI_DUO", "MGC", {"ai_duo": True}, True),
    Spec("SPLIT_NOISE", "NOISE", "MNQ", {"noise": True, "ai_duo": True, "noise_ai_split": True}, False),
    Spec("SPLIT_AI_DUO", "AI_DUO", "MNQ", {"noise": True, "ai_duo": True, "noise_ai_split": True}, True),
    Spec("ORDER_FLOW_MNQ", "ORDER_FLOW", "MNQ", {"order_flow": True}, True),
    Spec("ORDER_FLOW_MGC", "ORDER_FLOW", "MGC", {"order_flow": True}, True),
]


# ------------------------------------------------------------------------------------------------ config helpers
def dd_of(r: RulesConfig, stage: str) -> str:
    return r.eval.drawdown_type if stage == "EVAL" else r.funded.drawdown_type


def strategy_cap(r: RulesConfig, spec: Spec) -> int:
    """The strategy's OWN contract cap, read from its config (before the firm/internal caps)."""
    st, size = r.strategy, r.account_size
    if spec.mode == "NOISE":
        tiers = [
            t
            for table in (st.size_table, st.size_table_high, st.size_table_eval, st.size_table_eval_high)
            for t in table
            if t.account_size == size
        ]
        cap = max([max(t.contracts, t.max_contracts or 0) for t in tiers], default=st.noise_cfg.contracts)
    elif spec.mode == "OPEN_DRIVE":
        cap = st.open_drive_cfg.contracts
    elif spec.mode == "AI_DUO":
        duo = st.ai_duo_cfg
        cap = duo.max_qty if size >= duo.big_account_size else duo.contracts
    elif spec.mode == "ORDER_FLOW":
        cap = st.order_flow_cfg.contracts
    else:  # STANDARD (LunqFX): sized by the risk engine, bounded only by the firm and internal caps
        cap = min(r.max_contracts.micros, r.internal.internal_max_micros)
    if "noise_ai_split" in spec.flags and spec.mode in ("NOISE", "AI_DUO"):
        cap = split_contracts(cap, st.noise_ai_split_share)
    return cap


def room_of(r: RulesConfig, stage: str) -> D:
    """DLL room and MLL room (distance minus kill-switch distance) of a fresh account, from the plan only."""
    sr = stage_rules(r, stage, dd_of(r, stage))
    mll_room = sr.max_loss - r.internal.kill_switch_mll_distance
    return mll_room if sr.dll is None else min(sr.dll, mll_room)


def per_contract(r: RulesConfig, symbol: str, stop_pts: D) -> D:
    i = r.instrument(symbol)
    slip = i.slippage_ticks or r.trade_plan.slippage_ticks
    return stop_pts / i.tick * i.tick_value + i.fee_rt + slip * i.tick_value


def realistic_stop_pts(r: RulesConfig, spec: Spec) -> D:
    i = r.instrument(spec.symbol)
    slip = i.slippage_ticks or r.trade_plan.slippage_ticks
    if spec.mode == "NOISE" and r.strategy.noise_cfg.emergency_stop_usd is not None:
        return stop_pts_for_usd(r.strategy.noise_cfg.emergency_stop_usd, i.tick, i.tick_value, i.fee_rt, slip)
    if spec.mode == "ORDER_FLOW":
        return r.strategy.order_flow_cfg.max_risk_ticks * i.tick
    return 2 * (i.min_stop_ticks or r.trade_plan.min_stop_ticks) * i.tick


def wide_stop_pts(r: RulesConfig, spec: Spec, stage: str) -> D:
    """A stop whose per-contract loss is 3x the whole MLL: nothing may ever be sized into it unscaled."""
    i = r.instrument(spec.symbol)
    sr = stage_rules(r, stage, dd_of(r, stage))
    return (3 * sr.max_loss / i.tick_value).to_integral_value() * i.tick


# ------------------------------------------------------------------------------------------------ controller driver
class Ctx:
    def __init__(self, app: Any, clock: Any, client: Any, stem: str) -> None:
        self.app, self.clock, self.client, self.stem = app, clock, client, stem
        self.st = app.state
        self.n = 0
        clock.set(AT)
        for sym, px in PRICE.items():
            self.st.controller.adapter.sim.last[sym] = px
        self.st.controller.mode = "FULL"

    def set_rules(self, spec_flags: dict[str, Any]) -> RulesConfig:
        base = rules_of(self.stem)
        off = {k: False for k in ("lunqfx", "noise", "open_drive", "ai_bias", "pm_fade", "ai_duo", "order_flow")}
        strat = base.strategy.model_copy(update={**off, **spec_flags})
        r = base.model_copy(update={"strategy": strat})
        self.st.rules.rules = r
        return r

    def account(self, stage: str, *, paper: bool = True) -> int:
        r = self.st.rules.rules
        self.n += 1
        with self.st.sessionmaker() as s:
            a = self.st.controller.create_paper_account(
                s, f"M{self.n}", stage, dd_of(r, stage), r.account_size, "matrix"
            )
            a.armed, a.selected, a.is_sim = True, True, paper
            s.commit()
            aid = a.id
        self.client.post("/api/attestation", json={"confirm": True})
        return aid

    def ext(self, aid: int) -> str:
        with self.st.sessionmaker() as s:
            return s.get(Account, aid).broker_account_id

    def signal(
        self, spec: Spec, stop_pts: D, tag: str, direction: Direction = Direction.LONG, symbol: str | None = None
    ):
        r = self.st.rules.rules
        sym = symbol or spec.symbol
        i = r.instrument(sym)
        entry = PRICE[sym]
        stop = entry - direction.sign * stop_pts
        tp = entry + direction.sign * stop_pts * 2
        with self.st.sessionmaker() as s:
            sig = SS._new_signal(
                s, FixedClock(AT), symbol=sym, key=f"{spec.name}-{tag}-{self.n}", direction=direction, at=AT,
                gate=(True, "OK", ""), features={}, plan=(spec.mode, entry, stop, tp, stop_pts, D(2)),
            )  # fmt: skip
            if spec.mode == "STANDARD":
                sig.score = r.score.min_score + 30
            del i
            s.commit()
            return sig.id

    def execute(self, sid: int, aid: int):
        return asyncio.run(self.st.controller.execute(sid, "automation", only=[aid]))

    def trades(self, aid: int):
        ext = self.ext(aid)
        return [t for t in self.st.controller.om.trades.values() if t.account == ext]

    def flat_all(self) -> None:
        with self.st.sessionmaker() as s:
            ids = [a.id for a in s.query(Account)]
        for aid in ids:
            asyncio.run(self.st.controller.flatten(aid, "matrix", "MANUAL_FLATTEN"))
        self.st.controller.om.trades.clear()


def check_trade(r: RulesConfig, spec: Spec, stage: str, t: Any, where: str, out: list[str]) -> None:
    cap = min(strategy_cap(r, spec), r.max_contracts.micros, r.internal.internal_max_micros)
    firm = firm_max_micros(r, stage, D(0))
    if t.qty > min(cap, firm):
        out.append(f"{where}: {t.qty} contracts > cap {min(cap, firm)} (strategy {cap}, firm {firm})")
    if spec.mode == "ORDER_FLOW" and t.qty != 1:
        out.append(f"{where}: Order Flow must be 1 micro, got {t.qty}")
    stop_pts = abs(t.plan.entry - t.plan.stop)
    worst = t.qty * per_contract(r, t.symbol, stop_pts)
    room = room_of(r, stage)
    if worst + r.internal.dll_safety_margin > room:
        out.append(f"{where}: worst case ${worst:.2f} + margin {r.internal.dll_safety_margin} > room ${room}")


# ------------------------------------------------------------------------------------------------ the matrix
@pytest.mark.parametrize("stem", PLAN_IDS)
def test_sizing_worst_case_one_position_and_hedge_lock_per_plan(authed, clock, stem):
    ctx = Ctx(authed.app, clock, authed, stem)
    out: list[str] = []
    opened: dict[str, int] = {}
    for stage in STAGES:
        for spec in SPECS:
            r = ctx.set_rules(spec.flags)
            where = f"{stem}/{stage}/{spec.name}"
            # 1) realistic stop and 2) an absurdly wide stop: any trade that opens must satisfy every bound
            for label, pts in (("real", realistic_stop_pts(r, spec)), ("wide", wide_stop_pts(r, spec, stage))):
                aid = ctx.account(stage)
                res = ctx.execute(ctx.signal(spec, pts, label), aid)
                if res[0].ok:
                    opened[spec.name] = opened.get(spec.name, 0) + 1
                    for t in ctx.trades(aid):
                        check_trade(r, spec, stage, t, f"{where}/{label}", out)
                ctx.flat_all()
            # 3) max open positions: a 2nd signal on an account that holds one is refused (AI Duo: its own config)
            if spec.mode in ("NOISE", "ORDER_FLOW", "AI_DUO"):
                aid = ctx.account(stage)
                pts = realistic_stop_pts(r, spec)
                allowed = (
                    r.strategy.ai_duo_cfg.max_open_positions
                    if spec.mode == "AI_DUO" and r.account_size >= r.strategy.ai_duo_cfg.big_account_size
                    else r.behavior.max_open_positions_per_account
                )
                for k in range(allowed + 2):
                    ctx.execute(ctx.signal(spec, pts, f"pos{k}"), aid)
                held = len(ctx.trades(aid))
                if held > allowed:
                    out.append(f"{where}: {held} open positions on one account, config allows {allowed}")
                for t in ctx.trades(aid):
                    check_trade(r, spec, stage, t, f"{where}/pos", out)
                if len(ctx.trades(aid)) > 1:  # aggregate worst case of everything open (AI Duo big accounts)
                    total = sum(
                        t.qty * per_contract(r, t.symbol, abs(t.plan.entry - t.plan.stop)) for t in ctx.trades(aid)
                    )
                    if total + r.internal.dll_safety_margin > room_of(r, stage):
                        out.append(f"{where}: aggregate worst case ${total:.2f} exceeds the room")
                ctx.flat_all()
        # 4) household hedge lock: EQUITY_INDEX across instruments/accounts, METALS across accounts
        r = ctx.set_rules({"noise": True})
        nz = SPECS[0]
        a, b = ctx.account(stage), ctx.account(stage)
        pts = realistic_stop_pts(r, nz)
        if not ctx.execute(ctx.signal(nz, pts, "h1"), a)[0].ok:
            out.append(f"{stem}/{stage}: hedge setup trade (NOISE long) did not open")
        else:
            for sym in ("MNQ", "MYM"):
                res = ctx.execute(ctx.signal(nz, pts, f"h-{sym}", Direction.SHORT, sym), b)
                if res[0].reason != "HEDGE_LOCK":
                    out.append(
                        f"{stem}/{stage}: EQUITY_INDEX short {sym} vs long MNQ gave {res[0].reason}, want HEDGE_LOCK"
                    )
        ctx.flat_all()
        r = ctx.set_rules({"order_flow": True})
        of = next(s for s in SPECS if s.name == "ORDER_FLOW_MGC")
        a, b = ctx.account(stage), ctx.account(stage)
        if not ctx.execute(ctx.signal(of, realistic_stop_pts(r, of), "m1"), a)[0].ok:
            out.append(f"{stem}/{stage}: METALS setup trade (Order Flow MGC long) did not open")
        else:
            res = ctx.execute(ctx.signal(of, realistic_stop_pts(r, of), "m2", Direction.SHORT), b)
            if res[0].reason != "HEDGE_LOCK":
                out.append(f"{stem}/{stage}: METALS short vs long gave {res[0].reason}, want HEDGE_LOCK")
        ctx.flat_all()
    # the matrix is only meaningful if the strategies actually traded somewhere in this plan
    for spec in SPECS:
        if spec.mode in ("NOISE", "ORDER_FLOW") and not opened.get(spec.name):
            out.append(f"{stem}/{spec.name}: never opened a trade (matrix would be vacuous)")
    assert not out, "\n".join(out)


@pytest.mark.parametrize("stem", PLAN_IDS)
def test_unverified_strategies_are_paper_only_per_plan(authed, clock, stem):
    ctx = Ctx(authed.app, clock, authed, stem)
    out: list[str] = []
    for stage in STAGES:
        for spec in SPECS:
            r = ctx.set_rules(spec.flags)
            aid = ctx.account(stage, paper=False)
            res = ctx.execute(ctx.signal(spec, realistic_stop_pts(r, spec), "np"), aid)
            refused = res[0].ok is False and res[0].reason == "PAPER_ONLY_STRATEGY"
            if spec.paper_only and not (refused and not ctx.trades(aid)):
                out.append(f"{stem}/{stage}/{spec.name}: not refused on a non-paper account: {res[0]}")
            if not spec.paper_only and res[0].reason == "PAPER_ONLY_STRATEGY":
                out.append(f"{stem}/{stage}/{spec.name}: verified strategy wrongly refused as paper-only")
            ctx.flat_all()
    assert not out, "\n".join(out)


# ------------------------------------------------------------------------------------------------ config-only checks
@pytest.mark.parametrize("stem", PLAN_IDS)
def test_unverified_strategy_flags_are_paper_only_in_config(stem):
    st = rules_of(stem).strategy
    for name, cfg in (
        ("open_drive", st.open_drive_cfg),
        ("ai_bias", st.ai_bias_cfg),
        ("pm_fade", st.pm_fade_cfg),
        ("ai_duo", st.ai_duo_cfg),
        ("order_flow", st.order_flow_cfg),
    ):
        assert cfg.paper_only is True, f"{stem}: {name} must stay paper-only"
    assert st.order_flow_cfg.contracts == 1 and st.order_flow_cfg.rr_min >= D("1.5")
    # every unverified button defaults OFF
    assert not (st.open_drive or st.ai_bias or st.ai_duo or st.order_flow), f"{stem}: unverified button ON by default"
    # MGC only through Order Flow's own switch (D96); the global instrument switch stays as the plan says
    r = rules_of(stem)
    for sym in st.order_flow_cfg.instruments:
        assert sym in r.instruments


@pytest.mark.parametrize("stem", PLAN_IDS)
def test_flat_times_news_and_position_limits_per_plan(stem):
    r = rules_of(stem)
    flats = [
        parse_hhmm(r.strategy.noise_cfg.flat_at),
        parse_hhmm(r.strategy.order_flow_cfg.flat_at),
        parse_hhmm(r.strategy.ai_bias_cfg.flat_at),
        parse_hhmm(r.strategy.ai_duo_cfg.flat_at),
        parse_hhmm(r.strategy.pm_fade_cfg.flat_at),
    ]
    auto, hard, firm = (
        parse_hhmm(r.internal.auto_flatten),
        parse_hhmm(r.internal.hard_flat),
        parse_hhmm(r.session.flat_by),
    )
    assert max(flats) <= parse_hhmm("16:00")  # strategies are flat at 16:00 ET at the latest
    assert max(flats) < auto <= hard < firm  # then the global auto flat, hard flat, then the firm's flat time
    assert r.behavior.max_open_positions_per_account == 1
    assert r.behavior.no_hedging is True
    for stage_cfg in (r.eval, r.funded):
        # our own news margins are never smaller than the firm's (flatten before the release, no entries before it)
        assert r.internal.news_flatten_before_min >= stage_cfg.news_breach_min_before
        assert r.internal.no_entry_before_news_min >= r.internal.news_flatten_before_min
    for sym, inst in r.instruments.items():  # every instrument sits in a hedge-lock super-group, and the lock sees it
        assert r.super_group_of(sym) == inst.super_group
    assert r.super_group_of("MNQ") == r.super_group_of("MYM") != r.super_group_of("MGC")
    assert r.behavior.hedge_lock_scope == r.super_group_of("MNQ")
    assert r.instrument("MGC").super_group == "METALS" and "GC" in r.super_groups["METALS"]


@pytest.mark.parametrize("stage", STAGES)
@pytest.mark.parametrize("stem", PLAN_IDS)
def test_consistency_day_stop_and_cap_present_where_the_plan_states_one(authed, stem, stage):
    from app.automation import state as stt

    r = rules_of(stem)
    pct = (
        r.eval.consistency_max_day_pct
        if stage == "EVAL"
        else (r.internal.funded_consistency_pct if r.internal.consistency_on_funded else None)
    )
    with authed.app.state.sessionmaker() as s:
        a = authed.app.state.controller.create_paper_account(s, "C", stage, dd_of(r, stage), r.account_size, "m")
        lim = stt.consistency(s, a, r)
    if pct is None:
        assert lim is None, f"{stem}/{stage}: no consistency rule in the plan, yet a limit is applied"
        return
    assert lim is not None, f"{stem}/{stage}: the plan states a {pct}% consistency rule but no limit is applied"
    assert 0 < lim.day_stop < lim.cap, f"{stem}/{stage}: day stop must be below the cap"
    ref = r.eval.profit_target if stage == "EVAL" else max(r.internal.funded_consistency_reference_min, D(0))
    assert lim.cap == (pct / 100 * ref).quantize(D("0.01"))
    if stem.startswith("lucid_pro") and stage == "FUNDED":  # D89 official payout consistency (Pro funded only)
        assert r.funded.payout_consistency is not None
