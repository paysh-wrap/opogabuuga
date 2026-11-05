"""TradersPost adapter — SEND-ONLY backup route (docs: docs.traderspost.io webhook reference, checked 2026-11-05).

POST https://webhooks.traderspost.io/trading/webhook/{uuid}/{password} (one strategy webhook per Lucid account).
Fields used: ticker, action (buy|sell|exit|cancel), quantity, orderType, takeProfit{limitPrice},
stopLoss{type:"stop", stopPrice}, rejectAfter (s), time. TradersPost has no read API → CONSERVATIVE MODE (§4):
no position/fill/P&L read-back, so FULL-AUTO stays blocked and stops can't be modified (guard/1:1 can't run).
The strategy subscription must have "Allow signal override" ON for takeProfit/stopLoss to apply.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from app.execution.adapters.base import (
    CAP_CANCEL_ALL,
    CAP_FLATTEN,
    CAP_PLACE_BRACKET,
    AdapterHealth,
    BracketAck,
    BracketRequest,
    BrokerAccount,
    BrokerError,
    Fill,
    NotSupported,
    Order,
    PnlUpdate,
    Position,
)

PREFIX = "https://webhooks.traderspost.io/trading/webhook/"


class TradersPostAdapter:
    name = "traderspost"
    capabilities = frozenset({CAP_PLACE_BRACKET, CAP_FLATTEN, CAP_CANCEL_ALL})

    def __init__(self, webhooks: dict[str, str], http: httpx.AsyncClient, tv_symbols: dict[str, str]) -> None:
        for acct, url in webhooks.items():
            if not url.startswith(PREFIX):
                raise BrokerError(f"{acct}: not a TradersPost webhook URL")
        self.webhooks, self.http, self.tv_symbols = webhooks, http, tv_symbols

    async def _send(self, acct: str, body: dict[str, Any]) -> dict[str, Any]:
        url = self.webhooks.get(acct)
        if url is None:
            raise BrokerError(f"no TradersPost webhook for {acct}")
        body = {**body, "time": datetime.now(UTC).isoformat(), "rejectAfter": 10}
        try:
            r = await self.http.post(url, json=body)
        except httpx.HTTPError as e:
            raise BrokerError(f"TradersPost unreachable: {type(e).__name__}") from e
        data: dict[str, Any] = r.json() if r.content else {}
        if r.status_code != 200 or not data.get("success"):
            raise BrokerError(f"TradersPost {r.status_code} {data.get('messageCode')}: {data.get('message', '')}"[:300])
        return data

    async def place_bracket(self, acct: str, req: BracketRequest) -> BracketAck:
        body: dict[str, Any] = {
            "ticker": self.tv_symbols.get(req.symbol, req.symbol),
            "action": "buy" if req.side == "BUY" else "sell",
            "quantity": req.qty,
            "orderType": req.entry_type.lower(),
            "takeProfit": {"limitPrice": float(req.take_profit)},
            "stopLoss": {"type": "stop", "stopPrice": float(req.stop)},
            "extras": {"clientId": req.client_id},
        }
        if req.entry_type == "LIMIT":
            body["limitPrice"] = float(req.limit_price or 0)
        data = await self._send(acct, body)
        sid = str(data.get("id", req.client_id))
        return BracketAck(sid, sid, f"{sid}-SL", f"{sid}-TP")

    async def flatten(self, acct: str) -> None:
        for sym in self.tv_symbols.values():
            await self._send(acct, {"ticker": sym, "action": "exit"})

    async def cancel_all(self, acct: str) -> None:
        for sym in self.tv_symbols.values():
            await self._send(acct, {"ticker": sym, "action": "cancel"})

    async def cancel_entry(self, acct: str, bracket_id: str) -> None:
        raise BrokerError("traderspost: cancelling a single entry order is not supported")

    async def modify_stop(self, acct: str, order_id: str, price: Decimal) -> bool:
        return False  # not supported → callers flatten + pause; guard/1:1 trades are refused on this route

    async def list_accounts(self) -> list[BrokerAccount]:
        raise NotSupported("TradersPost has no account read API")

    async def get_positions(self, acct: str) -> list[Position]:
        raise NotSupported("TradersPost has no position read API")

    async def get_orders(self, acct: str) -> list[Order]:
        raise NotSupported("TradersPost has no order read API")

    async def get_balance(self, acct: str) -> Decimal:
        raise NotSupported("TradersPost has no balance read API")

    async def stream_fills(self) -> AsyncIterator[Fill]:
        raise NotSupported("no fill stream")
        yield  # pragma: no cover

    def stream_pnl(self) -> AsyncIterator[PnlUpdate] | None:
        return None  # → CONSERVATIVE MODE

    async def health(self) -> AdapterHealth:
        return AdapterHealth(bool(self.webhooks), "send-only (no read-back)")
