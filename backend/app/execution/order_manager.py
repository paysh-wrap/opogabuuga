"""Order manager: turns an approved plan into bracket orders and manages them until flat (§7, §8, D7, D8).

Safety rules enforced here:
- every leg is a full bracket (stop + take-profit), never a naked entry;
- if any leg fails to place, the account is flattened and paused (no half-protected position);
- a market fill is re-checked against the 2–3R window; outside it → flatten (RR_INVALID_AFTER_FILL);
- a failed stop modification → flatten + pause (§8), never left at the old stop silently.
"""

from __future__ import annotations

import contextlib
import itertools
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.engine.trade_plan import Direction, Skip, TradePlan, rebuild_after_fill, round_to_tick
from app.execution.adapters.base import BracketRequest, BrokerAdapter, BrokerError, Fill, Side
from app.management.drawdown_guard import ratchet, runner_stop, split_legs
from app.management.exits import adverse_half_due, early_exit_allowed, exit_allowed_now


@dataclass
class Leg:
    name: str  # ONLY | A | B
    qty: int
    take_profit: Decimal
    bracket_id: str = ""
    stop_order_id: str = ""
    stop: Decimal = Decimal(0)
    entry: Decimal | None = None
    exit: Decimal | None = None
    fee: Decimal = Decimal(0)
    closed: bool = False


@dataclass
class OpenTrade:
    trade_id: str
    account: str
    symbol: str
    plan: TradePlan
    guard_on: bool
    tick: Decimal
    tick_value: Decimal
    opened_at: datetime
    legs: list[Leg]
    rr_window: tuple[Decimal, Decimal, Decimal, Decimal, int, int]  # invalid, t2, rr_min, rr_max, buffer, min_stop
    best: Decimal | None = None
    partial_done: bool = False
    locked: bool = False
    half_used: bool = False
    runner_trail: Decimal | None = None  # scalp runner: trail distance in R after the first half is banked

    @property
    def d(self) -> Direction:
        return self.plan.direction

    @property
    def qty(self) -> int:
        return sum(leg.qty for leg in self.legs)

    @property
    def closed(self) -> bool:
        return all(leg.closed for leg in self.legs)

    def pnl(self) -> Decimal:
        s = self.d.sign
        total = Decimal(0)
        for leg in self.legs:
            if leg.entry is not None and leg.exit is not None:
                total += (leg.exit - leg.entry) * s / self.tick * self.tick_value * leg.qty - leg.fee
        return total

    def risk_usd(self) -> Decimal:
        return self.plan.risk_pts / self.tick * self.tick_value * self.qty


@dataclass(frozen=True)
class Event:
    kind: Literal["OPENED", "CLOSED", "PAUSE", "FLATTENED", "STOP_MOVED"]
    trade: OpenTrade
    detail: str = ""


