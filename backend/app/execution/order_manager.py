"""Order manager: turns an approved plan into bracket orders and manages them until flat (§7, §8, D7, D8).

Safety rules enforced here:
- every leg is a full bracket (stop + take-profit), never a naked entry;
- if any leg fails to place, the account is flattened and paused (no half-protected position);
- a market fill is re-checked against the 2–3R window; outside it → flatten (RR_INVALID_AFTER_FILL);
- limit_cisd mode: every leg is a LIMIT bracket at the planned entry (stop + TP attached); an entry still unfilled
  after the timeout is cancelled (LIMIT_TIMEOUT) and is never booked as a trade; a failed cancel pauses the
  account and is retried, a working order is never left behind silently;
- a failed stop modification → flatten + pause (§8), never left at the old stop silently.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.engine.trade_plan import Direction, Skip, TradePlan, rebuild_after_fill, round_to_tick
from app.execution.adapters.base import BracketRequest, BrokerAdapter, BrokerError, Fill, Side
from app.indicators.bars import Bar
from app.management.drawdown_guard import ratchet, runner_stop, split_legs
from app.management.dynamic_trail import TrailParams, dynamic_stop
from app.management.exits import adverse_half_due, early_exit_allowed, exit_allowed_now
from app.management.profit_lock import PROFIT_LOCK_REASON, lock_stop
from app.management.trade_manage import ManageCfg, managed_stop


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
    closing: str | None = None  # exit reason once a flatten was requested: stays tracked until the exit fill arrives
    closing_since: datetime | None = None  # stamped by the controller (watchdog grace for a missing exit fill)
    orphan: bool = False  # leg placement failed AND the emergency flatten failed: unprotected, watchdog flattens
    exit_qty: int = 0  # unmatched (flatten) exit fills accumulated while closing
    exit_notional: Decimal = Decimal(0)
    exit_fee: Decimal = Decimal(0)
    pending_until: datetime | None = None  # limit entries: cancel the unfilled legs from this moment on
    cancel_alerted: bool = False  # a failed entry cancel already raised the pause/banner (retries stay quiet)
    profile: str = ""  # signal profile (TIGHT/STD): the half-off defence reads this timeframe's MSO (D37)
    signal_id: int | None = None  # D55: strategy exits find their trades by signal
    strategy: str = ""  # D55: NOISE / AI_DUO / ... trades are exited by their own rules
    profit_lock: tuple[Decimal, Decimal] | None = None  # D82: (trigger_pts, lock_pts) — NOISE profit lock (D75-P1)
    profit_locked: bool = False  # the stop has been moved to entry + lock_pts
    manage: ManageCfg | None = None  # D85: AI Duo break-even / profit lock / trail (management/trade_manage.py)
    dyn_trail: TrailParams | None = None  # D122: dynamic trailing stop (management/dynamic_trail.py), toggle per strategy

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


class OrphanedPosition(BrokerError):
    """A leg failed to place and the emergency flatten failed too: the trade stays tracked as an orphan."""

    def __init__(self, trade: OpenTrade, detail: str) -> None:
        super().__init__(detail)
        self.trade = trade


@dataclass(frozen=True)
class Event:
    kind: Literal["OPENED", "CLOSED", "PAUSE", "FLATTENED", "STOP_MOVED", "CANCELLED", "ENTRY_TRIMMED"]
    trade: OpenTrade
    detail: str = ""


@dataclass
class OrderManager:
    adapter: BrokerAdapter
    trail_r: Decimal = Decimal(2)
    min_hold_s: Decimal | float = Decimal("7.5")
    early_exit_until_r: Decimal = Decimal(1)
    split_for_defence: bool = False
    scalp_runner: tuple[Decimal, Decimal] | None = None  # (runner target R, trail R) when Scalp mode is on
    trades: dict[str, OpenTrade] = field(default_factory=dict)
    bars: dict[str, list[Bar]] = field(default_factory=dict)  # D122: recent heartbeat bars per symbol (finest feed)
    max_bars: int = 600
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
        entry_mode: Literal["market", "limit_cisd"] = "market",
        limit_deadline: datetime | None = None,
        trade_id: str | None = None,
    ) -> OpenTrade:
        """trade_id: the controller passes the deterministic `P-{signal_id}-{account_id}` (unique across restarts, and
        the broker client order id derives from it, so a re-run is rejected broker-side too). Tests may omit it."""
        limit = entry_mode == "limit_cisd"
        side: Side = "BUY" if plan.direction is Direction.LONG else "SELL"
        t = OpenTrade(
            trade_id or f"T{next(self._ids)}",
            account,
            symbol,
            plan,
            guard_on,
            tick,
            tick_value,
            now,
            self.legs_for(plan, contracts, guard_on, tick),
            rr_window,
            pending_until=limit_deadline if limit else None,
        )
        for leg in t.legs:
            try:
                ack = await self.adapter.place_bracket(
                    account,
                    BracketRequest(
                        f"{t.trade_id}-{leg.name}",
                        symbol,
                        side,
                        leg.qty,
                        plan.stop,
                        leg.take_profit,
                        "LIMIT" if limit else "MARKET",
                        plan.entry if limit else None,
                    ),
                )
            except BrokerError as e:
                if not await self._emergency_flatten(t):
                    # keep the (possibly unprotected) position tracked; the watchdog keeps trying to flatten it
                    t.orphan, t.closing = True, "ORPHAN_FLATTEN"
                    self.trades[t.trade_id] = t
                    raise OrphanedPosition(t, str(e)) from e
                raise
            leg.bracket_id, leg.stop_order_id, leg.stop = ack.bracket_id, ack.stop_order_id, plan.stop
        if self.scalp_runner is not None and len(t.legs) == 2 and t.legs[0].name == "A" and plan.mode == "ONE_TO_ONE":
            t.runner_trail = self.scalp_runner[1]
        self.trades[t.trade_id] = t
        return t

    async def _emergency_flatten(self, t: OpenTrade) -> bool:
        """True when the broker accepted the flatten. False → caller keeps the trade tracked (never silent)."""
        try:
            await self.adapter.flatten(t.account)
        except BrokerError:
            return False
        return True

    def restore(self, t: OpenTrade) -> None:
        """Restart recovery: put a rebuilt trade back under management."""
        self.trades[t.trade_id] = t

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
            return self._closing_fill(f)  # a flatten exit fill (no bracket) or not ours → reconcile.py reports it
        t, leg = hit
        out: list[Event] = []
        if f.role == "ENTRY":
            leg.entry = f.price
            if t.pending_until is not None and t.opened_at < f.at:
                t.opened_at = f.at  # limit entries: the hold rule (D8) runs from the fill, not from the order
            return await self._entries_done(t) if all(x.entry is not None for x in t.legs) else out
        leg.exit, leg.fee, leg.closed = f.price, f.fee, True
        if f.role == "TP" and leg.name == "A":
            t.partial_done = True
            b = next((x for x in t.legs if x.name == "B"), None)  # absent when B's limit entry was cancelled
            be = t.plan.breakeven_price
            if b is not None and not b.closed and be is not None:
                out += await self._move_stop(t, b, be, "BREAKEVEN")
        if t.closed:
            del self.trades[t.trade_id]
            locked_exit = f.role == "STOP" and t.profit_locked
            out.append(Event("CLOSED", t, PROFIT_LOCK_REASON if locked_exit else f.role))
        return out

    async def _entries_done(self, t: OpenTrade) -> list[Event]:
        """Every remaining leg is filled: re-check the 2–3R window with the average fill (§7), then report OPENED.
        A better-than-limit fill never fails the check (the rebuilt plan is capped at rr_max); only a real window
        violation flattens."""
        out: list[Event] = []
        t.pending_until = None
        if t.plan.mode == "STANDARD":
            inv, t2, rmin, rmax, buf, mst = t.rr_window
            avg = sum(((x.entry or Decimal(0)) * x.qty for x in t.legs), Decimal(0)) / t.qty
            p = rebuild_after_fill(t.plan, avg, inv, t2, t.tick, buf, mst, rmin, rmax)
            if isinstance(p, Skip):
                await self.adapter.flatten(t.account)
                t.closing = "RR_INVALID_AFTER_FILL"  # stays tracked until the exit fill books the real P&L
                out.append(Event("FLATTENED", t, "RR_INVALID_AFTER_FILL"))
        out.append(Event("OPENED", t))
        return out

    # ---------- unfilled limit entries ----------
    @staticmethod
    def has_unfilled(t: OpenTrade) -> bool:
        return any(x.entry is None and x.bracket_id for x in t.legs)

    async def expire_unfilled(self, now: datetime) -> list[Event]:
        """Cancel the working entries of every limit trade whose timeout has passed (LIMIT_TIMEOUT)."""
        out: list[Event] = []
        for t in list(self.trades.values()):
            if t.pending_until is not None and now >= t.pending_until and not t.closing and self.has_unfilled(t):
                out += await self.cancel_unfilled(t, "LIMIT_TIMEOUT")
        return out

    async def cancel_unfilled(self, t: OpenTrade, reason: str) -> list[Event]:
        """Cancel the unfilled limit entries of a trade (their stop + TP go with them).
        Nothing filled → the trade is dropped (CANCELLED, never booked). Some legs filled → only the unfilled legs
        are removed (ENTRY_TRIMMED) and the filled ones are managed normally. A failed cancel keeps everything
        tracked, pauses the account once and is retried by the caller (never a silent working order)."""
        pending = [x for x in t.legs if x.entry is None and x.bracket_id]
        if not pending:
            return []
        filled = any(x.entry is not None for x in t.legs)
        try:
            if filled:  # a per-bracket cancel: an account-wide cancel would also remove the filled leg's stop
                for leg in pending:
                    await self.adapter.cancel_entry(t.account, leg.bracket_id)
            else:
                await self.adapter.cancel_all(t.account)
        except BrokerError as e:
            if t.cancel_alerted:
                return []
            t.cancel_alerted = True
            return [Event("PAUSE", t, f"LIMIT_CANCEL_FAILED: {e}")]
        t.pending_until = None
        if not filled:
            self.trades.pop(t.trade_id, None)
            return [Event("CANCELLED", t, reason)]
        t.legs = [x for x in t.legs if x not in pending]
        return [Event("ENTRY_TRIMMED", t, reason)] + await self._entries_done(t)

    def _closing_fill(self, f: Fill) -> list[Event]:
        """Exit fill of a flatten order (no bracket id, e.g. CrossTrade polling): books the real exit price on the
        trade that is waiting in 'closing'. Partial fills accumulate until the whole open quantity is out."""
        remaining = f.qty
        events: list[Event] = []
        for t in list(self.trades.values()):  # several positions on one account (AI Duo 150K): fill the trades in turn
            if remaining <= 0:
                break
            if not t.closing or t.account != f.account_id or t.symbol != f.symbol:
                continue
            if f.side != ("SELL" if t.d is Direction.LONG else "BUY"):
                continue
            open_legs = [x for x in t.legs if x.entry is not None and not x.closed]
            if not open_legs:
                continue
            need = sum(x.qty for x in open_legs) - t.exit_qty
            take = min(remaining, need)
            if take <= 0:
                continue
            remaining -= take
            t.exit_qty += take
            t.exit_notional += f.price * take
            t.exit_fee += f.fee * take / f.qty if f.qty else f.fee
            if t.exit_qty < sum(x.qty for x in open_legs):
                continue
            avg = t.exit_notional / t.exit_qty
            for i, leg in enumerate(open_legs):
                leg.exit, leg.fee, leg.closed = avg, (t.exit_fee if i == 0 else Decimal(0)), True
            del self.trades[t.trade_id]
            events.append(Event("CLOSED", t, "FLATTEN"))
        return events

    async def _stop_already_done(self, t: OpenTrade, leg: Leg) -> bool:
        """True only when the broker shows this leg's stop order no longer working (filled, or cancelled by its OCO
        take-profit). Any doubt (lookup error, order still listed WORKING) → False, so the §8 pause still applies."""
        try:
            orders = await self.adapter.get_orders(t.account)
        except BrokerError:
            return False
        o = next((x for x in orders if x.order_id == leg.stop_order_id), None)
        return o is None or o.status in ("FILLED", "CANCELLED")

    async def _move_stop(self, t: OpenTrade, leg: Leg, price: Decimal, why: str) -> list[Event]:
        new = ratchet(leg.stop, price, t.d)
        if new == leg.stop:
            return []
        ok = False
        try:
            ok = await self.adapter.modify_stop(t.account, leg.stop_order_id, new)
        except BrokerError:
            ok = False
        if not ok and await self._stop_already_done(t, leg):
            return []  # D38: the stop/TP already filled at the broker (race on the same bar) — its fill closes the leg
        if not ok:  # §8: stop-modify failure → flatten remainder + pause account
            t.closing = t.closing or "STOP_MODIFY_FAILED"  # tracked until flat; watchdog retries a failed flatten
            await self._emergency_flatten(t)
            return [Event("PAUSE", t, "STOP_MODIFY_FAILED")]
        leg.stop = new
        return [Event("STOP_MOVED", t, f"{why} {new}")]

    async def _managed(self, t: OpenTrade, last: Decimal | None) -> list[Event]:
        """D85: break-even, profit lock and trailing stop for each open leg on its own (ratchet only)."""
        assert t.manage is not None and t.best is not None
        out: list[Event] = []
        for leg in [x for x in t.legs if x.entry is not None and not x.closed]:
            mv = managed_stop(t.d, leg.entry or Decimal(0), t.plan.risk_pts, t.best, leg.stop, t.manage, t.tick, last)
            if mv is None:
                continue
            out += await self._move_stop(
                t, leg, mv.stop, f"MANAGE:{mv.rule}"
            )  # the rule that chose the level is logged
            if t.closing:
                break  # stop-modify failure: flattening, nothing more to move
        return out

    async def _profit_lock(self, t: OpenTrade, last: Decimal | None = None) -> list[Event]:
        """D82 / D75-P1: after +trigger pts the stop of every open leg moves to entry + lock pts (ratchet only, and
        never at or through the current price: pulled back to one tick behind it, review fix)."""
        assert t.profit_lock is not None
        out: list[Event] = []
        for leg in [x for x in t.legs if x.entry is not None and not x.closed]:
            new = lock_stop(t.d, leg.entry or Decimal(0), t.best or Decimal(0), *t.profit_lock, t.tick)
            if new is None:
                continue
            if last is not None and (new - (last - t.d.sign * t.tick)) * t.d.sign > 0:
                new = last - t.d.sign * t.tick
            ev = await self._move_stop(t, leg, new, PROFIT_LOCK_REASON)
            out += ev
            if any(e.kind == "STOP_MOVED" for e in ev):
                t.profit_locked = True
            if t.closing:
                break  # stop-modify failure: flattening, nothing more to move
        return out

    async def _dynamic(self, t: OpenTrade, last: Decimal | None) -> list[Event]:
        """D122: dynamic trailing stop for each open leg (ratchet only, never closer than the min distance)."""
        assert t.dyn_trail is not None and t.best is not None
        out: list[Event] = []
        bars = self.bars.get(t.symbol, [])
        for leg in [x for x in t.legs if x.entry is not None and not x.closed]:
            mv = dynamic_stop(
                t.d, leg.entry or Decimal(0), t.plan.risk_pts, t.best, leg.stop, bars, t.dyn_trail, t.tick, last
            )
            if mv is None:
                continue
            out += await self._move_stop(t, leg, mv.stop, f"DYN_TRAIL:{mv.rule}")
            if t.closing:
                break  # stop-modify failure: flattening, nothing more to move
        return out

    def add_bar(self, symbol: str, bar: Bar) -> None:
        """Keep the last max_bars heartbeat bars (a repeated bar replaces its earlier copy)."""
        buf = self.bars.setdefault(symbol, [])
        if buf and buf[-1].close_ms == bar.close_ms:
            buf[-1] = bar
        elif not buf or bar.close_ms > buf[-1].close_ms:
            buf.append(bar)
        del buf[: -self.max_bars]

    # ---------- price ----------
    async def on_bar(
        self, symbol: str, high: Decimal, low: Decimal, close: Decimal | None = None, bar: Bar | None = None
    ) -> list[Event]:
        out: list[Event] = []
        if bar is not None:
            self.add_bar(symbol, bar)
        for t in list(self.trades.values()):
            if t.symbol != symbol or any(x.entry is None for x in t.legs):
                continue
            fav = high if t.d is Direction.LONG else low
            t.best = fav if t.best is None or (fav - t.best) * t.d.sign > 0 else t.best
            last = close if close is not None else low  # the controller always passes the close: the cap is exact
            if t.profit_lock is not None and not t.closing:
                out += await self._profit_lock(t, last)
            if t.manage is not None and not t.closing:
                out += await self._managed(t, last)
            if t.dyn_trail is not None and not t.closing:
                out += await self._dynamic(t, last)
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
    async def strategy_exit(self, trade_id: str, reason: str, now: datetime) -> list[Event] | None:
        """D55: NOISE trailing exit / 16:00 flat, strategy time stops. An entry that never filled is cancelled.
        App-initiated → the minimum hold (D8) applies: None = not allowed YET (the controller retries next bar)."""
        t = self.trades.get(trade_id)
        if t is None or t.closing:
            return []
        if all(x.entry is None for x in t.legs):
            return await self.cancel_unfilled(t, reason)
        if not exit_allowed_now("STRATEGY_EXIT", t.opened_at, now, self.min_hold_s):
            return None
        await self.adapter.flatten(t.account)
        t.closing = reason
        return [Event("FLATTENED", t, reason)]

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
        t.closing = reason
        return [Event("FLATTENED", t, reason)]
