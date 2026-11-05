"""Sim adapter (§4): paper trading on real TradingView prices. Fees, slippage, stop-first on ambiguous bars,
gap fills at the open. Deterministic; failure injection for testing every safety path."""

from __future__ import annotations

import asyncio
import itertools
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.clock import Clock
from app.execution.adapters.base import (
    FULL_CAPS,
    AdapterHealth,
    BracketAck,
    BracketRequest,
    BrokerAccount,
    BrokerError,
    Fill,
    Order,
    PnlUpdate,
    Position,
    Side,
)


def _opp(side: Side) -> Side:
    return "SELL" if side == "BUY" else "BUY"


@dataclass(frozen=True)
class SimInstrument:
    tick: Decimal
    tick_value: Decimal
    fee_rt: Decimal


@dataclass
class _Bracket:
    bid: str
    acct: str
    req: BracketRequest
    entry_id: str
    stop_id: str
    tp_id: str
    entry_filled: bool = False
    entry_price: Decimal | None = None
    stop: Decimal = Decimal(0)
    done: bool = False


@dataclass
class _Account:
    balance: Decimal
    brackets: dict[str, _Bracket] = field(default_factory=dict)
    orders: dict[str, Order] = field(default_factory=dict)


class SimAdapter:
    name = "sim"
    capabilities = FULL_CAPS

    def __init__(self, clock: Clock, instruments: dict[str, SimInstrument], slippage_ticks: int = 1) -> None:
        self.clock = clock
        self.instruments = instruments
        self.slip = slippage_ticks
        self.accounts: dict[str, _Account] = {}
        self.last: dict[str, Decimal] = {}
        self._ids = itertools.count(1)
        self._fills: asyncio.Queue[Fill] = asyncio.Queue()
        self._pnl: asyncio.Queue[PnlUpdate] = asyncio.Queue()
        self.fail_next: set[str] = set()  # method names that fail once (tests)
        self._recent: list[Fill] = []

    # ---------- helpers ----------
    def _id(self, p: str) -> str:
        return f"{p}{next(self._ids)}"

    def _check(self, method: str) -> None:
        if method in self.fail_next:
            self.fail_next.discard(method)
            raise BrokerError(f"sim: injected {method} failure")

    def _acct(self, acct: str) -> _Account:
        if acct not in self.accounts:
            raise BrokerError(f"sim: unknown account {acct}")
        return self.accounts[acct]

    def add_account(self, acct: str, balance: Decimal) -> None:
        self.accounts[acct] = _Account(balance)

    def _inst(self, symbol: str) -> SimInstrument:
        return self.instruments[symbol]

    def _fill(self, a: str, b: _Bracket, role: str, price: Decimal, qty: int, side: Side) -> Fill:
        fee = self._inst(b.req.symbol).fee_rt * qty if role != "ENTRY" else Decimal(0)  # round trip charged on exit
        f = Fill(
            a,
            {"ENTRY": b.entry_id, "STOP": b.stop_id, "TP": b.tp_id}.get(role, b.entry_id),
            b.bid,
            role,
            b.req.symbol,
            side,
            qty,
            price,
            self.clock.now(),
            fee,
        )
        self._fills.put_nowait(f)
        self._recent.append(f)
        return f

    def _close(self, a: str, b: _Bracket, role: str, price: Decimal) -> None:
        acct, inst = self.accounts[a], self._inst(b.req.symbol)
        sign = 1 if b.req.side == "BUY" else -1
        assert b.entry_price is not None
        pnl = (price - b.entry_price) * sign / inst.tick * inst.tick_value * b.req.qty - inst.fee_rt * b.req.qty
        acct.balance += pnl
        b.done = True
        exit_side = _opp(b.req.side)
        filled_id = b.stop_id if role == "STOP" else b.tp_id if role == "TP" else None
        for oid in (b.stop_id, b.tp_id):
            o = acct.orders[oid]
            status: Literal["FILLED", "CANCELLED"] = "FILLED" if oid == filled_id else "CANCELLED"
            acct.orders[oid] = Order(
                o.order_id, o.account_id, o.symbol, o.side, o.qty, o.kind, o.price, status, o.bracket_id, o.role
            )
        self._fill(a, b, role, price, b.req.qty, exit_side)

    def _fill_entry(self, a: str, b: _Bracket, price: Decimal) -> None:
        b.entry_filled, b.entry_price = True, price
        acct = self.accounts[a]
        o = acct.orders[b.entry_id]
        acct.orders[b.entry_id] = Order(
            o.order_id, o.account_id, o.symbol, o.side, o.qty, o.kind, price, "FILLED", o.bracket_id, "ENTRY"
        )
        self._fill(a, b, "ENTRY", price, b.req.qty, b.req.side)

    # ---------- BrokerAdapter ----------
    async def list_accounts(self) -> list[BrokerAccount]:
        self._check("list_accounts")
        return [BrokerAccount(k, k, v.balance) for k, v in self.accounts.items()]

    async def get_positions(self, acct: str) -> list[Position]:
        self._check("get_positions")
        net: dict[str, tuple[int, Decimal]] = {}
        for b in self._acct(acct).brackets.values():
            if b.entry_filled and not b.done:
                q = b.req.qty if b.req.side == "BUY" else -b.req.qty
                assert b.entry_price is not None
                prev_q, prev_cost = net.get(b.req.symbol, (0, Decimal(0)))
                net[b.req.symbol] = (prev_q + q, prev_cost + b.entry_price * abs(q))
        return [Position(acct, s, q, (c / abs(q)) if q else Decimal(0)) for s, (q, c) in net.items() if q != 0]

    async def get_orders(self, acct: str) -> list[Order]:
        self._check("get_orders")
        return [o for o in self._acct(acct).orders.values() if o.status == "WORKING"]

    async def get_balance(self, acct: str) -> Decimal:
        self._check("get_balance")
        return self._acct(acct).balance

    async def place_bracket(self, acct: str, req: BracketRequest) -> BracketAck:
        self._check("place_bracket")
        a = self._acct(acct)
        inst = self._inst(req.symbol)
        bid = self._id("B")
        b = _Bracket(bid, acct, req, self._id("O"), self._id("O"), self._id("O"), stop=req.stop)
        exit_side = _opp(req.side)
        a.orders[b.entry_id] = Order(
            b.entry_id, acct, req.symbol, req.side, req.qty, req.entry_type, req.limit_price, "WORKING", bid, "ENTRY"
        )
        a.orders[b.stop_id] = Order(
            b.stop_id, acct, req.symbol, exit_side, req.qty, "STOP", req.stop, "WORKING", bid, "STOP"
        )
        a.orders[b.tp_id] = Order(
            b.tp_id, acct, req.symbol, exit_side, req.qty, "LIMIT", req.take_profit, "WORKING", bid, "TP"
        )
        a.brackets[bid] = b
        if req.entry_type == "MARKET":
            last = self.last.get(req.symbol)
            if last is None:
                raise BrokerError(f"sim: no price yet for {req.symbol}")
            sign = 1 if req.side == "BUY" else -1
            self._fill_entry(acct, b, last + sign * self.slip * inst.tick)  # adverse slippage
        return BracketAck(bid, b.entry_id, b.stop_id, b.tp_id)

    async def modify_stop(self, acct: str, order_id: str, price: Decimal) -> bool:
        if "modify_stop" in self.fail_next:
            self.fail_next.discard("modify_stop")
            return False
        a = self._acct(acct)
        for b in a.brackets.values():
            if b.stop_id == order_id and not b.done:
                b.stop = price
                o = a.orders[order_id]
                a.orders[order_id] = Order(
                    o.order_id, o.account_id, o.symbol, o.side, o.qty, o.kind, price, o.status, o.bracket_id, o.role
                )
                return True
        return False

    async def cancel_all(self, acct: str) -> None:
        self._check("cancel_all")
        a = self._acct(acct)
        for b in a.brackets.values():
            if not b.entry_filled and not b.done:
                b.done = True
        for oid, o in list(a.orders.items()):
            if o.status == "WORKING" and not self._protects_open(a, o):
                a.orders[oid] = Order(
                    o.order_id,
                    o.account_id,
                    o.symbol,
                    o.side,
                    o.qty,
                    o.kind,
                    o.price,
                    "CANCELLED",
                    o.bracket_id,
                    o.role,
                )

    @staticmethod
    def _protects_open(a: _Account, o: Order) -> bool:
        b = a.brackets.get(o.bracket_id or "")
        return b is not None and b.entry_filled and not b.done and o.role in ("STOP", "TP")

    async def flatten(self, acct: str) -> None:
        self._check("flatten")
        a = self._acct(acct)
        for b in a.brackets.values():
            if b.entry_filled and not b.done:
                inst = self._inst(b.req.symbol)
                sign = 1 if b.req.side == "BUY" else -1
                px = self.last.get(b.req.symbol, b.entry_price or Decimal(0)) - sign * self.slip * inst.tick
                self._close(acct, b, "FLATTEN", px)
        await self.cancel_all(acct)

    async def stream_fills(self) -> AsyncIterator[Fill]:
        while True:
            yield await self._fills.get()

    async def stream_pnl(self) -> AsyncIterator[PnlUpdate]:
        while True:
            yield await self._pnl.get()

    async def health(self) -> AdapterHealth:
        return AdapterHealth(True, "simulator")

    # ---------- price feed ----------
    def drain_fills(self) -> list[Fill]:
        out = []
        while not self._fills.empty():
            out.append(self._fills.get_nowait())
        return out

    def open_pnl(self, acct: str) -> Decimal:
        a = self.accounts[acct]
        total = Decimal(0)
        for b in a.brackets.values():
            if b.entry_filled and not b.done and b.req.symbol in self.last:
                inst = self._inst(b.req.symbol)
                sign = 1 if b.req.side == "BUY" else -1
                assert b.entry_price is not None
                total += (self.last[b.req.symbol] - b.entry_price) * sign / inst.tick * inst.tick_value * b.req.qty
        return total

    def on_bar(self, symbol: str, o: Decimal, h: Decimal, low: Decimal, c: Decimal, at: datetime) -> list[Fill]:
        """Process one closed bar: limit entries, then stops/targets (stop first when both are touched).
        Returns the fills this bar produced (they are also on the stream)."""
        self._recent = []
        for acct_id, a in self.accounts.items():
            for b in list(a.brackets.values()):
                if b.done or b.req.symbol != symbol:
                    continue
                if not b.entry_filled and b.req.entry_type == "LIMIT" and b.req.limit_price is not None:
                    lp = b.req.limit_price
                    if (b.req.side == "BUY" and low <= lp) or (b.req.side == "SELL" and h >= lp):
                        self._fill_entry(acct_id, b, min(o, lp) if b.req.side == "BUY" else max(o, lp))
                    continue
                if not b.entry_filled:
                    continue
                long = b.req.side == "BUY"
                stop_hit = low <= b.stop if long else h >= b.stop
                tp_hit = h >= b.req.take_profit if long else low <= b.req.take_profit
                inst = self._inst(symbol)
                if stop_hit:  # stop first on ambiguous bars (§4)
                    gap = (o <= b.stop) if long else (o >= b.stop)
                    px = o if gap else b.stop
                    px = px - (inst.tick * self.slip if long else -inst.tick * self.slip)
                    self._close(acct_id, b, "STOP", px)
                elif tp_hit:
                    gap = (o >= b.req.take_profit) if long else (o <= b.req.take_profit)
                    self._close(acct_id, b, "TP", o if gap else b.req.take_profit)
        self.last[symbol] = c
        for acct_id, a in self.accounts.items():
            self._pnl.put_nowait(PnlUpdate(acct_id, a.balance, self.open_pnl(acct_id), at))
        return list(self._recent)
