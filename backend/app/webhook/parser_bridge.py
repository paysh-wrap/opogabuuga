"""Parse Paytience_Bridge alert bodies into WebhookPayload + map TradingView tickers to our instruments."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.config import RulesConfig
from app.webhook.schemas import FRACTAL_EVENTS, MSO_EVENTS, WebhookPayload
from app.webhook.security import Rejection

_CONTRACT = re.compile(r"^([A-Z0-9]{2,4}?)([FGHJKMNQUVXZ])(\d{1,4})$")


def map_symbol(ticker: str, rules: RulesConfig) -> str | None:
    """'MNQ1!', 'MNQZ2026', 'MNQZ6', 'CME_MINI:MNQ1!' → 'MNQ'. Unknown → None."""
    t = ticker.upper().split(":")[-1].strip()
    for sym, inst in rules.instruments.items():
        if t in (sym, inst.tv_symbol.upper()):
            return sym
    if t.endswith("1!") or t.endswith("2!"):
        root = t[:-2]
        return root if root in rules.instruments else None
    m = _CONTRACT.match(t)
    if m and m.group(1) in rules.instruments:
        return m.group(1)
    return None


def parse(body: bytes, rules: RulesConfig) -> tuple[WebhookPayload | None, Rejection | None]:
    if len(body) > rules.webhook.max_body_bytes:
        return None, Rejection(413, "TOO_LARGE", "payload too large")
    try:
        data = json.loads(body.decode("utf-8"), parse_float=str, parse_int=int)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, Rejection(422, "BAD_JSON", "body is not valid JSON")
    if not isinstance(data, dict):
        return None, Rejection(422, "BAD_JSON", "body must be a JSON object")
    try:
        p = WebhookPayload.model_validate(data)
    except ValidationError as e:
        first = e.errors()[0]
        loc = ".".join(str(x) for x in first["loc"])
        return None, Rejection(422, "BAD_PAYLOAD", f"{loc}: {first['msg']}"[:200])
    if p.event == "HEARTBEAT" and p.price is None:
        return None, Rejection(422, "BAD_PAYLOAD", "HEARTBEAT needs price")
    if p.event in FRACTAL_EVENTS and (p.fractal is None or p.direction == "NONE"):
        return None, Rejection(422, "BAD_PAYLOAD", f"{p.event} needs fractal fields and a direction")
    if p.event in MSO_EVENTS and (p.mso is None or p.direction == "NONE"):
        return None, Rejection(422, "BAD_PAYLOAD", f"{p.event} needs mso fields and a direction")
    return p, None
