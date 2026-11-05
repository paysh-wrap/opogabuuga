"""BrokerAdapter contract (§4) + shared models. Adapters declare what they cannot do via `capabilities`."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol

CAP_READ_POSITIONS = "read_positions"
CAP_READ_ORDERS = "read_orders"
CAP_READ_BALANCE = "read_balance"
CAP_PLACE_BRACKET = "place_bracket"
CAP_MODIFY_STOP = "modify_stop"
CAP_CANCEL_ALL = "cancel_all"
CAP_FLATTEN = "flatten"
CAP_STREAM_FILLS = "stream_fills"
CAP_STREAM_PNL = "stream_pnl"
FULL_CAPS = frozenset(
    {
        CAP_READ_POSITIONS,
        CAP_READ_ORDERS,
        CAP_READ_BALANCE,
        CAP_PLACE_BRACKET,
        CAP_MODIFY_STOP,
        CAP_CANCEL_ALL,
        CAP_FLATTEN,
        CAP_STREAM_FILLS,
        CAP_STREAM_PNL,
    }
)

Side = Literal["BUY", "SELL"]


class NotSupported(Exception):
    """The adapter declared it cannot do this (see capabilities)."""


class BrokerError(Exception):
    """A broker call failed. Callers must block new entries + alert (§1.9)."""


@dataclass(frozen=True)
class BrokerAccount:
    account_id: str
    name: str
    balance: Decimal


@dataclass(frozen=True)
class Position:
    account_id: str
    symbol: str
    qty: int  # signed: + long, − short
    avg_price: Decimal


@dataclass(frozen=True)
class Order:
    order_id: str
    account_id: str
    symbol: str
    side: Side
    qty: int
    kind: Literal["MARKET", "LIMIT", "STOP"]
    price: Decimal | None
    status: Literal["WORKING", "FILLED", "CANCELLED", "REJECTED"]
    bracket_id: str | None = None
    role: Literal["ENTRY", "STOP", "TP"] = "ENTRY"


@dataclass(frozen=True)
class BracketRequest:
    """One OCO bracket: entry + protective stop + take-profit. A stop is ALWAYS required (user rule)."""

    client_id: str
    symbol: str
    side: Side
    qty: int
    stop: Decimal
    take_profit: Decimal
    entry_type: Literal["MARKET", "LIMIT"] = "MARKET"
    limit_price: Decimal | None = None

    def __post_init__(self) -> None:
        if self.qty < 1:
            raise ValueError("bracket qty must be ≥ 1")
        if self.stop is None or self.take_profit is None:
            raise ValueError("every order needs a stop-loss and a take-profit")


@dataclass(frozen=True)
class BracketAck:
    bracket_id: str
    entry_order_id: str
    stop_order_id: str
    tp_order_id: str


@dataclass(frozen=True)
class Fill:
    account_id: str
    order_id: str
    bracket_id: str | None
    role: str
    symbol: str
    side: Side
    qty: int
    price: Decimal
    at: datetime
    fee: Decimal = Decimal(0)


@dataclass(frozen=True)
class PnlUpdate:
    account_id: str
    balance: Decimal
    open_pnl: Decimal
    at: datetime

    @property
    def equity(self) -> Decimal:
        return self.balance + self.open_pnl


@dataclass(frozen=True)
class AdapterHealth:
    ok: bool
    detail: str = ""
    latency_ms: float | None = None
    token_expires_at: datetime | None = None
    extra: dict[str, str] = field(default_factory=dict)


class BrokerAdapter(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def capabilities(self) -> frozenset[str]: ...

    async def list_accounts(self) -> list[BrokerAccount]: ...
    async def get_positions(self, acct: str) -> list[Position]: ...
    async def get_orders(self, acct: str) -> list[Order]: ...
    async def get_balance(self, acct: str) -> Decimal: ...
    async def place_bracket(self, acct: str, req: BracketRequest) -> BracketAck: ...
    async def modify_stop(self, acct: str, order_id: str, price: Decimal) -> bool: ...
    async def cancel_all(self, acct: str) -> None: ...
    async def flatten(self, acct: str) -> None: ...
    def stream_fills(self) -> AsyncIterator[Fill]: ...
    def stream_pnl(self) -> AsyncIterator[PnlUpdate] | None: ...  # None → CONSERVATIVE MODE
    async def health(self) -> AdapterHealth: ...


def conservative_mode(adapter: BrokerAdapter) -> bool:
    """§4: no live P&L stream → open positions assumed at their stop; UI banner."""
    return CAP_STREAM_PNL not in adapter.capabilities or CAP_READ_POSITIONS not in adapter.capabilities
