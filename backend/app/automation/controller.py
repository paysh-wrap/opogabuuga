"""Automation controller (§13): modes, approvals, fan-out to accounts, trade lifecycle, kill switch, safety monitor.

Paper by default: the Sim adapter fills on the real TradingView prices. LIVE needs PAYTIENCE_ALLOW_LIVE + the
checklist (§1.5) and a verified broker adapter — until then every account is a paper account.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app import audit
from app.automation import state as st
from app.automation.account_selector import Candidate
from app.automation.account_selector import select as select_accounts
from app.automation.preflight import allowed_mode
from app.bias import ledger as bias_ledger
from app.clock import Clock, parse_hhmm, session_date, to_et
from app.engine.filters import news_flatten_due
from app.engine.noise import stop_pts_for_usd
from app.engine.trade_plan import Direction, TradePlan, fee_cover_ticks
from app.execution import trade_state
from app.execution.adapters.base import BrokerError, conservative_mode
from app.execution.adapters.router import RoutingAdapter
from app.execution.order_manager import Event, OpenTrade, OrderManager, OrphanedPosition
from app.indicators.bars import Bar as PriceBar
from app.indicators.bars import tf_minutes
from app.management.drawdown_guard import GuardCfgView, apply_guard, guard_active, min_contracts
from app.management.dynamic_trail import TrailParams
from app.management.profit_lock import PROFIT_LOCK_REASON
from app.management.trade_manage import ManageCfg
from app.models import Account, AuditLog, Bar, Order, Payout, Signal, Trade, TradePlanRow
from app.phases.mll_tracker import MllState, update_mll
from app.phases.phase_engine import firm_max_micros, new_mll, stage_rules
from app.risk.checks import AccountView, TradeLimits, dll_remaining, pretrade
from app.risk.consistency import live_day_stop_hit
from app.risk.cushion import (
    CushionLevels,
    cushion_block,
    cushion_contracts,
    cushion_k_minus,
    cushion_level,
    cushion_share,
)
from app.risk.eval_mode import effective_risk_cfg, eval_mode_effective, one_to_one_for
from app.risk.fast_eval import effective_fast_cfg, fast_contracts, harvest_limits, quality_day_block
from app.risk.hedge_lock import OpenPosition, hedge_conflict
from app.risk.holder import RulesHolder
from app.risk.risk_base import money, risk_base
from app.risk.split_risk import SPLIT_STRATEGIES, side_budget_left, split_active, split_budget, split_contracts
from app.risk.strategy_sizing import SizeTier, auto_contracts, bias_size, plan_contracts, risk_cap
from app.risk.tiers import FloorRules, RiskCfg

MODES = ("OFF", "SEMI", "FULL")
APPROVAL_SECONDS = 90
STRATEGY_MODES = (
    "NOISE",
    "AI_BIAS",
    "PM_FADE",
    "AI_DUO",
    "ORDER_FLOW",
)  # D55: TradePlan modes of the fixed-size strategies (D107: OPEN_DRIVE removed -> its plans are NO_PLAN)
RESTART_UNMANAGED = "RESTART_UNMANAGED"  # paused_reason: a restart found a position nothing manages
CLOSE_GRACE_S = 60  # flat at the broker but no exit fill seen this long → close with a loud "P&L unverified" alert


@dataclass
class Approval:
    signal_id: int
    created: datetime
    expires: datetime
    mode: str = "SEMI"  # global mode when it was queued: a FULL-mode approval is for the SEMI-override accounts only


@dataclass
class AccountResult:
    account_id: int
    ok: bool
    reason: str | None
    contracts: int = 0
    trade_ref: str | None = None
    checks: list[dict[str, Any]] = field(default_factory=list)


def _manual(sig: Signal) -> bool:
    return bool((sig.features or {}).get("manual"))


def override_allows(override: str | None, actor: str, mode: str, manual: bool) -> bool:
    """§13 per-account mode override — only ever MORE restrictive than the global mode.
    OFF: never traded by automation or approvals. SEMI: only via a human approval (never auto-executed).
    In global FULL, a human approval is for the SEMI accounts only (the others were already auto-executed).
    The manual ticket is the user's explicit order for one account, so the override does not apply to it."""
    if manual:
        return True
    if override == "OFF":
        return False
    if actor == "automation":
        return override != "SEMI"
    return override == "SEMI" if mode == "FULL" else True


def cushion_levels(c: Any) -> CushionLevels:
    """D122: the plan's / My Settings' CushionCfg as the pure risk/cushion.py levels."""
    return CushionLevels(
        c.normal_min, c.reduce_min, c.minimal_min, c.reduce_size_minus, c.reduce_k_minus, c.minimal_k_minus,
        c.minimal_max_trades,
    )  # fmt: skip


def trail_params(c: Any, fee_ticks: int, k_minus: Decimal, of_trail: tuple[int, Decimal] | None) -> TrailParams:
    """D122: the DynamicTrailCfg as the pure management/dynamic_trail.py parameters."""
    return TrailParams(
        c.activate_r, c.min_distance_ticks, c.atr_tf_min, c.atr_period, c.swing_tf_min,
        tuple((x.until_r, x.k) for x in c.steps), c.low_vol_percentile, c.low_vol_mult, c.low_vol_lookback,
        c.k_floor, fee_ticks, k_minus, of_trail,
    )  # fmt: skip


