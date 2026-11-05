"""Live-Readiness Checklist (§1.5). PURE. LIVE orders need EVERY item true; the default is always PAPER."""

from __future__ import annotations

from dataclasses import dataclass

LIVE_PHRASE = "I ACCEPT LIVE RISK"
MIN_PARITY_SESSIONS = 20


@dataclass(frozen=True)
class LiveInputs:
    env_allow_live: bool  # PAYTIENCE_ALLOW_LIVE=true on the server
    toggle_on: bool  # Settings toggle (stored, typed phrase required to turn on)
    broker_name: str
    broker_reads_back: bool  # positions/fills read-back (CrossTrade yes, TradersPost no)
    broker_connected: bool
    parity_sessions: int  # sessions where Python ↔ Pine bridge ↔ original indicators matched
    unconfirmed_verify: int  # rule values still marked VERIFY
    preflight_ok: bool
    rules_error: str | None


def checklist(i: LiveInputs) -> list[dict[str, object]]:
    items = [
        ("server_allows_live", i.env_allow_live, "set PAYTIENCE_ALLOW_LIVE=true on the server"),
        ("live_toggle", i.toggle_on, f"turn on the live toggle and type {LIVE_PHRASE!r}"),
        ("broker_reads_back", i.broker_reads_back, f"{i.broker_name} cannot report positions — use CrossTrade"),
        ("broker_connected", i.broker_connected, "connect CrossTrade on the Connections page"),
        (
            "indicator_parity",
            i.parity_sessions >= MIN_PARITY_SESSIONS,
            f"{i.parity_sessions}/{MIN_PARITY_SESSIONS} sessions of indicator parity",
        ),
        ("rules_verified", i.unconfirmed_verify == 0, f"{i.unconfirmed_verify} rule values still marked VERIFY"),
        ("preflight", i.preflight_ok, "pre-flight must pass"),
        ("rules_loaded", i.rules_error is None, i.rules_error or ""),
    ]
    return [{"check": n, "ok": ok, "detail": "" if ok else d} for n, ok, d in items]


def live_allowed(i: LiveInputs) -> bool:
    return all(c["ok"] for c in checklist(i))


def can_enable_toggle(phrase: str) -> bool:
    return phrase.strip() == LIVE_PHRASE
