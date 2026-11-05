"""CrossTrade → Tradovate adapter (REST, docs checked 2026-11-05: crosstrade.io/docs/api/tradovate/overview).

Base https://app.crosstrade.io, prefix /v1/api/tv, header `Authorization: Bearer <token>` (requires CrossTrade Pro and a
linked Tradovate identity). Brackets are one native Tradovate OSO (TP = oso1Id, SL = oso2Id).

Safety rules from the docs that this adapter follows:
- a 2xx with an id means "accepted", not "working/filled" → callers reconcile;
- after 500/502/timeouts on a mutation, NEVER resend blind → raise UnconfirmedError so the caller pauses + reconciles;
- a stop "change" success is only a command ack → verify the new stop on the working order before reporting success;
- 429 → BrokerError (rate limited); no market data here (prices come from TradingView).
Fills: polled from GET /accounts/{a}/fills (verified format), deduped by executionId; session resets ~17:00 ET.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from app.execution.adapters.base import (
    CAP_CANCEL_ALL,
    CAP_FLATTEN,
    CAP_MODIFY_STOP,
    CAP_PLACE_BRACKET,
    CAP_READ_BALANCE,
    CAP_READ_ORDERS,
    CAP_READ_POSITIONS,
    CAP_STREAM_FILLS,
    CAP_STREAM_PNL,
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

BASE = "https://app.crosstrade.io/v1/api/tv"


class UnconfirmedError(BrokerError):
    """The broker may or may not have acted. Do not retry; pause and reconcile."""


def _d(x: Any) -> Decimal:
    return Decimal(str(x))


class CrossTradeAdapter:
    name = "crosstrade"
    capabilities = frozenset(
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

    def __init__(
        self,
        token: str,
        http: httpx.AsyncClient,
        tv_symbols: dict[str, str],
        poll_s: float = 5.0,
        verify_delay_s: float = 1.0,
    ) -> None:
        if not token:
            raise BrokerError("CrossTrade token missing (Connections page)")
        self._h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self.http, self.tv_symbols, self.poll_s, self.verify_delay_s = http, tv_symbols, poll_s, verify_delay_s
        self._roles: dict[str, tuple[str, str]] = {}  # order id → (bracket id, role)
        self._seen: set[str] = set()
        self._root = {v.rstrip("!").rstrip("1"): k for k, v in tv_symbols.items()}

    # ---------- http ----------
    async def _req(self, method: str, path: str, body: dict[str, Any] | None = None, mutation: bool = False) -> Any:
        try:
            r = await self.http.request(method, BASE + path, headers=self._h, json=body)
        except httpx.TimeoutException as e:
            if mutation:
                raise UnconfirmedError(f"timeout on {path}; outcome unknown") from e
            raise BrokerError(f"timeout on {path}") from e
        except httpx.HTTPError as e:
            raise BrokerError(f"network error on {path}: {type(e).__name__}") from e
        data = r.json() if r.content else {}
        if r.status_code in (500, 502) and mutation:
            raise UnconfirmedError(f"{r.status_code} {data.get('error')} on {path}; outcome unknown")
        if r.status_code >= 400 or data.get("success") is False:
            raise BrokerError(f"{r.status_code} {data.get('error')}: {data.get('detail', '')}"[:300])
        return data

    async def _snapshot(self) -> list[dict[str, Any]]:
        data = await self._req("GET", "/accounts/snapshot")
        return list(data.get("accounts", []))

    async def _acct(self, acct: str) -> dict[str, Any]:
        for a in await self._snapshot():
            if str(a.get("name", "")).upper() == acct.upper():
                if a.get("errorCode"):
                    raise BrokerError(f"{acct}: {a['errorCode']}")
                return a
        raise BrokerError(f"account {acct} not linked in CrossTrade")

    def _symbol(self, contract: str) -> str:
        """'MNQZ6' → 'MNQ' (root before the month code)."""
        c = contract.upper()
        for n in (3, 2):
            if c[:n] in self.tv_symbols:
                return c[:n]
        return c

    # ---------- reads ----------
    async def list_accounts(self) -> list[BrokerAccount]:
        out = []
        for a in await self._snapshot():
            nl, op = a.get("netLiq"), a.get("openPnl")
            bal = _d(nl) - _d(op) if nl is not None and op is not None else Decimal(0)
            out.append(BrokerAccount(str(a["name"]), str(a["name"]), bal))
        return out

    async def get_positions(self, acct: str) -> list[Position]:
        a = await self._acct(acct)
        return [
            Position(acct, self._symbol(str(p["contract"])), int(p["netPos"]), _d(p["netPrice"]))
            for p in a.get("positions", [])
            if int(p.get("netPos", 0)) != 0
        ]

    async def get_orders(self, acct: str) -> list[Order]:
        a = await self._acct(acct)
        out = []
        for o in a.get("workingOrders", []):
            kind = {"Limit": "LIMIT", "Stop": "STOP", "Market": "MARKET"}.get(str(o.get("orderType")), "LIMIT")
            px = o.get("stopPrice") if kind == "STOP" else o.get("price")
            out.append(
                Order(
                    str(o["orderId"]),
                    acct,
                    self._symbol(str(o["contract"])),
                    "BUY" if o.get("action") == "Buy" else "SELL",
                    int(o["qty"]),
                    kind,  # type: ignore[arg-type]
                    _d(px) if px is not None else None,
                    "WORKING",
                    role="STOP" if kind == "STOP" else "TP" if kind == "LIMIT" else "ENTRY",
                )
            )
        return out

    async def get_balance(self, acct: str) -> Decimal:
        a = await self._acct(acct)
        if a.get("netLiq") is None or a.get("openPnl") is None:
            raise BrokerError(f"{acct}: no fresh pricing for open positions (P&L null)")
        return _d(a["netLiq"]) - _d(a["openPnl"])

    async def open_pnl(self, acct: str) -> Decimal:
        a = await self._acct(acct)
        if a.get("openPnl") is None:
            raise BrokerError(f"{acct}: open P&L unavailable")
        return _d(a["openPnl"])

    # ---------- writes ----------
    async def place_bracket(self, acct: str, req: BracketRequest) -> BracketAck:
        body: dict[str, Any] = {
            "instrument": self.tv_symbols.get(req.symbol, req.symbol),
            "action": "buy" if req.side == "BUY" else "sell",
            "qty": req.qty,
            "orderType": req.entry_type.lower(),
            "takeProfit": float(req.take_profit),
            "stopLoss": float(req.stop),
            "clOrdId": req.client_id[:64],
        }
        if req.entry_type == "LIMIT":
            body["limitPrice"] = float(req.limit_price or 0)
        data = await self._req("POST", f"/accounts/{acct}/orders/place", body, mutation=True)
        r = data.get("response", {})
        if not all(k in r for k in ("orderId", "oso1Id", "oso2Id")):
            raise UnconfirmedError(f"bracket ack incomplete: {r}")
        b = str(r["orderId"])
        self._roles.update({b: (b, "ENTRY"), str(r["oso2Id"]): (b, "STOP"), str(r["oso1Id"]): (b, "TP")})
        return BracketAck(b, b, str(r["oso2Id"]), str(r["oso1Id"]))

    async def modify_stop(self, acct: str, order_id: str, price: Decimal) -> bool:
        try:
            await self._req(
                "PUT", f"/accounts/{acct}/orders/{order_id}/change", {"stopPrice": float(price)}, mutation=True
            )
        except BrokerError:
            return False
        await asyncio.sleep(self.verify_delay_s)  # Tradovate can reject ~1 s after accepting
        for o in await self.get_orders(acct):
            if o.order_id == order_id:
                return o.price is not None and o.price == price
        return False

    async def cancel_all(self, acct: str) -> None:
        await self._req("POST", f"/accounts/{acct}/orders/cancel", {}, mutation=True)

    async def flatten(self, acct: str) -> None:
        await self._req("POST", f"/accounts/{acct}/positions/flatten", {}, mutation=True)

    def _fill(self, acct: str, f: dict[str, Any]) -> Fill | None:
        key = str(f.get("executionId") or f.get("fillId") or f.get("id"))
        if key in self._seen or f.get("action") not in ("Buy", "Sell"):
            return None
        self._seen.add(key)
        oid = str(f["orderId"])
        bracket, role = self._roles.get(oid, (None, "EXTERNAL"))
        at = datetime.fromisoformat(str(f["timestamp"]).replace("Z", "+00:00"))
        side: Side = "BUY" if f["action"] == "Buy" else "SELL"
        return Fill(
            acct,
            oid,
            bracket,
            role,
            self._symbol(str(f.get("instrument", ""))),
            side,
            int(f["qty"]),
            _d(f["price"]),
            at,
        )

    async def poll_fills(self, acct: str) -> list[Fill]:
        data = await self._req("GET", f"/accounts/{acct}/fills")
        return [x for f in data.get("data", []) if (x := self._fill(acct, f)) is not None]

    async def stream_fills(self) -> AsyncIterator[Fill]:
        """Polls each linked account's fills (180 req/min limit → poll_s ≥ 5 s)."""
        first = True
        while True:
            for a in await self._snapshot():
                for fill in await self.poll_fills(str(a["name"])):
                    if not first:  # fills already on the books at startup are history, not new events
                        yield fill
            first = False
            await asyncio.sleep(self.poll_s)

    async def stream_pnl(self) -> AsyncIterator[PnlUpdate]:
        """Polls the snapshot (docs: poll at five seconds or slower)."""
        while True:
            for a in await self._snapshot():
                nl, op = a.get("netLiq"), a.get("openPnl")
                if nl is not None and op is not None:
                    yield PnlUpdate(str(a["name"]), _d(nl) - _d(op), _d(op), datetime.now(UTC))
            await asyncio.sleep(self.poll_s)

    async def health(self) -> AdapterHealth:
        try:
            await self._req("GET", "/status")
        except BrokerError as e:
            return AdapterHealth(False, str(e))
        return AdapterHealth(True, "crosstrade")