@dataclass
class Controller:
    sessionmaker: sessionmaker[Session]
    clock: Clock
    rules: RulesHolder
    adapter: RoutingAdapter
    om: OrderManager
    mode: str = "OFF"  # §13: the app always starts OFF
    approvals: dict[int, Approval] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    notices: list[dict[str, Any]] = field(default_factory=list)  # banner/notify queue for the API layer
    _flatten_reason: str | None = None
    _flatten_alerted: set[str] = field(default_factory=set)  # accounts whose failed flatten already raised the banner
    _bar_feeds: dict[str, dict[int, datetime]] = field(default_factory=dict)  # symbol → {tf minutes: last bar seen}
    _pending_exits: dict[str, str] = field(default_factory=dict)  # D55 strategy exits still inside the minimum hold
    bus: Any = None  # app.events.EventBus: stored notifications + WS events (§19)
    feed_delayed: dict[str, float] = field(default_factory=dict)  # D112 symbol → lag s (CME data not real-time)
    feed_state: dict[str, str] = field(default_factory=dict)  # symbol → WARN | LOST (position open, no 1-minute bar)
    _exposure_since: dict[str, datetime] = field(default_factory=dict)  # symbol → first seen with an open position
    _exit_alerted: set[str] = field(default_factory=set)  # trade ids whose failed strategy exit already alerted
    _recovery_pending: set[int] = field(default_factory=set)  # account ids restart recovery could not verify yet
    _missed_alerted: set[str] = field(default_factory=set)  # "SYMBOL@close-iso" check minutes already alerted

    # ---------- setup ----------
    def load_accounts(self) -> None:
        """Register paper accounts with the simulator (balance = start + closed P&L). The simulator is in memory:
        open paper trades with a stored snapshot are rebuilt by recover_open_trades(); older rows close SIM_RESTART."""
        with self.sessionmaker() as s:
            for a in s.execute(select(Account).where(Account.is_sim)).scalars():
                closed = sum(
                    (
                        t.pnl_usd or Decimal(0)
                        for t in s.execute(
                            select(Trade).where(Trade.account_id == a.id, Trade.closed_at.is_not(None))
                        ).scalars()
                    ),
                    Decimal(0),
                )
                paid = sum(
                    (
                        p.amount
                        for p in s.execute(
                            select(Payout).where(Payout.account_id == a.id, Payout.status == "processed")
                        ).scalars()
                    ),
                    Decimal(0),
                )
                self.adapter.add_account(a.broker_account_id, (a.starting_balance or Decimal(0)) + closed - paid)
                for t in s.execute(select(Trade).where(Trade.account_id == a.id, Trade.closed_at.is_(None))).scalars():
                    if t.om_state is None:  # no snapshot (pre-session-14 row): cannot be rebuilt → close, as before
                        t.closed_at, t.exit_reason, t.pnl_usd = self.clock.now(), "SIM_RESTART", Decimal(0)
            self._commit(s)

    def notify(self, level: str, title: str, detail: str = "", kind: str = "general") -> None:
        self.notices.append({"level": level, "title": title, "detail": detail, "at": self.clock.now().isoformat()})
        del self.notices[:-50]
        if self.bus is not None:
            self.bus.notify(level, title, detail, kind)

    def publish(self, event: str, data: dict[str, Any]) -> None:
        if self.bus is not None:
            self.bus.publish(event, data)

    # ---------- accounts ----------
    def create_paper_account(
        self,
        s: Session,
        label: str,
        stage: str,
        drawdown_type: str,
        balance: Decimal,
        actor: str,
        real_id: str | None = None,
    ) -> Account:
        """real_id = Tradovate account → REAL account: orders only via the live broker + full live checklist."""
        sr = stage_rules(self.rules.rules, stage, drawdown_type)
        ext = real_id or f"SIM-{label or 'acct'}-{int(self.clock.now().timestamp())}"
        m = new_mll(sr, balance)
        a = Account(
            broker_account_id=ext,
            label=label,
            stage=stage,
            drawdown_type=drawdown_type,
            is_sim=real_id is None,
            starting_balance=balance,
            mll=m.mll,
            mll_peak=m.peak,
            mll_locked=False,
            stage_started_at=self.clock.now(),
            selected=False,
            armed=False,
        )
        s.add(a)
        s.flush()
        if real_id is None:
            self.adapter.add_account(ext, balance)
        else:
            self.adapter.live_accounts.add(ext)
        audit.record(
            s,
            self.clock,
            actor,
            "account.created",
            ext,
            {"stage": stage, "balance": str(balance), "real": bool(real_id)},
        )
        return a

    def _mll_state(self, a: Account) -> MllState:
        sr = stage_rules(self.rules.rules, a.stage, a.drawdown_type, a.dll_enabled)
        start = a.starting_balance or Decimal(0)
        if a.mll is None or a.mll_peak is None:
            return new_mll(sr, start)
        return MllState(sr.drawdown_type, sr.max_loss, a.mll_peak, a.mll, sr.lock_trigger, sr.lock_level, a.mll_locked)

    async def _equity(self, a: Account) -> tuple[Decimal, Decimal]:
        bal = await self.adapter.get_balance(a.broker_account_id)
        return bal, self.adapter.open_pnl(a.broker_account_id)

    async def open_positions(self, s: Session) -> list[OpenPosition]:
        out = []
        for a in s.execute(select(Account)).scalars():
            if a.broker_account_id not in self.adapter.accounts:
                continue
            for p in await self.adapter.get_positions(a.broker_account_id):
                out.append(OpenPosition(a.broker_account_id, p.symbol, "?", "LONG" if p.qty > 0 else "SHORT"))
        return out

    def inflight_positions(self, s: Session) -> list[OpenPosition]:
        """B5 (session 20): trades the household SENT that the broker may not report yet (CrossTrade polls). The hedge
        lock sees these too: every trade the order manager tracks (unfilled, working or open) on any account, plus
        persisted trades opened in the last `reliability.hedge_inflight_s` seconds and not closed (covers a restart
        before recovery). Only ever adds positions → the lock can only block more, never less."""
        out = [
            OpenPosition(t.account, t.symbol, t.profile or "?", t.d.value)
            for t in self.om.trades.values()
            if not t.closed
        ]
        since = self.clock.now() - timedelta(seconds=self.rules.rules.reliability.hedge_inflight_s)
        rows = s.execute(
            select(Trade.symbol, Trade.direction, Account.broker_account_id)
            .join(Account, Account.id == Trade.account_id)
            .where(Trade.closed_at.is_(None), Trade.opened_at >= since, Trade.mode != "BACKTEST")
        ).all()
        out += [OpenPosition(acct, sym, "?", d) for sym, d, acct in rows]
        return out

    # ---------- mode ----------
    def set_mode(self, s: Session, requested: str, actor: str) -> str:
        if requested not in MODES:
            raise ValueError("mode must be OFF, SEMI or FULL")
        if requested != "OFF" and self.rules.error:
            raise ValueError(f"cannot enable automation: {self.rules.error}")
        armed = list(s.execute(select(Account).where(Account.armed)).scalars())
        sessions = [st.stage_sessions(s, a) for a in armed]
        got = allowed_mode(
            requested,
            sessions,
            self.rules.rules.automation.semi_auto_sessions_per_stage,
            conservative_mode(self.adapter),
        )
        self.mode = got
        st.set_setting(s, "automation.mode", got, self.clock.now())
        audit.record(s, self.clock, actor, "automation.mode", got, {"requested": requested})
        return got

    # ---------- signals ----------
    def on_signal_pass(self, signal_id: int) -> str:
        """Called when a signal passes G1–G7. Returns what happened."""
        if self.mode == "OFF":
            return "OFF"
        now = self.clock.now()
        if self.mode == "SEMI":
            self.approvals[signal_id] = Approval(signal_id, now, now + timedelta(seconds=APPROVAL_SECONDS), "SEMI")
            return "APPROVAL"
        # §13 per-account override (only more restrictive): in FULL, armed+selected SEMI accounts still need approval.
        with self.sessionmaker() as s:
            semi = s.execute(
                select(Account.id).where(Account.mode_override == "SEMI", Account.armed, Account.selected)
            ).first()
        if semi is not None:
            self.approvals[signal_id] = Approval(signal_id, now, now + timedelta(seconds=APPROVAL_SECONDS), "FULL")
            return "EXECUTE_AND_APPROVAL"
        return "EXECUTE"

    def expire_approvals(self) -> list[int]:
        now = self.clock.now()
        gone = [k for k, v in self.approvals.items() if v.expires <= now]
        for k in gone:
            del self.approvals[k]
        return gone

    def _plan(self, s: Session, sig: Signal) -> TradePlan | None:
        r = self.rules.rules
        any_1to1 = (
            r.one_to_one_mode.enabled or r.scalp_mode.enabled or (self.rules.eval_mode_on and r.eval_mode.one_to_one)
        )
        want = "ONE_TO_ONE" if any_1to1 else "STANDARD"
        rows = list(s.execute(select(TradePlanRow).where(TradePlanRow.signal_id == sig.id)).scalars())
        strategy = (sig.features or {}).get("strategy")
        if strategy in STRATEGY_MODES:  # D55: each strategy carries exactly one plan in its own mode
            want = strategy
            rows = [r for r in rows if r.mode == strategy]
        row = next((r for r in rows if r.mode == want), None) or next((r for r in rows if r.mode == "STANDARD"), None)
        if row is None:
            return None
        return TradePlan(
            Direction(row.direction),
            row.entry,
            row.stop,
            row.take_profit,
            row.risk_pts,
            row.rr,
            row.partial_price,
            row.breakeven_price,
            row.lock_price,
            row.mode,
        )

    async def execute(self, signal_id: int, actor: str, only: list[int] | None = None) -> list[AccountResult]:
        async with self.lock:
            return await self._execute(signal_id, actor, only)

    async def _execute(self, signal_id: int, actor: str, only: list[int] | None) -> list[AccountResult]:
        r = self.rules.rules
        out: list[AccountResult] = []
        with self.sessionmaker() as s:
            sig = s.get(Signal, signal_id)
            if sig is None or sig.status != "PASS":
                return [AccountResult(0, False, "SIGNAL_NOT_TRADEABLE")]
            if sig.symbol in self.feed_delayed:
                return [AccountResult(0, False, "FEED_DELAYED")]  # D112: CME data not real-time → no NEW entries
            if self.feed_state.get(sig.symbol):
                return [AccountResult(0, False, "FEED_LOST")]  # position open + no price bars: no NEW entries
            plan0 = self._plan(s, sig)
            if plan0 is None:
                return [AccountResult(0, False, "NO_PLAN")]
            manual, mode = _manual(sig), self.mode
            if actor != "automation" and not manual:
                # §13: a human executes only a LIVE approval, and consumes it (no double click / late execute). The
                # FULL auto-run keeps it queued for SEMI-override accounts. Use the mode it was queued under, so a
                # FULL-mode approval never re-trades the accounts that were already auto-executed.
                ap = self.approvals.pop(signal_id, None)
                if ap is None or ap.expires <= self.clock.now():
                    return [AccountResult(0, False, "APPROVAL_EXPIRED")]
                mode = ap.mode
            all_accts = list(s.execute(select(Account)).scalars())
            any_live = any(a.stage == "LIVE" and not a.is_sim for a in all_accts)
            # one entry per model per account: an account that already has an order for this signal never re-enters
            done = set(s.execute(select(Order.account_id).where(Order.signal_id == sig.id)).scalars())
            accts = [a for a in all_accts if override_allows(a.mode_override, actor, mode, manual)]
            if plan0.mode == "AI_DUO":  # D83: per-market account choice (max 1 position per account is unchanged)
                mine = r.strategy.ai_duo_cfg.accounts.get(sig.symbol)  # type: ignore[call-overload]
                others = {i for k, i in r.strategy.ai_duo_cfg.accounts.items() if k != sig.symbol and i}
                accts = [a for a in accts if (a.id == mine if mine else a.id not in others)]
                if mine and not accts:
                    return [AccountResult(mine, False, "DUO_ASSIGNED_ACCOUNT_UNAVAILABLE")]
            out += [
                AccountResult(a.id, False, "ALREADY_TRADED")
                for a in accts
                if a.id in done and a.selected and (only is None or a.id in only)
            ]
            cands = [
                Candidate(a.id, a.priority, a.selected, a.armed, a.paused_reason is not None, a.stage, a.is_sim)
                for a in accts
                if (only is None or a.id in only) and a.id not in done
            ]
            chosen = select_accounts(cands, r.automation.accounts_to_trade, any_live)
            inst = r.instrument(sig.symbol)
            std, evm = RiskCfg.standard(r.internal), RiskCfg.evaluation(r.eval_mode)
            fl = FloorRules(
                r.internal.day_lockin_r,
                r.internal.dd_floor_pct,
                r.internal.streak_floor_losses,
                r.internal.streak_release_wins,
            )
            for c in chosen:
                a = s.get(Account, c.id)
                assert a is not None
                res = await self._one(s, a, sig, plan0, inst, std, evm, fl, actor)
                out.append(res)
            self._commit(s)
        return out

    async def _one(
        self,
        s: Session,
        a: Account,
        sig: Signal,
        plan0: TradePlan,
        inst: Any,
        std: RiskCfg,
        evm: RiskCfg,
        fl: FloorRules,
        actor: str,
    ) -> AccountResult:
        r = self.rules.rules
        now = self.clock.now()
        try:
            bal, opnl = await self._equity(a)
        except BrokerError as e:
            return AccountResult(a.id, False, f"BROKER_ERROR: {e}")
        mll = self._mll_state(a)
        equity = bal + opnl
        base = risk_base(equity, mll.mll)
        strategy = plan0.mode if plan0.mode in STRATEGY_MODES else ""
        # D102 (user 2026-11-11): no strategy is FORCED paper-only (defaults false). A plan file may still opt a
        # strategy into paper-only (tighten-only). Live trading itself stays behind every live gate (§1.5).
        paper_only = {
            "AI_BIAS": r.strategy.ai_bias_cfg.paper_only,
            "PM_FADE": r.strategy.pm_fade_cfg.paper_only,
            "AI_DUO": r.strategy.ai_duo_cfg.paper_only,
            "ORDER_FLOW": r.strategy.order_flow_cfg.paper_only,
        }
        if paper_only.get(strategy) and not a.is_sim:
            return AccountResult(a.id, False, "PAPER_ONLY_STRATEGY")  # opted in by the plan file
        if strategy == "PM_FADE" and a.stage == "EVAL" and r.strategy.pm_fade_cfg.eval_off:
            return AccountResult(a.id, False, "FADE_OFF_IN_EVAL")  # D132 / I3: EVAL stage only (FUNDED/LIVE keep it)
        one_to_one = (
            plan0.mode == "ONE_TO_ONE"
            and a.stage in r.one_to_one_mode.stages
            and one_to_one_for(
                a.stage,
                a.eval_mode,
                self.rules.eval_mode_on,
                r.one_to_one_mode.enabled or r.scalp_mode.enabled,
                r.eval_mode.one_to_one,
            )
        )
        plan = plan0
        guard_on = False
        if not one_to_one and not strategy:
            if plan0.mode == "ONE_TO_ONE":  # stage not allowed for 1:1 → fall back to the standard plan
                std_row = next(
                    (
                        x
                        for x in s.execute(
                            select(TradePlanRow).where(
                                TradePlanRow.signal_id == sig.id, TradePlanRow.mode == "STANDARD"
                            )
                        ).scalars()
                    ),
                    None,
                )
                if std_row is None:
                    return AccountResult(a.id, False, "NO_PLAN_FOR_STAGE")
                plan = TradePlan(
                    Direction(std_row.direction),
                    std_row.entry,
                    std_row.stop,
                    std_row.take_profit,
                    std_row.risk_pts,
                    std_row.rr,
                    mode="STANDARD",
                )
            guard_on = guard_active(a.drawdown_type, mll.locked, GuardCfgView(r.drawdown_guard.mode))
            if guard_on:
                plan = apply_guard(plan, inst.tick, fee_cover_ticks(inst.fee_rt, inst.tick_value))
        duo = r.strategy.ai_duo_cfg if strategy == "AI_DUO" else None
        if duo is not None:  # D85: the Drawdown Guard's own auto rule (intraday, MLL not locked) → 2-bracket mode
            guard_on = guard_active(a.drawdown_type, mll.locked, GuardCfgView(r.drawdown_guard.mode))
            if guard_on:
                plan = apply_guard(plan, inst.tick, fee_cover_ticks(inst.fee_rt, inst.tick_value))
        acct_size = a.starting_balance if a.starting_balance and a.starting_balance > 0 else r.account_size
        big = duo is not None and acct_size >= duo.big_account_size  # D85: 150K accounts only
        mine = [t for t in self.om.trades.values() if t.account == a.broker_account_id]
        positions = await self.open_positions(s)
        n_open = max(sum(1 for p in positions if p.account == a.broker_account_id), len(mine))
        view = AccountView(
            a.broker_account_id,
            a.stage,
            a.selected,
            a.armed,
            True,
            st.attested_today(s, now),
            st.payout_pending(s, a),
            any(p.account == a.broker_account_id for p in positions)
            or any(t.account == a.broker_account_id and self.om.has_unfilled(t) for t in self.om.trades.values()),
            a.paused_reason,
            equity,
            mll.mll,
            st.dll_for(r, a),
            base,
            max_open_positions=duo.max_open_positions if duo is not None and big else 1,
            open_positions=n_open,
            open_risk_usd=sum((self._open_risk(t) for t in mine), Decimal(0)) if duo is not None else Decimal(0),
        )
        # D115 (user 2026-11-11): each strategy's OWN per-plan size (config/rules/*.yaml), scaled down for an account
        # smaller than the plan; NOISE / PM_FADE use the size table below. Caps applied later: firm + internal max,
        # $ budgets (risk_cap), DLL/MLL worst case, consistency, split 50/50, hedge lock.
        fixed = (
            plan_contracts(
                {
                    "NOISE": r.strategy.noise_cfg.contracts,
                    "AI_BIAS": r.strategy.ai_bias_cfg.contracts,
                    "PM_FADE": r.strategy.pm_fade_cfg.contracts,
                    "AI_DUO": (r.strategy.ai_duo_cfg.max_qty if big else r.strategy.ai_duo_cfg.contracts),
                    "ORDER_FLOW": r.strategy.order_flow_cfg.contracts,
                }[strategy],
                r.account_size,
                acct_size,
            )
            if strategy
            else None
        )
        brake = {
            "AI_DUO": r.strategy.ai_duo_cfg.brake_below,
            "AI_BIAS": r.strategy.ai_bias_cfg.brake_below,
            "ORDER_FLOW": r.strategy.order_flow_cfg.brake_below,
        }.get(strategy)
        if brake is not None and fixed is not None and fixed > 1:  # D85/D115 cushion brake (size-table brake reused)
            tier = SizeTier(acct_size, r.eval.max_loss_limit, fixed, brake, 1)
            fixed = auto_contracts(acct_size, base, [tier]).contracts
        table = r.strategy.active_size_table()  # D64: Regular or High-risk profile
        eval_sizing = bool(r.strategy.active_eval_table()) and eval_mode_effective(
            a.stage, a.eval_mode, self.rules.eval_mode_on
        )
        if eval_sizing:  # D66: Evaluation Mode for the MAIN strategy — EVAL stage only (pure check in risk/eval_mode)
            table = r.strategy.active_eval_table()  # D66 / D69 (High risk → size_table_eval_high)
        if strategy in ("NOISE", "PM_FADE") and table:  # D63: size by this account's own size
            size = a.starting_balance if a.starting_balance and a.starting_balance > 0 else r.account_size
            remaining_frac: Decimal | None = None
            if eval_sizing:  # share of the eval target still to earn at the start of this session (D69 taper)
                day0 = st.day_stats(s, a, now).day_profit
                done = bal - day0 - (a.starting_balance or r.account_size)
                remaining_frac = max(r.eval.profit_target - done, Decimal(0)) / r.eval.profit_target
            auto = auto_contracts(
                size,
                base,
                [
                    SizeTier(
                        t.account_size,
                        t.mll,
                        t.contracts,
                        t.brake_below,
                        t.brake_contracts,
                        t.grow_per,
                        t.max_contracts,
                        t.taper_below_remaining,
                        t.taper_contracts,
                    )
                    for t in table
                ],
                remaining_frac,
            )
            fixed = auto.contracts
            row = next((t for t in table if t.account_size == auto.tier), None)
            ai_call = 0
            if r.strategy.ai_sizing and row is not None and size >= r.strategy.ai_sizing_min_account:
                ai_call = bias_ledger.sizing_call(
                    s,
                    inst.bias_proxy,
                    sig.symbol,
                    to_et(now).date(),
                    float(r.strategy.ai_sizing_min_accuracy),
                    r.strategy.ai_sizing_min_calls,
                )
                fixed = bias_size(fixed, row.contracts, plan.direction.sign, ai_call)  # D74 (proven record only)
            if (
                row is not None and row.stop_usd is not None
            ):  # D70: row-specific emergency stop (e.g. 25K high-risk eval)
                slip = inst.slippage_ticks or r.trade_plan.slippage_ticks
                pts = stop_pts_for_usd(row.stop_usd, inst.tick, inst.tick_value, inst.fee_rt, slip)
                risk = pts
                plan = replace(
                    plan,
                    stop=plan.entry - plan.direction.sign * pts,
                    risk_pts=risk,
                    rr=(plan.take_profit - plan.entry) * plan.direction.sign / risk,
                )
            if eval_sizing and row is not None and row.day_lock_pct is not None:  # D66 day lock-in (eval only)
                day_profit = st.day_stats(s, a, now).day_profit
                start_profit = bal - day_profit - (a.starting_balance or r.account_size)
                remaining = r.eval.profit_target - start_profit
                if day_profit > 0 and remaining > 0 and day_profit >= row.day_lock_pct * remaining:
                    return AccountResult(a.id, False, "EVAL_DAY_LOCK")
            audit.record(
                s,
                self.clock,
                actor,
                "trade.auto_size",
                a.broker_account_id,
                {
                    "signal": sig.id,
                    "contracts": auto.contracts,
                    "ai_call": ai_call,
                    "contracts_final": fixed,
                    "tier": str(auto.tier),
                    "braked": auto.braked,
                    "profile": "EVAL"
                    if eval_sizing
                    else "SUGGESTED"
                    if r.strategy.suggested_size and r.strategy.size_table_suggested
                    else "HIGH"
                    if r.strategy.high_risk
                    else "REGULAR",
                },
            )
        # D87 Fast Evaluation — EVAL stage only (pure check in risk/fast_eval); every other check below still runs
        fast_cfg = effective_fast_cfg(a.stage, self.rules.fast_eval_on, r.fast_eval)
        fast_pair = None
        consistency_lim = st.consistency(s, a, r)
        if fast_cfg is not None:
            fctx = st.fast_ctx(s, a, base, r, now, bal)
            skip = quality_day_block(fast_cfg, st.prior_day_pnls(s, a, now, fast_cfg.quality_day.trailing_days))
            if skip is not None:
                audit.record(
                    s, self.clock, actor, "trade.fast_eval", a.broker_account_id, {"signal": sig.id, "skip": skip}
                )
                return AccountResult(a.id, False, skip)
            if fixed is not None:
                sized = fast_contracts(fast_cfg, fctx, fixed)
                if sized != fixed:
                    audit.record(
                        s, self.clock, actor, "trade.fast_eval", a.broker_account_id,
                        {"signal": sig.id, "contracts_before": fixed, "contracts_after": sized},
                    )  # fmt: skip
                fixed = sized
            fast_pair = (fast_cfg, fctx)
            consistency_lim = harvest_limits(consistency_lim, fast_cfg, r.eval.profit_target)
        side_left: Decimal | None = None
        if strategy in SPLIT_STRATEGIES and split_active(
            r.strategy.noise_ai_split, r.strategy.noise, r.strategy.ai_duo
        ):  # D92: half size (down, min 1) + half the daily loss budget for this side; only ever tightens
            share = r.strategy.noise_ai_split_share
            if fixed is not None:
                fixed = split_contracts(fixed, share)
            budget = split_budget(st.dll_for(r, a), share)
            if budget is not None:
                side_open = sum(
                    (
                        self._open_risk(t)
                        for t in self.om.trades.values()
                        if t.account == a.broker_account_id and t.strategy == strategy
                    ),
                    Decimal(0),
                )
                side_left = side_budget_left(budget, st.strategy_day_pnl(s, a, now, strategy), side_open)
            audit.record(
                s,
                self.clock,
                actor,
                "trade.split_risk",
                a.broker_account_id,
                {"signal": sig.id, "strategy": strategy, "contracts": fixed, "budget_left": str(side_left)},
            )
        cush_k = Decimal(0)
        cc = r.strategy.cushion
        if strategy and fixed is not None and getattr(cc, strategy.lower(), False):
            # D122 cushion level controls: tighten-only on top of every check below (size tables untouched)
            lv = cushion_levels(cc)
            level = cushion_level(cushion_share(equity, mll.mll, mll.max_loss), lv)
            stopped = self._cushion_stopped(s, a, now)
            if level == "STOP" and not stopped:
                audit.record(
                    s, self.clock, actor, "risk.cushion_stop", a.broker_account_id,
                    {"session": session_date(now).isoformat(), "cushion": str(equity - mll.mll)},
                )  # fmt: skip
                self.notify("warn", "Cushion STOP - no new entries this session", f"{a.label}: cushion below STOP")
            skip = cushion_block(level, st.day_stats(s, a, now).trades, stopped, lv)
            sized = cushion_contracts(level, fixed, lv)
            audit.record(
                s, self.clock, actor, "trade.cushion", a.broker_account_id,
                {"signal": sig.id, "level": level, "contracts_before": fixed, "contracts_after": sized, "skip": skip},
            )  # fmt: skip
            if skip is not None:
                return AccountResult(a.id, False, skip)
            fixed, cush_k = sized, cushion_k_minus(level, lv)
        lim = TradeLimits(
            inst.tick,
            inst.tick_value,
            inst.fee_rt,
            inst.slippage_ticks or r.trade_plan.slippage_ticks,
            firm_max_micros(r, a.stage, bal - st.day_stats(s, a, now).day_profit - (a.starting_balance or Decimal(0))),
            r.internal.internal_max_micros,
            min_contracts(guard_on, r.drawdown_guard.min_contracts_on, r.drawdown_guard.min_contracts_off),
            r.internal.dll_safety_margin,
            r.internal.pause_below_risk_base,
            r.internal.kill_switch_mll_distance,
            Decimal(2) if self.rules.low_risk else None,  # D36: low risk may still trade 1 micro ≤ normal risk
            fixed_contracts=fixed,
            shrink_fraction=r.strategy.drawdown_shrink if strategy in ("NOISE", "AI_BIAS", "AI_DUO") else None,
            max_risk_usd=risk_cap(  # D85 AI Duo $250 · D115 strategy budget · D115 plan per-trade cap
                duo.max_risk_usd if duo is not None else None,
                {
                    "AI_BIAS": r.strategy.ai_bias_cfg.max_risk_usd,
                    "ORDER_FLOW": r.strategy.order_flow_cfg.max_risk_usd,
                }.get(strategy),
                r.strategy.max_trade_risk_usd if strategy else None,
            ),
            shrink_min_pct=r.strategy.drawdown_min_stop_pct,
            side_budget_left=side_left,
        )
        rcfg = effective_risk_cfg(a.stage, a.eval_mode, self.rules.eval_mode_on, std, evm)
        pt = pretrade(
            acct=view,
            plan=plan,
            score=sig.score or Decimal(0),
            rcfg=rcfg,
            ctx=st.risk_ctx(s, a, base, now, r),
            floor=fl,
            day=st.day_state(s, a, opnl, now),
            day_limits=st.day_limits(r, a.stage),
            consistency=consistency_lim,
            lim=lim,
            hedge_conflict=hedge_conflict(
                r, sig.symbol, plan.direction.value, positions + self.inflight_positions(s)
            )  # B5: orders in flight count too
            is not None,
            fast=fast_pair,
        )
        audit.record(
            s,
            self.clock,
            actor,
            "trade.pretrade",
            a.broker_account_id,
            {"signal": sig.id, "ok": pt.ok, "reason": pt.reason, "checks": pt.checks},
        )
        if not pt.ok:
            return AccountResult(a.id, False, pt.reason, checks=pt.checks)
        if pt.new_stop is not None:  # D57: drawdown-scaled emergency stop (strategy trades exit by their own rules)
            risk_pts = (plan.entry - pt.new_stop) * plan.direction.sign
            plan = replace(
                plan,
                stop=pt.new_stop,
                risk_pts=risk_pts,
                rr=(plan.take_profit - plan.entry) * plan.direction.sign / risk_pts,
            )
            audit.record(
                s,
                self.clock,
                actor,
                "trade.stop_scaled",
                a.broker_account_id,
                {"signal": sig.id, "stop": str(pt.new_stop)},
            )
        if "invalid" not in sig.features or "t2" not in sig.features:
            return AccountResult(a.id, False, "SIGNAL_MISSING_MODEL_LEVELS", checks=pt.checks)
        rr_window = (
            Decimal(str(sig.features["invalid"])),
            Decimal(str(sig.features["t2"])),
            r.trade_plan.rr_min,
            Decimal(str(sig.features.get("rr_max", r.trade_plan.rr_max))),  # D36: per-signal cap survives the fill
            inst.stop_buffer_ticks or r.trade_plan.stop_buffer_ticks,
            inst.min_stop_ticks or r.trade_plan.min_stop_ticks,
        )
        try:
            self.om.split_for_defence = r.internal.adverse_half_enabled
            sm = r.scalp_mode
            self.om.scalp_runner = (sm.runner_r, sm.trail_r) if sm.enabled else None
            t = await self.om.open_trade(
                a.broker_account_id,
                sig.symbol,
                plan,
                pt.contracts,
                guard_on,
                inst.tick,
                inst.tick_value,
                now,
                rr_window,
                "market" if strategy else r.entry.mode,  # D107: the only limit strategy (OPEN_DRIVE) is gone
                self._strategy_deadline(sig) if strategy else self._limit_deadline(sig, now),
                trade_id=f"P-{sig.id}-{a.id}",  # deterministic: unique across restarts, broker clOrdId derives from it
            )
            t.profile, t.signal_id, t.strategy = sig.profile, sig.id, strategy
            if duo is not None:  # D85: break-even / profit lock / trail on every Duo position, each on its own
                step = duo.step_trail.get(sig.symbol)  # type: ignore[call-overload]
                lk = None if step else duo.lock_pts[sig.symbol]  # type: ignore[index]
                ai = (sig.features or {}).get("lock_price")  # the AI setup's own lock level (research setups)
                t.manage = ManageCfg(
                    duo.be_r, lk[0] if lk else None, lk[1] if lk else None, duo.trail_start_r, duo.trail_r,
                    fee_cover_ticks(inst.fee_rt, inst.tick_value), Decimal(str(ai)) if ai else None,
                    step[0] if step else None, step[1] if step else None,
                )  # fmt: skip
            dt = r.strategy.dynamic_trail
            if strategy and getattr(dt, strategy.lower(), False):  # D122 dynamic trailing stop (toggle per strategy)
                ar = r.strategy.order_flow_cfg.ar
                of = (
                    (ar.trail_candle_min, ar.be_after_r)
                    if strategy == "ORDER_FLOW" and "zone" not in (sig.features or {})
                    else None
                )  # D101 AR candle trail wired here (zone trades keep their own D111 bar-close trail)
                t.dyn_trail = trail_params(dt, fee_cover_ticks(inst.fee_rt, inst.tick_value), cush_k, of)
            lock = r.strategy.noise_profit_lock()  # D82 / D75-P1 (preset C); D132 100/80 pt trigger toggle
            if strategy == "NOISE" and lock is not None:
                t.profit_lock = lock
        except OrphanedPosition as e:
            # leg placement failed AND the emergency flatten failed: keep the position tracked (watchdog flattens it),
            # pause the account for good (never auto-resumes) and raise the banner (§1.8)
            self._persist_trade(
                s, a, sig, plan, e.trade, pt.contracts, pt.risk_usd or Decimal(0), guard_on, rcfg.kind, actor
            )
            st.day_stats(s, a, now).trades += 1
            a.paused_reason, a.armed = "ORPHAN_POSITION", False
            audit.record(
                s, self.clock, "automation", "account.paused", a.broker_account_id, {"reason": "ORPHAN_POSITION"}
            )
            self.notify("error", "ORPHAN POSITION — flatten failed, act manually in Tradovate", f"{a.label}: {e}")
            return AccountResult(a.id, False, "ORPHAN_POSITION", checks=pt.checks)
        except BrokerError as e:
            a.paused_reason, a.armed = "ORDER_REJECTS", False
            self.notify("error", "Order failed — account paused", f"{a.label}: {e}")
            return AccountResult(a.id, False, "ORDER_FAILED", checks=pt.checks)
        self._persist_trade(s, a, sig, plan, t, pt.contracts, pt.risk_usd or Decimal(0), guard_on, rcfg.kind, actor)
        st.day_stats(s, a, now).trades += 1
        a.last_trade_at = now
        for f in self.adapter.drain_fills():
            await self._handle_events(s, await self.om.on_fill(f))
        return AccountResult(a.id, True, None, pt.contracts, t.trade_id, pt.checks)

    @staticmethod
    def _cushion_stopped(s: Session, a: Account, now: datetime) -> bool:
        """D122: a cushion STOP earlier this session (audited, so it survives a restart) blocks until the next one."""
        row = s.execute(
            select(AuditLog)
            .where(AuditLog.action == "risk.cushion_stop", AuditLog.entity == a.broker_account_id)
            .order_by(AuditLog.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        return row is not None and (row.payload or {}).get("session") == session_date(now).isoformat()

    @staticmethod
    def _strategy_deadline(sig: Signal) -> datetime | None:
        """D55: an entry may work until features.entry_expires_at when a strategy sets it (none does after D107)."""
        until = (sig.features or {}).get("entry_expires_at")
        return datetime.fromisoformat(until) if until else None

    async def strategy_exit(self, signal_id: int, reason: str) -> int:
        """D55: close every open trade of this strategy signal (trailing exit, 16:00 flat, time stop).
        Returns how many trades were flattened/cancelled now; ones inside the minimum hold retry on the next bar."""
        done = 0
        async with self.lock:
            with self.sessionmaker() as s:
                for t in [t for t in self.om.trades.values() if t.signal_id == signal_id and not t.closing]:
                    try:
                        ev = await self.om.strategy_exit(t.trade_id, reason, self.clock.now())
                    except (
                        BrokerError
                    ) as e:  # never silent, never lost: the exit marker stays, retried every bar/minute
                        self._pending_exits[t.trade_id] = reason
                        self._exit_failed(s, t, reason, e)
                        continue
                    if ev is None:
                        self._pending_exits[t.trade_id] = reason
                        continue
                    self._pending_exits.pop(t.trade_id, None)
                    audit.record(s, self.clock, "automation", "trade.strategy_exit", t.account, {"reason": reason})
                    done += 1
                    await self._handle_events(s, ev)
                for f in self.adapter.drain_fills():
                    await self._handle_events(s, await self.om.on_fill(f))
                self._commit(s)
        return done

    def _exit_failed(self, s: Session, t: OpenTrade, reason: str, e: Exception) -> None:
        if t.trade_id in self._exit_alerted:
            return  # the retry keeps running quietly; the first failure already raised the banner
        self._exit_alerted.add(t.trade_id)
        audit.record(
            s, self.clock, "automation", "trade.exit_failed", t.account, {"reason": reason, "error": str(e)[:200]}
        )
        self.notify(
            "error",
            "Exit order failed - retrying",
            f"{t.account} {t.symbol}: {reason} ({type(e).__name__}). The app keeps retrying; Flatten if it persists.",
            "exit",
        )

    async def _retry_strategy_exits(self, s: Session) -> None:
        for tid, reason in list(self._pending_exits.items()):
            t = self.om.trades.get(tid)
            if t is None or t.closing:
                del self._pending_exits[tid]  # closed / already flattening: nothing left to retry
                continue
            try:
                ev = await self.om.strategy_exit(tid, reason, self.clock.now())
            except BrokerError as e:
                self._exit_failed(s, t, reason, e)
                continue
            if ev is None:
                continue
            del self._pending_exits[tid]
            self._exit_alerted.discard(tid)
            await self._handle_events(s, ev)

    async def exit_watchdog(self) -> None:
        """Watchdog step: a strategy exit was REQUESTED (marker on the signal) but the trade is not closed. Re-issue it
        until the broker confirms the flat (the signal turns CLOSED only in _close_trade). Covers a crash after the
        request, an exit lost inside the 6 s hold, and a failed flatten. The 16:44 hard flat stays the backstop."""
        async with self.lock:
            with self.sessionmaker() as s:
                since = self.clock.now() - timedelta(days=3)
                for sig in s.execute(select(Signal).where(Signal.status == "PASS", Signal.bar_time >= since)).scalars():
                    mark = (sig.features or {}).get("exit_requested")
                    if not mark or sig.features.get("state") != "OPEN":
                        continue
                    reason = str(mark.get("reason", "EXIT_REQUESTED"))
                    rows = list(
                        s.execute(select(Trade).where(Trade.signal_id == sig.id, Trade.closed_at.is_(None))).scalars()
                    )
                    if not rows:
                        self._mark_signal_closed(s, sig.id, reason)
                        continue
                    for row in rows:
                        t = self.om.trades.get(row.trade_ref or "")
                        if t is not None and not t.closing and t.trade_id not in self._pending_exits:
                            self._pending_exits[t.trade_id] = reason
                        elif t is None:  # not under management (never recovered): flatten its account directly
                            a = s.get(Account, row.account_id)
                            if a is not None and a.broker_account_id in self.adapter.accounts:
                                await self._flatten_account(s, a, reason)
                await self._retry_strategy_exits(s)
                self._commit(s)

    def _open_risk(self, t: OpenTrade) -> Decimal:
        """$ still at risk on an open position: per open leg (entry − current stop, never below 0) × qty at the tick
        value, plus round-trip fee and slippage — the same per-contract formula the pre-trade sizing uses."""
        total = Decimal(0)
        r = self.rules.rules
        inst = r.instrument(t.symbol)
        slip = inst.slippage_ticks or r.trade_plan.slippage_ticks
        for leg in t.legs:
            if leg.closed:
                continue
            entry = leg.entry if leg.entry is not None else t.plan.entry  # an unfilled entry still carries its risk
            dist = max((entry - leg.stop) * t.d.sign, Decimal(0))
            total += leg.qty * (dist / t.tick * t.tick_value + inst.fee_rt + slip * t.tick_value)
        return total

    def _mark_lock_exit(self, s: Session, signal_id: int | None) -> None:
        """D82 / D75-P1: a locked-stop exit ends NOISE for the day (strategy_service reads `lock_exit`).
        The signal turns CLOSED once its last trade is closed."""
        sig = s.get(Signal, signal_id) if signal_id is not None else None
        if sig is None:
            return
        feats = {**(sig.features or {}), "lock_exit": True}
        none_open = (
            s.execute(select(Trade.id).where(Trade.signal_id == sig.id, Trade.closed_at.is_(None))).first() is None
        )
        if none_open and feats.get("state") == "OPEN":
            feats = {
                **feats,
                "state": "CLOSED",
                "exit_reason": PROFIT_LOCK_REASON,
                "exit_at": self.clock.now().isoformat(),
            }
        sig.features = feats
        sig.updated_at = self.clock.now()

    def _mark_signal_closed(self, s: Session, signal_id: int | None, reason: str) -> None:
        """A strategy signal whose exit was requested turns CLOSED only now, when its last trade is really closed."""
        sig = s.get(Signal, signal_id) if signal_id is not None else None
        if sig is None or not (sig.features or {}).get("exit_requested") or sig.features.get("state") != "OPEN":
            return
        if s.execute(select(Trade.id).where(Trade.signal_id == sig.id, Trade.closed_at.is_(None))).first() is not None:
            return  # another account's trade of this signal is still open
        mark = sig.features["exit_requested"]
        sig.features = {
            **sig.features,
            "state": "CLOSED",
            "exit_reason": str(mark.get("reason", reason)),
            "exit_at": self.clock.now().isoformat(),
        }
        sig.updated_at = self.clock.now()

    # ---------- persistence of the live trades (restart recovery) ----------
    def _commit(self, s: Session) -> None:
        self._save_states(s)
        s.commit()

    def _save_states(self, s: Session) -> None:
        """Snapshot every tracked trade onto its Trade row so a restart can rebuild order management."""
        for t in self.om.trades.values():
            row = self._trade_row(s, t.trade_id, t.account)
            if row is not None:
                snap = trade_state.dump(t)
                if row.om_state != snap:
                    row.om_state = snap

    def _trade_row(self, s: Session, ref: str, account_ext: str | None = None) -> Trade | None:
        """The OPEN trade row for a trade ref (newest first). Old rows (refs restarted at T1 after every restart) and
        closed rows never match, so a lookup can no longer raise MultipleResultsFound."""
        q = select(Trade).where(Trade.trade_ref == ref, Trade.closed_at.is_(None))
        if account_ext is not None:
            q = q.where(Trade.account_id.in_(select(Account.id).where(Account.broker_account_id == account_ext)))
        return s.execute(q.order_by(Trade.id.desc())).scalars().first()

    def _limit_deadline(self, sig: Signal, now: datetime) -> datetime | None:
        """limit_cisd: the entry may work for limit_timeout_bars bars of the signal's (LTF) timeframe."""
        r = self.rules.rules
        if r.entry.mode != "limit_cisd":
            return None
        ltf = r.profiles.TIGHT.ltf if sig.profile == "TIGHT" else r.profiles.STD.ltf
        return now + timedelta(minutes=r.entry.limit_timeout_bars * tf_minutes(ltf))

    def _persist_trade(
        self,
        s: Session,
        a: Account,
        sig: Signal,
        plan: TradePlan,
        t: OpenTrade,
        contracts: int,
        risk_usd: Decimal,
        guard_on: bool,
        kind: str,
        actor: str,
    ) -> None:
        now = self.clock.now()
        s.add(
            Trade(
                account_id=a.id,
                signal_id=sig.id,
                symbol=sig.symbol,
                direction=plan.direction.value,
                qty=contracts,
                entry=plan.entry,
                risk_usd=risk_usd,
                guard_on=guard_on,
                risk_profile_kind=kind,
                opened_at=now,
                mode="PAPER" if a.is_sim else "LIVE",
                trade_ref=t.trade_id,
                profile=sig.profile,
                legs=[{"name": x.name, "qty": x.qty, "tp": str(x.take_profit)} for x in t.legs],
            )
        )
        for leg in t.legs:
            if not leg.bracket_id:
                continue  # never placed
            s.add(
                Order(
                    account_id=a.id,
                    signal_id=sig.id,
                    broker_order_id=leg.bracket_id,
                    kind="bracket",
                    side="BUY" if plan.direction is Direction.LONG else "SELL",
                    qty=leg.qty,
                    price=plan.entry,
                    status="WORKING",
                    source="MANUAL" if sig.profile == "MANUAL" else "AUTO" if actor == "automation" else "SEMI",
                )
            )

    # ---------- fills / prices ----------
    def bar_feed_ok(self, symbol: str, tf: str, now: datetime) -> bool:
        """Fills, stops and trade management use only the FINEST live price feed of a symbol (D37): a 5-minute bar
        holds prices from before a 1-minute trade was placed (false fills/stops), so it is ignored while 1-minute
        bars keep arriving (seen within the last 3 of their bars). A missing finer feed falls back to the slower one."""
        try:
            m = int(tf)
        except ValueError:
            return True
        seen = self._bar_feeds.setdefault(symbol, {})
        seen[m] = now
        return not any(t < m and 0 <= (now - last).total_seconds() <= 3 * 60 * t for t, last in seen.items())

    async def on_bar(
        self,
        symbol: str,
        o: Decimal,
        h: Decimal,
        low: Decimal,
        c: Decimal,
        at: datetime,
        bar_close_ms: int | None = None,
        tf: str = "1",
    ) -> None:
        bar = None
        if bar_close_ms is not None:  # D122: the heartbeat bar itself feeds the dynamic trail (ATR / swing)
            with contextlib.suppress(ValueError):  # an unknown timeframe string: no bar history, nothing else changes
                span = tf_minutes(tf) * 60_000
                bar = PriceBar(bar_close_ms - span, bar_close_ms, o, h, low, c)
        async with self.lock:
            with self.sessionmaker() as s:
                for f in self.adapter.on_bar(symbol, o, h, low, c, at):
                    await self._handle_events(s, await self.om.on_fill(f))
                await self._handle_events(s, await self.om.expire_unfilled(self.clock.now()))
                await self._handle_events(s, await self.om.on_bar(symbol, h, low, c, bar))
                await self._retry_strategy_exits(s)
                await self._scalp_time_stop(s, symbol)
                await self._monitor(s)
                self._commit(s)

    async def process_live_fills(self) -> None:
        """Live (CrossTrade) fills arrive from a background poller; apply them promptly (stop→BE moves etc.)."""
        fills = self.adapter.drain_live()
        if not fills:
            return
        async with self.lock:
            with self.sessionmaker() as s:
                for f in fills:
                    await self._handle_events(s, await self.om.on_fill(f))
                await self._monitor(s)
                self._commit(s)

    async def _scalp_time_stop(self, s: Session, symbol: str) -> None:
        """Scalp mode: a quick trade still open after max_hold_s is closed at market (app exit, ≥ 6 s hold)."""
        r = self.rules.rules
        if not r.scalp_mode.enabled:
            return
        now = self.clock.now()
        for t in [t for t in self.om.trades.values() if t.symbol == symbol and t.plan.mode == "ONE_TO_ONE"]:
            if t.partial_done:
                continue  # first half banked: the runner may run (stop at breakeven, trailing) until the day's close
            held = (now - t.opened_at).total_seconds()
            if held >= max(float(r.scalp_mode.max_hold_s), float(r.behavior.min_hold_seconds)):
                a = s.execute(select(Account).where(Account.broker_account_id == t.account)).scalar_one_or_none()
                if a is not None:
                    await self._flatten_account(s, a, "SCALP_TIME")

    async def _handle_events(self, s: Session, events: list[Event]) -> None:
        for e in events:
            if e.kind == "CLOSED":
                reason = e.detail
                if e.detail == "FLATTEN":
                    reason = e.trade.closing or self._flatten_reason or e.detail
                self._close_trade(s, e.trade, reason)
            elif e.kind == "STOP_MOVED":  # every stop move is logged (D85: which rule chose the level)
                audit.record(s, self.clock, "automation", "trade.stop_moved", e.trade.account, {"detail": e.detail})
            elif e.kind == "PAUSE":
                self._pause(s, e.trade.account, e.detail)
            elif e.kind == "CANCELLED":
                self._drop_unfilled_trade(s, e.trade, e.detail)
            elif e.kind == "ENTRY_TRIMMED":
                row = self._trade_row(s, e.trade.trade_id)
                if row is not None:
                    row.qty = e.trade.qty
                    row.legs = [{"name": x.name, "qty": x.qty, "tp": str(x.take_profit)} for x in e.trade.legs]
                self.notify("warn", "Unfilled limit leg cancelled", f"{e.trade.account}: {e.detail}")
            elif e.kind == "FLATTENED":
                self.notify("warn", "Position flattened", f"{e.trade.account}: {e.detail}")
                e.trade.closing = e.trade.closing or e.detail
                # P&L is booked when the exit fill arrives (immediately on the simulator, later on CrossTrade)
                for f in self.adapter.drain_fills():
                    await self._handle_events(s, await self.om.on_fill(f))

    def _acct(self, s: Session, ext: str) -> Account | None:
        return s.execute(select(Account).where(Account.broker_account_id == ext)).scalar_one_or_none()

    def _drop_unfilled_trade(self, s: Session, t: OpenTrade, reason: str) -> None:
        """A limit entry that never filled (timeout / flatten / news): NOT a trade — no P&L, no win/loss, no count
        towards max_trades_per_day. The persisted row is removed and the audit log keeps the record."""
        a = self._acct(s, t.account)
        row = self._trade_row(s, t.trade_id)
        if row is not None:
            s.delete(row)
        for o in s.execute(
            select(Order).where(Order.broker_order_id.in_([x.bracket_id for x in t.legs if x.bracket_id]))
        ).scalars():
            o.status = "CANCELLED"
        if a is not None:
            ds = st.day_stats(s, a, self.clock.now())
            ds.trades = max(0, ds.trades - 1)
            audit.record(
                s, self.clock, "automation", "trade.limit_cancelled", t.account, {"ref": t.trade_id, "reason": reason}
            )
            self.notify("info", "Limit entry cancelled", f"{a.label}: {reason}")
        self._pending_exits.pop(t.trade_id, None)
        s.flush()
        self._mark_signal_closed(s, t.signal_id, reason)

    async def limit_timeout_check(self) -> None:
        """Wall-clock watchdog step: cancel limit entries past their timeout (also retries a failed cancel)."""
        if not any(t.pending_until is not None for t in self.om.trades.values()):
            return
        async with self.lock:
            with self.sessionmaker() as s:
                await self._handle_events(s, await self.om.expire_unfilled(self.clock.now()))
                self._commit(s)

    def _close_trade(self, s: Session, t: OpenTrade, reason: str) -> None:
        row = self._trade_row(s, t.trade_id, t.account)
        a = self._acct(s, t.account)
        if row is None or a is None or row.closed_at is not None:
            return
        pnl = money(t.pnl())
        risk = t.risk_usd()
        row.pnl_usd, row.closed_at, row.exit_reason = pnl, self.clock.now(), reason
        row.exit = next((x.exit for x in reversed(t.legs) if x.exit is not None), None)
        row.net_r = (pnl / risk).quantize(Decimal("0.01")) if risk else Decimal(0)
        fees = sum((x.fee for x in t.legs), Decimal(0))
        row.gross_r = ((pnl + fees) / risk).quantize(Decimal("0.01")) if risk else Decimal(0)
        row.resolution = {"TP": "TP", "STOP": "STOP"}.get(reason, reason[:16])
        ds = st.day_stats(s, a, self.clock.now())
        ds.day_profit += pnl
        ds.day_net_r += row.net_r
        if pnl < 0:
            ds.losses += 1
            ds.consecutive_losses += 1
            ds.win_streak = 0
        else:
            ds.consecutive_losses = 0
            ds.win_streak += 1
        if self.om.trades.get(t.trade_id):
            del self.om.trades[t.trade_id]
        self._pending_exits.pop(t.trade_id, None)
        self._exit_alerted.discard(t.trade_id)
        s.flush()
        self._mark_signal_closed(s, t.signal_id, reason)
        if reason == PROFIT_LOCK_REASON:
            self._mark_lock_exit(s, t.signal_id)
        self.notify("info", "Trade closed", f"{a.label}: {pnl} ({row.net_r}R)", "trade")
        self.publish("position.updated", {"account": a.id})
        self.publish("account.updated", {"id": a.id})
        lock_r = self.rules.rules.internal.day_lockin_r
        if ds.day_net_r >= lock_r and ds.day_net_r - row.net_r < lock_r:  # crossed the lock-in this trade
            self.publish("risk.day_lockin", {"account": a.id, "day_net_r": str(ds.day_net_r), "lockin_r": str(lock_r)})

    def _pause(self, s: Session, ext: str, reason: str) -> None:
        a = self._acct(s, ext)
        if a is None:
            return
        a.paused_reason, a.armed = reason, False
        audit.record(s, self.clock, "automation", "account.paused", ext, {"reason": reason})
        self.notify("error", "Account paused", f"{a.label}: {reason}", "pause")
        self.publish("risk.alert", {"account": a.id, "reason": reason})
        self.publish("account.updated", {"id": a.id})

    async def _monitor(self, s: Session) -> None:
        """Every price update: intraday MLL, kill distance, DLL breach (§9)."""
        r = self.rules.rules
        for a in s.execute(select(Account)).scalars():
            if a.broker_account_id not in self.adapter.accounts:
                continue
            try:
                bal, opnl = await self._equity(a)
            except BrokerError as e:  # no P&L → cannot watch MLL/DLL → block entries on this account (§1.8)
                if a.paused_reason is None:
                    self._pause(s, a.broker_account_id, "NO_LIVE_PNL")
                self.notify("error", "No live P&L", f"{a.label}: {e}")
                continue
            equity = bal + opnl
            m = self._mll_state(a)
            update_mll(m, equity)  # trails intraday accounts only; EOD accounts move at the EOD update
            a.mll, a.mll_peak, a.mll_locked = m.mll, m.peak, m.locked
            day = st.day_state(s, a, opnl, self.clock.now())
            if equity - m.mll <= r.internal.kill_switch_mll_distance and (opnl != 0 or equity <= m.mll):
                if a.paused_reason in ("KILL_SWITCH", "MLL_BREACH") and not await self._exposed(a):
                    continue  # already killed and flat: the watchdog must not re-fire every tick
                await self._flatten_account(s, a, "KILL_SWITCH")
                self._pause(s, a.broker_account_id, "KILL_SWITCH" if equity > m.mll else "MLL_BREACH")
                continue
            dll = st.dll_for(r, a)
            if dll is not None and dll_remaining(dll, day.today_pnl, day.today_peak_pnl) <= 0 and opnl != 0:
                await self._flatten_account(s, a, "DLL_LIMIT")
                st.day_stats(s, a, self.clock.now()).stopped_reason = "DLL_LIMIT"
                continue
            if opnl > 0 and any(t.account == a.broker_account_id and t.strategy for t in self.om.trades.values()):
                # N6: fixed-size strategy trades are not fitted to the consistency cap before entry, so the day stop is
                # enforced here, live: flatten once today's realised + open profit reaches it (protective, never waits)
                clim = st.consistency(s, a, r)
                fcfg = effective_fast_cfg(a.stage, self.rules.fast_eval_on, r.fast_eval)
                if clim is not None and fcfg is not None:
                    clim = harvest_limits(clim, fcfg, r.eval.profit_target)
                if clim is not None and live_day_stop_hit(day.today_profit_for_consistency, opnl, clim):
                    await self._flatten_account(s, a, "CONSISTENCY_DAY_STOP")
                    st.day_stats(s, a, self.clock.now()).stopped_reason = "CONSISTENCY_DAY_STOP"
                    self.notify("warn", "Consistency day stop", f"{a.label}: strategy trades flattened at the day stop")

    async def reconcile(self, s: Session) -> list[Any]:
        """Broker vs our open trades; mismatching accounts are paused (§13)."""
        from app.monitor.reconcile import reconcile

        exp: dict[tuple[str, str], int] = {}
        for t in self.om.trades.values():
            q = sum(x.qty for x in t.legs if not x.closed and x.entry is not None)
            exp[(t.account, t.symbol)] = exp.get((t.account, t.symbol), 0) + q * t.d.sign
        act: dict[tuple[str, str], int] = {}
        for a in s.execute(select(Account)).scalars():
            if a.broker_account_id in self.adapter.accounts:
                for p in await self.adapter.get_positions(a.broker_account_id):
                    act[(a.broker_account_id, p.symbol)] = p.qty
        bad = reconcile(exp, act)
        for m in bad:
            self._pause(s, m.account, "POSITION_MISMATCH")
        return bad

    async def eod_all(self) -> int:
        """Once per session after the hard flat: EOD-trailing accounts trail their MLL on the settled balance (§10).
        Intraday accounts already trail on every P&L update. Returns how many accounts were updated."""
        n = 0
        async with self.lock:
            with self.sessionmaker() as s:
                for a in s.execute(select(Account)).scalars():
                    if a.drawdown_type != "eod" or a.broker_account_id not in self.adapter.accounts:
                        continue
                    try:
                        bal = await self.adapter.get_balance(a.broker_account_id)
                    except BrokerError as e:
                        self.notify("error", "EOD drawdown update failed", f"{a.label}: {e}")
                        continue
                    before = a.mll
                    self.eod_update(s, a, bal)
                    audit.record(
                        s,
                        self.clock,
                        "automation",
                        "mll.eod",
                        a.broker_account_id,
                        {"balance": str(bal), "mll_before": str(before), "mll": str(a.mll), "locked": a.mll_locked},
                    )
                    n += 1
                self._commit(s)
        return n

    def eod_update(self, s: Session, a: Account, settled_balance: Decimal) -> None:
        m = self._mll_state(a)
        update_mll(m, settled_balance, eod=True)
        a.mll, a.mll_peak, a.mll_locked = m.mll, m.peak, m.locked

    # ---------- flatten / kill ----------
    async def _exposed(self, a: Account) -> bool:
        """Open exposure on the account: a tracked trade not already closing, or any broker position (unknown → yes)."""
        if any(t.account == a.broker_account_id and not t.closing for t in self.om.trades.values()):
            return True
        try:
            return bool(await self.adapter.get_positions(a.broker_account_id))
        except BrokerError:
            return True

    async def _cancel_entries(self, s: Session, ext: str, reason: str) -> bool:
        """Cancel the working (unfilled) limit entries of an account before it is flattened."""
        ok = True
        for t in [t for t in self.om.trades.values() if t.account == ext and self.om.has_unfilled(t)]:
            events = await self.om.cancel_unfilled(t, reason)
            ok = ok and any(e.kind in ("CANCELLED", "ENTRY_TRIMMED") for e in events)
            await self._handle_events(s, events)
        return ok

    async def _flatten_account(self, s: Session, a: Account, reason: str) -> bool:
        """Flatten via the broker. Tracked trades stay 'closing' until their exit fill books the real P&L (instant on
        the simulator, later on CrossTrade). Returns False when the broker call failed (caller retries/escalates)."""
        ext = a.broker_account_id
        self._flatten_reason = reason
        cancel_ok = await self._cancel_entries(s, ext, reason)
        try:
            await self.adapter.flatten(ext)
        except BrokerError as e:
            self._flatten_reason = None
            if ext not in self._flatten_alerted:
                self._flatten_alerted.add(ext)
                self.notify("error", "FLATTEN FAILED — act manually in Tradovate", f"{a.label}: {e}")
            return False
        if not cancel_ok:
            self._flatten_reason = None
            if ext not in self._flatten_alerted:
                self._flatten_alerted.add(ext)
                self.notify("error", "ENTRY CANCEL FAILED — act manually in Tradovate", a.label)
            return False  # a working entry is still out there: the watchdog retries
        self._flatten_alerted.discard(ext)
        now = self.clock.now()
        for t in [t for t in self.om.trades.values() if t.account == ext]:
            t.closing = t.closing or reason
            t.closing_since = t.closing_since or now
        for f in self.adapter.drain_fills():
            await self._handle_events(s, await self.om.on_fill(f))
        for t in [t for t in self.om.trades.values() if t.account == ext]:
            if not any(x.entry is not None for x in t.legs) and ext not in self.adapter.live_accounts:
                self._close_trade(s, t, reason)  # simulator: never filled → cancelled, nothing to wait for
        self._flatten_reason = None
        audit.record(s, self.clock, "automation", "account.flattened", ext, {"reason": reason})
        return True

    async def flatten(self, account_id: int, actor: str, reason: str = "MANUAL_FLATTEN") -> None:
        async with self.lock:
            with self.sessionmaker() as s:
                a = s.get(Account, account_id)
                if a is None:
                    raise LookupError("no such account")
                await self._flatten_account(s, a, reason)
                audit.record(s, self.clock, actor, "account.flatten", a.broker_account_id, {"reason": reason})
                self._commit(s)

    async def flatten_all(self, actor: str, reason: str = "FLATTEN_ALL") -> None:
        async with self.lock:
            with self.sessionmaker() as s:
                for a in s.execute(select(Account)).scalars():
                    if a.broker_account_id in self.adapter.accounts:
                        await self._flatten_account(s, a, reason)
                audit.record(s, self.clock, actor, "flatten_all", "", {"reason": reason})
                self._commit(s)

    async def kill_switch(self, actor: str) -> None:
        """Flatten + cancel + disarm all + automation OFF (§13). Never auto-resumes."""
        await self.flatten_all(actor, "KILL_SWITCH")
        with self.sessionmaker() as s:
            for a in s.execute(select(Account)).scalars():
                a.armed, a.paused_reason = False, "KILL_SWITCH"
            self.mode = "OFF"
            self.approvals.clear()
            st.set_setting(s, "automation.mode", "OFF", self.clock.now())
            audit.record(s, self.clock, actor, "kill_switch", "", {})
            self._commit(s)
        self.notify("error", "KILL SWITCH", f"by {actor}: all flat, all disarmed, automation OFF", "kill_switch")
        self.publish("risk.alert", {"kill_switch": True, "by": actor})
        self.publish("automation.changed", {"mode": "OFF", "kill_switch": True})

    async def flat_time_check(self) -> str | None:
        """16:40 auto-flatten, then the 16:44 hard flat (ET) until the reopen. Based on BROKER positions as well as
        tracked trades (restarts / untracked positions must flatten too). Called every watchdog tick, so a failed
        flatten is retried; failing at the hard flat pauses the account (never auto-resumes) + banner (§1.8)."""
        r = self.rules.rules
        t = to_et(self.clock.now()).time()
        if not parse_hhmm(r.internal.auto_flatten) <= t < parse_hhmm(r.session.reopen):
            return None
        hard = t >= parse_hhmm(r.internal.hard_flat)
        reason = "HARD_FLAT" if hard else "FLAT_TIME"
        hit = None
        async with self.lock:
            with self.sessionmaker() as s:
                for a in s.execute(select(Account)).scalars():
                    if a.broker_account_id not in self.adapter.accounts or not await self._exposed(a):
                        continue
                    hit = reason
                    if not await self._flatten_account(s, a, reason) and hard and a.paused_reason != "FLATTEN_FAILED":
                        self._pause(s, a.broker_account_id, "FLATTEN_FAILED")
                self._commit(s)
        return hit

    async def news_check(self, events: list[Any] | None) -> str | None:
        """Flatten open exposure before high-impact news (§15): every account news_flatten_before_min ahead; accounts
        whose firm treats news as a hard breach (funded/live, eval when not allowed) stay flat until
        breach_min_after."""
        if not events:
            return None
        r, now = self.rules.rules, self.clock.now()
        hit = None
        async with self.lock:
            with self.sessionmaker() as s:
                for a in s.execute(select(Account)).scalars():
                    if a.broker_account_id not in self.adapter.accounts:
                        continue
                    sr = stage_rules(r, a.stage, a.drawdown_type, a.dll_enabled)
                    stage_cfg = r.funded if a.stage != "EVAL" else r.eval
                    before = max(r.internal.news_flatten_before_min, stage_cfg.news_breach_min_before)
                    after = stage_cfg.news_breach_min_after if sr.news_hard_breach else 0
                    ev = news_flatten_due(now, events, before, after)
                    if ev is not None and await self._exposed(a):
                        if await self._flatten_account(s, a, "NEWS"):
                            self.notify("warn", "Flattened for news", f"{a.label}: {ev.title}")
                        hit = "NEWS"
                self._commit(s)
        return hit

    async def monitor_accounts(self) -> None:
        """Wall-clock MLL / kill-switch / DLL monitor (no new bar needed)."""
        async with self.lock:
            with self.sessionmaker() as s:
                await self._monitor(s)
                self._commit(s)

    async def retry_closing(self) -> None:
        """Trades waiting in 'closing' (flatten requested, exit fill not seen): still in the market → flatten again;
        flat at the broker but no fill after CLOSE_GRACE_S → close with an error alert (P&L unverified)."""
        now = self.clock.now()
        async with self.lock:
            with self.sessionmaker() as s:
                for t in [t for t in self.om.trades.values() if t.closing]:
                    a = self._acct(s, t.account)
                    reason = t.closing
                    if a is None or reason is None:
                        continue
                    t.closing_since = t.closing_since or now
                    try:
                        pos = await self.adapter.get_positions(t.account)
                    except BrokerError:
                        continue
                    if any(p.symbol == t.symbol and p.qty != 0 for p in pos):
                        await self._flatten_account(s, a, reason)
                    elif (now - t.closing_since).total_seconds() >= CLOSE_GRACE_S:
                        self.notify("error", "Exit fill missing — P&L unverified", f"{a.label}: {reason}")
                        self._close_trade(s, t, reason)
                self._commit(s)

    # ---------- restart recovery (session 14, item 1) ----------
    async def recover_open_trades(self, only: set[int] | None = None) -> None:
        """Startup (and after the live adapter attached): rebuild order management from the open Trade rows + broker
        positions. Paper: the in-memory simulator is re-seeded from the snapshot. Live: the snapshot must match the
        broker position; anything unmatched is flattened, the account paused and a banner raised (never silent)."""
        async with self.lock:
            with self.sessionmaker() as s:
                await self._recover(s, only)
                self._commit(s)

    async def retry_recovery(self) -> None:
        if self._recovery_pending:
            await self.recover_open_trades(set(self._recovery_pending))

    async def _recover(self, s: Session, only: set[int] | None) -> None:
        rows = list(s.execute(select(Trade).where(Trade.closed_at.is_(None))).scalars())
        restored = 0
        for a in s.execute(select(Account)).scalars():
            if (only is not None and a.id not in only) or a.broker_account_id not in self.adapter.accounts:
                continue
            ext = a.broker_account_id
            tracked: list[OpenTrade] = []
            for row in (r for r in rows if r.account_id == a.id):
                t = self._load_snapshot(row)
                if t is None:  # no usable snapshot
                    if a.is_sim:
                        row.closed_at, row.exit_reason, row.pnl_usd = self.clock.now(), "SIM_RESTART", Decimal(0)
                    else:
                        row.closed_at, row.exit_reason, row.pnl_usd = self.clock.now(), "RESTART_UNTRACKED", Decimal(0)
                        self.notify(
                            "error", "Restart: trade P&L unverified", f"{a.label}: {row.symbol} {row.trade_ref}"
                        )
                    continue
                tracked.append(t)
            try:
                if a.is_sim:
                    for t in tracked:
                        self._restore_sim(ext, t)
                        self.om.restore(t)
                        restored += 1
                    self._recovery_pending.discard(a.id)
                    continue
                restored += await self._recover_live(s, a, tracked)
                self._recovery_pending.discard(a.id)
            except BrokerError as e:
                for t in tracked:  # keep managing what we know while the broker cannot be read
                    self.om.restore(t)
                if a.id not in self._recovery_pending:
                    self._recovery_pending.add(a.id)
                    self._pause(s, ext, "RESTART_UNVERIFIED")
                    self.notify(
                        "error",
                        "Restart recovery could not read the broker",
                        f"{a.label}: {e}. Entries are blocked; the app retries every minute.",
                        "restart",
                    )
        if restored:
            self.notify("info", "Restart recovery", f"{restored} open trade(s) put back under management", "restart")

    @staticmethod
    def _load_snapshot(row: Trade) -> OpenTrade | None:
        if not row.om_state:
            return None
        try:
            t = trade_state.load(row.om_state)
        except (KeyError, ValueError, TypeError, ArithmeticError):
            return None
        return t if t.trade_id == row.trade_ref else None

    def _restore_sim(self, ext: str, t: OpenTrade) -> None:
        from app.execution.adapters.base import BracketRequest

        side: Literal["BUY", "SELL"] = "BUY" if t.d is Direction.LONG else "SELL"
        limit = t.pending_until is not None and any(x.entry is None for x in t.legs)
        for leg in t.legs:
            if leg.closed or not leg.bracket_id:
                continue
            req = BracketRequest(
                f"{t.trade_id}-{leg.name}",
                t.symbol,
                side,
                leg.qty,
                t.plan.stop,
                leg.take_profit,
                "LIMIT" if limit and leg.entry is None else "MARKET",
                t.plan.entry if limit and leg.entry is None else None,
            )
            self.adapter.sim.restore_bracket(ext, leg.bracket_id, leg.stop_order_id, req, leg.entry, leg.stop)

    async def _recover_live(self, s: Session, a: Account, tracked: list[OpenTrade]) -> int:
        ext, now = a.broker_account_id, self.clock.now()
        positions = {p.symbol: p.qty for p in await self.adapter.get_positions(ext)}
        working = {o.order_id for o in await self.adapter.get_orders(ext)}
        bad: list[str] = []
        kept = 0
        expected: dict[str, int] = {}
        for t in tracked:
            filled = [x for x in t.legs if x.entry is not None and not x.closed]
            if not filled:  # never filled: keep only while its entry still works at the broker
                if any(x.bracket_id in working for x in t.legs):
                    self.om.restore(t)
                    kept += 1
                else:
                    row = self._trade_row(s, t.trade_id, ext)
                    if row is not None:
                        self._drop_unfilled_trade(s, t, "RESTART_ENTRY_GONE")
                continue
            expected[t.symbol] = expected.get(t.symbol, 0) + sum(x.qty for x in filled) * t.d.sign
            self.om.restore(t)
            kept += 1
        for sym in set(expected) | set(positions):
            have, want = positions.get(sym, 0), expected.get(sym, 0)
            if have == want:
                continue
            if have == 0:  # closed at the broker while we were down: exit fill unknown → closes as "unverified"
                for t in self.om.trades.values():
                    if t.account == ext and t.symbol == sym and not t.closing:
                        t.closing, t.closing_since = "RESTART_FLAT", now
                continue
            bad.append(f"{sym} broker {have} vs managed {want}")
        if bad:
            self._pause(s, ext, RESTART_UNMANAGED)
            self.notify(
                "error",
                "Restart found an unmanaged position",
                f"{a.label}: {'; '.join(bad)}. Flattened and the account is paused - check Tradovate.",
                "restart",
            )
            await self._flatten_account(s, a, RESTART_UNMANAGED)
        return kept

    # ---------- feed-loss protection (session 14, item 5) ----------
    async def feed_guard(self) -> None:
        """Position open AND no 1-minute bar for > feed_warn_min → error alert + new entries blocked; for >
        feed_flatten_min → flatten (FEED_LOST), a protective exit that never waits for the hold. Broker positions are
        the truth for "open"; the broker's own open P&L keeps feeding the MLL/DLL monitor without TradingView."""
        cfg = self.rules.rules.reliability
        if not cfg.feed_guard_enabled:
            self.feed_state.clear()
            self._exposure_since.clear()
            return
        now = self.clock.now()
        async with self.lock:
            with self.sessionmaker() as s:
                exposed = await self._exposed_by_symbol(s)
                for sym in [k for k in self._exposure_since if k not in exposed]:
                    del self._exposure_since[sym]
                    if self.feed_state.pop(sym, None):
                        self.notify("info", "Price feed is back", f"{sym}: no open position any more", "feed")
                for sym, accts in exposed.items():
                    since = self._exposure_since.setdefault(sym, self._opened_at(sym) or now)
                    last, extra = self._last_bar(s, sym)
                    ref = max(x for x in (last, since) if x is not None)
                    age = (now - ref).total_seconds() / 60
                    if age >= cfg.feed_flatten_min + extra:
                        state = "LOST"
                    elif age >= cfg.feed_warn_min + extra:
                        state = "WARN"
                    else:
                        state = ""
                    before = self.feed_state.get(sym, "")
                    if state:
                        self.feed_state[sym] = state
                    else:
                        self.feed_state.pop(sym, None)
                        if before:
                            self.notify("info", "Price feed is back", f"{sym}: bars are arriving again", "feed")
                    if state and state != before:
                        self.notify(
                            "error",
                            "Price feed lost while in a position",
                            f"{sym}: no 1-minute bar for {int(age)} min. New entries are blocked"
                            + (
                                "; flattening (FEED_LOST)."
                                if state == "LOST"
                                else f"; flattens after {cfg.feed_flatten_min} min."
                            ),
                            "feed",
                        )
                    if state == "LOST":
                        for a in accts:
                            await self._flatten_account(s, a, "FEED_LOST")
                self._commit(s)

    def _last_bar(self, s: Session, symbol: str) -> tuple[datetime | None, int]:
        """Latest price bar of the symbol: the 1-minute feed when it is alive, else the finest slower feed (extra =
        its extra minutes, so a 5-minute-only profile does not alarm between its bars)."""
        from sqlalchemy import func

        floor = self.clock.now() - timedelta(days=1)
        one = s.execute(
            select(func.max(Bar.close_time)).where(Bar.symbol == symbol, Bar.tf == "1", Bar.close_time > floor)
        ).scalar_one_or_none()
        if one is not None:
            return one, 0
        best: tuple[datetime | None, int] = (None, 0)
        for tf, at in s.execute(
            select(Bar.tf, func.max(Bar.close_time))
            .where(Bar.symbol == symbol, Bar.close_time > floor)
            .group_by(Bar.tf)
        ):
            try:
                m = tf_minutes(tf)
            except ValueError:
                continue
            if at is not None and (best[0] is None or at > best[0]):
                best = (at, m - 1)
        return best

    def _opened_at(self, symbol: str) -> datetime | None:
        """Earliest open time of the tracked trades in a symbol (the feed clock starts when the position did)."""
        times = [t.opened_at for t in self.om.trades.values() if t.symbol == symbol]
        return min(times) if times else None

    async def _exposed_by_symbol(self, s: Session) -> dict[str, list[Account]]:
        out: dict[str, list[Account]] = {}
        for a in s.execute(select(Account)).scalars():
            ext = a.broker_account_id
            if ext not in self.adapter.accounts:
                continue
            syms = {
                t.symbol
                for t in self.om.trades.values()
                if t.account == ext and any(x.entry is not None and not x.closed for x in t.legs)
            }
            with contextlib.suppress(BrokerError):  # unreadable broker: the tracked trades still count
                syms |= {p.symbol for p in await self.adapter.get_positions(ext) if p.qty != 0}
            for sym in syms:
                out.setdefault(sym, []).append(a)
        return out

    def safety_status(self, s: Session) -> dict[str, Any]:
        """Everything the UI banners need (plain-language states for session 14 safety fixes)."""
        now = self.clock.now()
        unmanaged = [
            {"account": a.label or a.broker_account_id, "reason": a.paused_reason}
            for a in s.execute(
                select(Account).where(Account.paused_reason.in_([RESTART_UNMANAGED, "RESTART_UNVERIFIED"]))
            ).scalars()
        ]
        pending: list[dict[str, Any]] = []
        for sig in s.execute(
            select(Signal).where(Signal.status == "PASS", Signal.bar_time >= now - timedelta(days=3))
        ).scalars():
            mark = (sig.features or {}).get("exit_requested")
            if mark and sig.features.get("state") == "OPEN":
                pending.append(
                    {"signal_id": sig.id, "symbol": sig.symbol, "reason": mark.get("reason"), "since": mark.get("at")}
                )
        return {
            "unmanaged": unmanaged,
            "feed": [{"symbol": k, "state": v} for k, v in self.feed_state.items()],
            "feed_delayed": [{"symbol": k, "lag_s": int(v)} for k, v in self.feed_delayed.items()],
            "pending_exits": pending,
        }

    async def watchdog_tick(self, news_events: list[Any] | None) -> None:
        """Wall-clock safety loop, independent of TradingView webhooks (a stalled feed must not stop the flatten)."""
        steps: list[tuple[str, Any]] = [
            ("flat_time", self.flat_time_check()),
            ("news", self.news_check(news_events)),
            ("monitor", self.monitor_accounts()),
            ("closing", self.retry_closing()),
            ("limit_timeout", self.limit_timeout_check()),
            ("exits", self.exit_watchdog()),
            ("feed", self.feed_guard()),
            ("recovery", self.retry_recovery()),
        ]
        for name, coro in steps:
            try:
                await coro
            except Exception as e:  # never silent (§1.8); the other checks still run
                self.notify("error", "Safety watchdog step failed", f"{name}: {type(e).__name__}")

    async def defence_check(
        self,
        symbol: str,
        high: Decimal,
        low: Decimal,
        mso: dict[str, Any] | None,
        mso_events: list[tuple[str, str, int]],
        by_profile: dict[str, tuple[dict[str, Any] | None, list[tuple[str, str, int]]]] | None = None,
    ) -> None:
        """Half-off defence: every confirmation against the trade (MSO trend flipped AND a CHoCH against since entry)
        and price ≥ adverse_half_at of the way to the stop → close one of the two brackets (once per trade)."""
        r = self.rules.rules
        if not r.internal.adverse_half_enabled or not self.om.trades or not r.indicators.mso.enabled:  # D91
            return
        now = self.clock.now()
        async with self.lock:
            with self.sessionmaker() as s:
                for t in [t for t in self.om.trades.values() if t.symbol == symbol and not t.strategy]:
                    against = "SHORT" if t.d is Direction.LONG else "LONG"
                    # D37: judge the trade with its own timeframe's MSO when that state is known
                    t_mso, t_events = (by_profile or {}).get(t.profile, (mso, mso_events))
                    trend_against = (t_mso or {}).get("trend") == ("BEAR" if against == "SHORT" else "BULL")
                    opened_ms = int(t.opened_at.timestamp() * 1000)
                    choch_against = any(e == "MSO_CHOCH" and d == against and ms >= opened_ms for e, d, ms in t_events)
                    worst = low if t.d is Direction.LONG else high
                    ev = await self.om.adverse_half(
                        t.trade_id, worst, r.internal.adverse_half_at, trend_against and choch_against, now
                    )
                    for e in ev:
                        audit.record(s, self.clock, "automation", "trade.half_off", t.account, {"detail": e.detail})
                        self.notify("warn", "Half-off defence", f"{t.symbol}: {e.detail}")
                    for f in self.adapter.drain_fills():
                        await self._handle_events(s, await self.om.on_fill(f))
                self._commit(s)

    def entries_blocked_by_time(self) -> bool:
        r = self.rules.rules
        t = to_et(self.clock.now()).time()
        return parse_hhmm(r.internal.auto_flatten) <= t < parse_hhmm(r.session.reopen)
