"""Routes each account to the simulator (paper) or the live broker (CrossTrade → Tradovate).

Paper accounts always go to the simulator. A live account's ORDERS are refused unless `live_ok()` is true at that
moment (Live-Readiness Checklist §1.5). Protective actions (flatten, cancel, stop moves) are never blocked.
Live fills/P&L arrive from background pollers and are queued; the controller drains them like simulator fills.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.execution.adapters.base import (
    AdapterHealth,
    BracketAck,
    BracketRequest,
    BrokerAccount,
    BrokerAdapter,
    BrokerError,
    Fill,
    Order,
    PnlUpdate,
    Position,
)
from app.execution.adapters.sim import SimAdapter


class LiveBlockedError(BrokerError):
    """Live-Readiness Checklist not fully green → no live order."""


class RoutingAdapter:
    def __init__(self, sim: SimAdapter) -> None:
        self.sim = sim
        self.live: BrokerAdapter | None = None
        self.live_ok: Callable[[], bool] = lambda: False
        self.live_accounts: set[str] = set()
        self._live_fills: list[Fill] = []
        self._live_pnl: dict[str, PnlUpdate] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self.last_error: str | None = None
        self.retry_s = 5.0

    # ---------- wiring ----------
    @property
    def name(self) -> str:
        return f"sim+{self.live.name}" if self.live else "sim"

    @property
    def capabilities(self) -> frozenset[str]:
        caps = self.sim.capabilities
        return caps & self.live.capabilities if self.live else caps

    @property
    def accounts(self) -> set[str]:
        return set(self.sim.accounts) | (self.live_accounts if self.live else set())

    def set_live(self, live: BrokerAdapter | None, accounts: set[str], live_ok: Callable[[], bool]) -> None:
        self.stop()
        self.live, self.live_accounts, self.live_ok = live, set(accounts), live_ok

    def start(self) -> None:
        if self.live is not None:
            self._tasks = [asyncio.create_task(self._pump_fills()), asyncio.create_task(self._pump_pnl())]

    def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        self._tasks = []

    async def _pump_fills(self) -> None:
        while self.live is not None:
            try:
                async for f in self.live.stream_fills():
                    if f.account_id in self.live_accounts:
                        self._live_fills.append(f)
            except BrokerError as e:
                self.last_error = f"fills: {e}"
            await asyncio.sleep(self.retry_s)

    async def _pump_pnl(self) -> None:
        while self.live is not None:
            stream: AsyncIterator[PnlUpdate] | None = self.live.stream_pnl()
            if stream is None:
                return
            try:
                async for u in stream:
                    self._live_pnl[u.account_id] = u
            except BrokerError as e:
                self.last_error = f"pnl: {e}"
            await asyncio.sleep(self.retry_s)

    def push_live_fill(self, f: Fill) -> None:  # also used by tests
        self._live_fills.append(f)

    def push_live_pnl(self, u: PnlUpdate) -> None:
        self._live_pnl[u.account_id] = u

    def _for(self, acct: str) -> Any:
        if acct in self.sim.accounts:
            return self.sim
        if self.live is not None and acct in self.live_accounts:
            return self.live
        raise BrokerError(f"unknown account {acct}")

    # ---------- reads ----------
    async def list_accounts(self) -> list[BrokerAccount]:
        out = await self.sim.list_accounts()
        if self.live is not None:
            out += [a for a in await self.live.list_accounts() if a.account_id in self.live_accounts]
        return out

    async def get_positions(self, acct: str) -> list[Position]:
        return list(await self._for(acct).get_positions(acct))

    async def get_orders(self, acct: str) -> list[Order]:
        return list(await self._for(acct).get_orders(acct))

    async def get_balance(self, acct: str) -> Decimal:
        if acct in self._live_pnl and acct not in self.sim.accounts:
            return self._live_pnl[acct].balance
        return Decimal(await self._for(acct).get_balance(acct))

    def open_pnl(self, acct: str) -> Decimal:
        if acct in self.sim.accounts:
            return self.sim.open_pnl(acct)
        u = self._live_pnl.get(acct)
        if u is None:
            raise BrokerError(f"{acct}: no live P&L yet")
        return u.open_pnl

    def pnl_age(self, acct: str, now: datetime) -> float | None:
        u = self._live_pnl.get(acct)
        return None if u is None else (now - u.at).total_seconds()

    # ---------- writes ----------
    async def place_bracket(self, acct: str, req: BracketRequest) -> BracketAck:
        ad = self._for(acct)
        if ad is not self.sim and not self.live_ok():
            raise LiveBlockedError("LIVE_BLOCKED: Live-Readiness Checklist not complete")
        ack: BracketAck = await ad.place_bracket(acct, req)
        return ack

    async def modify_stop(self, acct: str, order_id: str, price: Decimal) -> bool:
        return bool(await self._for(acct).modify_stop(acct, order_id, price))

    async def close_leg(self, acct: str, bracket_id: str) -> None:
        ad = self._for(acct)
        if not hasattr(ad, "close_leg"):
            raise BrokerError(f"{ad.name}: closing one bracket is not supported yet")
        await ad.close_leg(acct, bracket_id)

    async def cancel_all(self, acct: str) -> None:
        await self._for(acct).cancel_all(acct)

    async def cancel_entry(self, acct: str, bracket_id: str) -> None:
        await self._for(acct).cancel_entry(acct, bracket_id)

    async def flatten(self, acct: str) -> None:
        await self._for(acct).flatten(acct)

    # ---------- streams ----------
    def drain_fills(self) -> list[Fill]:
        out = self.sim.drain_fills() + self._live_fills
        self._live_fills = []
        return out

    def on_bar(self, symbol: str, o: Decimal, h: Decimal, low: Decimal, c: Decimal, at: datetime) -> list[Fill]:
        fills = list(self.sim.on_bar(symbol, o, h, low, c, at))
        # the simulator also queues these fills; drop them from the queue so each is applied exactly once
        queued = self.sim.drain_fills()
        for f in queued:
            if f not in fills:
                self.sim._fills.put_nowait(f)
        return fills + self.drain_live()

    def drain_live(self) -> list[Fill]:
        out, self._live_fills = self._live_fills, []
        return out

    def register_bracket(self, acct: str, bracket_id: str, stop_order_id: str, tp_order_id: str) -> None:
        """Restart recovery: tell a live adapter which order ids belong to a recovered bracket (no-op elsewhere)."""
        if self.live is not None and acct in self.live_accounts and hasattr(self.live, "register_bracket"):
            self.live.register_bracket(bracket_id, stop_order_id, tp_order_id)

    def add_account(self, acct: str, balance: Decimal) -> None:
        self.sim.add_account(acct, balance)

    def stream_fills(self) -> AsyncIterator[Fill]:
        return self.sim.stream_fills()

    def stream_pnl(self) -> AsyncIterator[PnlUpdate] | None:
        return self.sim.stream_pnl()

    async def health(self) -> AdapterHealth:
        h = await self.sim.health()
        if self.live is None:
            return h
        lh = await self.live.health()
        return AdapterHealth(lh.ok, f"sim ok · {lh.detail}")
