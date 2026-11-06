"""Automation controller (§13): modes, approvals, fan-out to accounts, trade lifecycle, kill switch, safety monitor.

Paper by default: the Sim adapter fills on the real TradingView prices. LIVE needs PAYTIENCE_ALLOW_LIVE + the
checklist (§1.5) and a verified broker adapter — until then every account is a paper account.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app import audit
from app.automation import state as st
from app.automation.account_selector import Candidate
from app.automation.account_selector import select as select_accounts
from app.automation.preflight import allowed_mode
from app.clock import Clock, parse_hhmm, to_et
from app.engine.filters import news_flatten_due
from app.engine.trade_plan import Direction, TradePlan, fee_cover_ticks
from app.execution.adapters.base import BrokerError, conservative_mode
from app.execution.adapters.router import RoutingAdapter
from app.execution.order_manager import Event, OpenTrade, OrderManager, OrphanedPosition
from app.indicators.bars import tf_minutes
from app.management.drawdown_guard import GuardCfgView, apply_guard, guard_active, min_contracts
from app.models import Account, Order, Payout, Signal, Trade, TradePlanRow
from app.phases.mll_tracker import MllState, update_mll
from app.phases.phase_engine import firm_max_micros, new_mll, stage_rules
from app.risk.checks import AccountView, TradeLimits, dll_remaining, pretrade
from app.risk.eval_mode import effective_risk_cfg, one_to_one_for
from app.risk.hedge_lock import OpenPosition, hedge_conflict
from app.risk.holder import RulesHolder
from app.risk.risk_base import money, risk_base
from app.risk.tiers import FloorRules, RiskCfg

MODES = ("OFF", "SEMI", "FULL")
APPROVAL_SECONDS = 90
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
    bus: Any = None  # app.events.EventBus: stored notifications + WS events (§19)

    # ---------- setup ----------
    def load_accounts(self) -> None:
        """Register paper accounts with the simulator (balance = start + closed P&L). Open paper trades cannot
        survive a restart (the simulator is in memory) → they are closed as SIM_RESTART and reconciled flat."""
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
                    t.closed_at, t.exit_reason, t.pnl_usd = self.clock.now(), "SIM_RESTART", Decimal(0)
            s.commit()

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
            s.commit()
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
        if not one_to_one:
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
        positions = await self.open_positions(s)
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
        )
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
            consistency=st.consistency(s, a, r),
            lim=lim,
            hedge_conflict=hedge_conflict(r, sig.symbol, plan.direction.value, positions) is not None,
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
                r.entry.mode,
                self._limit_deadline(sig, now),
            )
            t.profile = sig.profile
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

    async def on_bar(self, symbol: str, o: Decimal, h: Decimal, low: Decimal, c: Decimal, at: datetime) -> None:
        async with self.lock:
            with self.sessionmaker() as s:
                for f in self.adapter.on_bar(symbol, o, h, low, c, at):
                    await self._handle_events(s, await self.om.on_fill(f))
                await self._handle_events(s, await self.om.expire_unfilled(self.clock.now()))
                await self._handle_events(s, await self.om.on_bar(symbol, h, low))
                await self._scalp_time_stop(s, symbol)
                await self._monitor(s)
                s.commit()

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
                s.commit()

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
            elif e.kind == "PAUSE":
                self._pause(s, e.trade.account, e.detail)
            elif e.kind == "CANCELLED":
                self._drop_unfilled_trade(s, e.trade, e.detail)
            elif e.kind == "ENTRY_TRIMMED":
                row = s.execute(select(Trade).where(Trade.trade_ref == e.trade.trade_id)).scalar_one_or_none()
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
        row = s.execute(select(Trade).where(Trade.trade_ref == t.trade_id)).scalar_one_or_none()
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

    async def limit_timeout_check(self) -> None:
        """Wall-clock watchdog step: cancel limit entries past their timeout (also retries a failed cancel)."""
        if not any(t.pending_until is not None for t in self.om.trades.values()):
            return
        async with self.lock:
            with self.sessionmaker() as s:
                await self._handle_events(s, await self.om.expire_unfilled(self.clock.now()))
                s.commit()

    def _close_trade(self, s: Session, t: OpenTrade, reason: str) -> None:
        row = s.execute(select(Trade).where(Trade.trade_ref == t.trade_id)).scalar_one_or_none()
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
                s.commit()
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
                s.commit()

    async def flatten_all(self, actor: str, reason: str = "FLATTEN_ALL") -> None:
        async with self.lock:
            with self.sessionmaker() as s:
                for a in s.execute(select(Account)).scalars():
                    if a.broker_account_id in self.adapter.accounts:
                        await self._flatten_account(s, a, reason)
                audit.record(s, self.clock, actor, "flatten_all", "", {"reason": reason})
                s.commit()

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
            s.commit()
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
                s.commit()
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
                s.commit()
        return hit

    async def monitor_accounts(self) -> None:
        """Wall-clock MLL / kill-switch / DLL monitor (no new bar needed)."""
        async with self.lock:
            with self.sessionmaker() as s:
                await self._monitor(s)
                s.commit()

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
                s.commit()

    async def watchdog_tick(self, news_events: list[Any] | None) -> None:
        """Wall-clock safety loop, independent of TradingView webhooks (a stalled feed must not stop the flatten)."""
        steps: list[tuple[str, Any]] = [
            ("flat_time", self.flat_time_check()),
            ("news", self.news_check(news_events)),
            ("monitor", self.monitor_accounts()),
            ("closing", self.retry_closing()),
            ("limit_timeout", self.limit_timeout_check()),
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
        if not r.internal.adverse_half_enabled or not self.om.trades:
            return
        now = self.clock.now()
        async with self.lock:
            with self.sessionmaker() as s:
                for t in [t for t in self.om.trades.values() if t.symbol == symbol]:
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
                s.commit()

    def entries_blocked_by_time(self) -> bool:
        r = self.rules.rules
        t = to_et(self.clock.now()).time()
        return parse_hhmm(r.internal.auto_flatten) <= t < parse_hhmm(r.session.reopen)