@dataclass
class OrderManager:
    adapter: BrokerAdapter
    trail_r: Decimal = Decimal(2)
    min_hold_s: int = 9
    early_exit_until_r: Decimal = Decimal(1)
    split_for_defence: bool = False
    scalp_runner: tuple[Decimal, Decimal] | None = None  # (runner target R, trail R) when Scalp mode is on
    trades: dict[str, OpenTrade] = field(default_factory=dict)
    _ids: itertools.count[int] = field(default_factory=lambda: itertools.count(1))

    # ---------- open ----------
    def legs_for(self, plan: TradePlan, n: int, guard_on: bool, tick: Decimal | None = None) -> list[Leg]:
        if self.scalp_runner is not None and plan.mode == "ONE_TO_ONE" and n >= 2 and tick is not None:
            # Scalp: half takes the quick target, half runs (stop → breakeven after the first half, then trails).
            runner_r, _ = self.scalp_runner
            a, b = split_legs(n)
            far = round_to_tick(plan.entry + plan.direction.sign * runner_r * plan.risk_pts, tick, toward=plan.entry)
            return [Leg("A", a, plan.take_profit), Leg("B", b, far)]
        split = (guard_on or plan.mode == "ONE_TO_ONE") and n >= 2 and plan.partial_price is not None
        if split:
            a, b = split_legs(n)
            assert plan.partial_price is not None
            return [Leg("A", a, plan.partial_price), Leg("B", b, plan.take_profit)]
        if self.split_for_defence and n >= 2:  # two identical brackets so half can be closed on its own
            a, b = split_legs(n)
            return [Leg("H1", a, plan.take_profit), Leg("H2", b, plan.take_profit)]
        return [Leg("ONLY", n, plan.take_profit)]

    async def adverse_half(
        self, trade_id: str, worst: Decimal, at: Decimal, broken: bool, now: datetime
    ) -> list[Event]:
        """Close one leg (≈ half) when every confirmation is against the trade and price is near the stop."""
        t = self.trades.get(trade_id)
        if t is None or t.half_used:
            return []
        open_legs = [x for x in t.legs if not x.closed and x.entry is not None]
        qty = sum(x.qty for x in open_legs)
        if not adverse_half_due(t.plan, worst, at, broken, qty, t.half_used) or len(open_legs) < 2:
            return []
        if not exit_allowed_now("ADVERSE_HALF", t.opened_at, now, self.min_hold_s):
            return []
        t.half_used = True
        leg = open_legs[0]
        try:
            await self.adapter.close_leg(t.account, leg.bracket_id)  # type: ignore[attr-defined]
        except BrokerError as e:
            return [Event("STOP_MOVED", t, f"HALF_OFF_FAILED: {e}")]
        return [Event("STOP_MOVED", t, f"HALF_OFF {leg.qty}")]

    async def open_trade(
        self,
        account: str,
        symbol: str,
        plan: TradePlan,
        contracts: int,
        guard_on: bool,
        tick: Decimal,
        tick_value: Decimal,
        now: datetime,
        rr_window: tuple[Decimal, Decimal, Decimal, Decimal, int, int],
    ) -> OpenTrade:
        side: Side = "BUY" if plan.direction is Direction.LONG else "SELL"
        t = OpenTrade(
            f"T{next(self._ids)}",
            account,
            symbol,
            plan,
            guard_on,
            tick,
            tick_value,
            now,
            self.legs_for(plan, contracts, guard_on, tick),
            rr_window,
        )
        for leg in t.legs:
            try:
                ack = await self.adapter.place_bracket(
                    account,
                    BracketRequest(f"{t.trade_id}-{leg.name}", symbol, side, leg.qty, plan.stop, leg.take_profit),
                )
            except BrokerError:
                await self._emergency_flatten(t)
                raise
            leg.bracket_id, leg.stop_order_id, leg.stop = ack.bracket_id, ack.stop_order_id, plan.stop
        if self.scalp_runner is not None and len(t.legs) == 2 and t.legs[0].name == "A" and plan.mode == "ONE_TO_ONE":
            t.runner_trail = self.scalp_runner[1]
        self.trades[t.trade_id] = t
        return t

    async def _emergency_flatten(self, t: OpenTrade) -> None:
        with contextlib.suppress(BrokerError):  # caller pauses + alerts; broker-side stops remain in place
            await self.adapter.flatten(t.account)

    def _find(self, bracket_id: str | None) -> tuple[OpenTrade, Leg] | None:
        for t in self.trades.values():
            for leg in t.legs:
                if leg.bracket_id == bracket_id:
                    return t, leg
        return None

    # ---------- fills ----------
    async def on_fill(self, f: Fill) -> list[Event]:
        hit = self._find(f.bracket_id)
        if hit is None:
            return []  # not ours → reconcile.py reports it
        t, leg = hit
        out: list[Event] = []
        if f.role == "ENTRY":
            leg.entry = f.price
            if all(x.entry is not None for x in t.legs) and t.plan.mode == "STANDARD":
                inv, t2, rmin, rmax, buf, mst = t.rr_window
                avg = sum(((x.entry or Decimal(0)) * x.qty for x in t.legs), Decimal(0)) / t.qty
                p = rebuild_after_fill(t.plan, avg, inv, t2, t.tick, buf, mst, rmin, rmax)
                if isinstance(p, Skip):
                    await self.adapter.flatten(t.account)
                    out.append(Event("FLATTENED", t, "RR_INVALID_AFTER_FILL"))
            if all(x.entry is not None for x in t.legs):
                out.append(Event("OPENED", t))
            return out
        leg.exit, leg.fee, leg.closed = f.price, f.fee, True
        if f.role == "TP" and leg.name == "A":
            t.partial_done = True
            b = next(x for x in t.legs if x.name == "B")
            be = t.plan.breakeven_price
            if not b.closed and be is not None:
                out += await self._move_stop(t, b, be, "BREAKEVEN")
        if t.closed:
            del self.trades[t.trade_id]
            out.append(Event("CLOSED", t, f.role))
        return out

    async def _move_stop(self, t: OpenTrade, leg: Leg, price: Decimal, why: str) -> list[Event]:
        new = ratchet(leg.stop, price, t.d)
        if new == leg.stop:
            return []
        ok = False
        try:
            ok = await self.adapter.modify_stop(t.account, leg.stop_order_id, new)
        except BrokerError:
            ok = False
        if not ok:  # §8: stop-modify failure → flatten remainder + pause account
            await self._emergency_flatten(t)
            return [Event("PAUSE", t, "STOP_MODIFY_FAILED")]
        leg.stop = new
        return [Event("STOP_MOVED", t, f"{why} {new}")]

    # ---------- price ----------
    async def on_bar(self, symbol: str, high: Decimal, low: Decimal) -> list[Event]:
        out: list[Event] = []
        for t in list(self.trades.values()):
            if t.symbol != symbol or any(x.entry is None for x in t.legs):
                continue
            fav = high if t.d is Direction.LONG else low
            t.best = fav if t.best is None or (fav - t.best) * t.d.sign > 0 else t.best
            trail = t.runner_trail or (self.trail_r if t.guard_on else None)
            if trail is not None and t.partial_done and t.plan.breakeven_price is not None:
                b = next(x for x in t.legs if x.name == "B")
                if not b.closed:
                    out += await self._move_stop(t, b, runner_stop(t.plan, t.best, trail, t.tick), "TRAIL")
            single_1to1 = t.plan.mode == "ONE_TO_ONE" and len(t.legs) == 1 and not t.locked
            p, lock = t.plan.partial_price, t.plan.lock_price
            if single_1to1 and p is not None and lock is not None and (t.best - p) * t.d.sign >= 0:
                t.locked = True
                out += await self._move_stop(t, t.legs[0], lock, "LOCK")
        return out

    # ---------- exits ----------
    async def early_exit(self, trade_id: str, reason: str, now: datetime) -> list[Event]:
        """C3 close / CHoCH against: only before +1R or the partial, and only after the minimum hold (D8)."""
        t = self.trades.get(trade_id)
        if t is None or t.best is None:
            return []
        if not early_exit_allowed(t.plan, t.best, t.partial_done, self.early_exit_until_r):
            return []
        if not exit_allowed_now("EARLY_EXIT", t.opened_at, now, self.min_hold_s):
            return []
        await self.adapter.flatten(t.account)
        return [Event("FLATTENED", t, reason)]
