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
from app.engine.trade_plan import Direction, TradePlan, fee_cover_ticks
from app.execution.adapters.base import BrokerError, conservative_mode
from app.execution.adapters.router import RoutingAdapter
from app.execution.order_manager import Event, OpenTrade, OrderManager
from app.management.drawdown_guard import GuardCfgView, apply_guard, guard_active, min_contracts
from app.models import Account, Order, Signal, Trade, TradePlanRow
from app.phases.mll_tracker import MllState, update_mll
from app.phases.phase_engine import new_mll, stage_rules
from app.risk.checks import AccountView, TradeLimits, dll_remaining, pretrade
from app.risk.eval_mode import effective_risk_cfg, one_to_one_for
from app.risk.hedge_lock import OpenPosition, hedge_conflict
from app.risk.holder import RulesHolder
from app.risk.risk_base import money, risk_base
from app.risk.tiers import FloorRules, RiskCfg

MODES = ("OFF", "SEMI", "FULL")
APPROVAL_SECONDS = 90


@dataclass
class Approval:
    signal_id: int
    created: datetime
    expires: datetime


@dataclass
class AccountResult:
    account_id: int
    ok: bool
    reason: str | None
    contracts: int = 0
    trade_ref: str | None = None
    checks: list[dict[str, Any]] = field(default_factory=list)


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
                self.adapter.add_account(a.broker_account_id, (a.starting_balance or Decimal(0)) + closed)
                for t in s.execute(select(Trade).where(Trade.account_id == a.id, Trade.closed_at.is_(None))).scalars():
                    t.closed_at, t.exit_reason, t.pnl_usd = self.clock.now(), "SIM_RESTART", Decimal(0)
            s.commit()

    def notify(self, level: str, title: str, detail: str = "") -> None:
        self.notices.append({"level": level, "title": title, "detail": detail, "at": self.clock.now().isoformat()})
        del self.notices[:-50]

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
        if self.mode == "SEMI":
            now = self.clock.now()
            self.approvals[signal_id] = Approval(signal_id, now, now + timedelta(seconds=APPROVAL_SECONDS))
            return "APPROVAL"
        return "EXECUTE"

    def expire_approvals(self) -> list[int]:
        now = self.clock.now()
        gone = [k for k, v in self.approvals.items() if v.expires <= now]
        for k in gone:
            del self.approvals[k]
        return gone

    def _plan(self, s: Session, sig: Signal) -> TradePlan | None:
        r = self.rules.rules
        any_1to1 = r.one_to_one_mode.enabled or (self.rules.eval_mode_on and r.eval_mode.one_to_one)
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
            self.approvals.pop(signal_id, None)
            accts = list(s.execute(select(Account)).scalars())
            any_live = any(a.stage == "LIVE" and not a.is_sim for a in accts)
            cands = [
                Candidate(a.id, a.priority, a.selected, a.armed, a.paused_reason is not None, a.stage, a.is_sim)
                for a in accts
                if only is None or a.id in only
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
                a.stage, a.eval_mode, self.rules.eval_mode_on, r.one_to_one_mode.enabled, r.eval_mode.one_to_one
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
            any(p.account == a.broker_account_id for p in positions),
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
            r.max_contracts.micros,
            r.internal.internal_max_micros,
            min_contracts(guard_on, r.drawdown_guard.min_contracts_on, r.drawdown_guard.min_contracts_off),
            r.internal.dll_safety_margin,
            r.internal.pause_below_risk_base,
            r.internal.kill_switch_mll_distance,
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
            r.trade_plan.rr_max,
            inst.stop_buffer_ticks or r.trade_plan.stop_buffer_ticks,
            inst.min_stop_ticks or r.trade_plan.min_stop_ticks,
        )
        try:
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
            )
        except BrokerError as e:
            a.paused_reason, a.armed = "ORDER_REJECTS", False
            self.notify("error", "Order failed — account paused", f"{a.label}: {e}")
            return AccountResult(a.id, False, "ORDER_FAILED", checks=pt.checks)
        s.add(
            Trade(
                account_id=a.id,
                signal_id=sig.id,
                symbol=sig.symbol,
                direction=plan.direction.value,
                qty=pt.contracts,
                entry=plan.entry,
                risk_usd=pt.risk_usd or Decimal(0),
                guard_on=guard_on,
                risk_profile_kind=rcfg.kind,
                opened_at=now,
                mode="PAPER" if a.is_sim else "LIVE",
                trade_ref=t.trade_id,
                profile=sig.profile,
                legs=[{"name": x.name, "qty": x.qty, "tp": str(x.take_profit)} for x in t.legs],
            )
        )
        for leg in t.legs:
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
                    source="AUTO" if actor == "automation" else "SEMI",
                )
            )
        st.day_stats(s, a, now).trades += 1
        a.last_trade_at = now
        for f in self.adapter.drain_fills():
            await self._handle_events(s, await self.om.on_fill(f))
        return AccountResult(a.id, True, None, pt.contracts, t.trade_id, pt.checks)

    # ---------- fills / prices ----------
    async def on_bar(self, symbol: str, o: Decimal, h: Decimal, low: Decimal, c: Decimal, at: datetime) -> None:
        async with self.lock:
            with self.sessionmaker() as s:
                for f in self.adapter.on_bar(symbol, o, h, low, c, at):
                    await self._handle_events(s, await self.om.on_fill(f))
                await self._handle_events(s, await self.om.on_bar(symbol, h, low))
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

    async def _handle_events(self, s: Session, events: list[Event]) -> None:
        for e in events:
            if e.kind == "CLOSED":
                reason = self._flatten_reason if e.detail == "FLATTEN" and self._flatten_reason else e.detail
                self._close_trade(s, e.trade, reason)
            elif e.kind == "PAUSE":
                self._pause(s, e.trade.account, e.detail)
            elif e.kind == "FLATTENED":
                self.notify("warn", "Position flattened", f"{e.trade.account}: {e.detail}")
                self._close_trade(s, e.trade, e.detail)

    def _acct(self, s: Session, ext: str) -> Account | None:
        return s.execute(select(Account).where(Account.broker_account_id == ext)).scalar_one_or_none()

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
        self.notify("info", "Trade closed", f"{a.label}: {pnl} ({row.net_r}R)")

    def _pause(self, s: Session, ext: str, reason: str) -> None:
        a = self._acct(s, ext)
        if a is None:
            return
        a.paused_reason, a.armed = reason, False
        audit.record(s, self.clock, "automation", "account.paused", ext, {"reason": reason})
        self.notify("error", "Account paused", f"{a.label}: {reason}")

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

    def eod_update(self, s: Session, a: Account, settled_balance: Decimal) -> None:
        m = self._mll_state(a)
        update_mll(m, settled_balance, eod=True)
        a.mll, a.mll_peak, a.mll_locked = m.mll, m.peak, m.locked

    # ---------- flatten / kill ----------
    async def _flatten_account(self, s: Session, a: Account, reason: str) -> None:
        self._flatten_reason = reason
        try:
            await self.adapter.flatten(a.broker_account_id)
        except BrokerError as e:
            self._flatten_reason = None
            self.notify("error", "FLATTEN FAILED — act manually in Tradovate", f"{a.label}: {e}")
            return
        for f in self.adapter.drain_fills():
            await self._handle_events(s, await self.om.on_fill(f))
        for t in [t for t in self.om.trades.values() if t.account == a.broker_account_id]:
            self._close_trade(s, t, reason)
        self._flatten_reason = None
        audit.record(s, self.clock, "automation", "account.flattened", a.broker_account_id, {"reason": reason})

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
        self.notify("error", "KILL SWITCH", f"by {actor}: all flat, all disarmed, automation OFF")

    async def flat_time_check(self) -> str | None:
        """16:40 auto-flatten and 16:44 hard flat (ET); entries are blocked from 16:40 until the 18:00 reopen."""
        r = self.rules.rules
        t = to_et(self.clock.now()).time()
        if parse_hhmm(r.internal.auto_flatten) <= t < parse_hhmm(r.session.reopen) and self.om.trades:
            await self.flatten_all("automation", "FLAT_TIME")
            return "FLAT_TIME"
        return None

    def entries_blocked_by_time(self) -> bool:
        r = self.rules.rules
        t = to_et(self.clock.now()).time()
        return parse_hhmm(r.internal.auto_flatten) <= t < parse_hhmm(r.session.reopen)
