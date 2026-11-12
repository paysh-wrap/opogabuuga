"""Live-Readiness Checklist (§1.5). PURE. LIVE orders need EVERY item true; the default is always PAPER."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

LIVE_PHRASE = "I ACCEPT LIVE RISK"
# B1 (user 2026-11-12): the old `indicator_parity` item (LunqFX/MSO, removed in D105/D91) was never written, so live
# could never pass. It is replaced by the `live.readiness_check` toggle: "paper_sessions" (default) needs this many
# completed paper sessions of the active strategies without an error banner; "off" skips ONLY that one item.
MIN_PAPER_SESSIONS = 20
READINESS_MODES = ("paper_sessions", "off")


@dataclass(frozen=True)
class PaperDay:
    session: date  # CME session date
    paper_trades: int  # closed PAPER trades of the active strategies in that session
    errors: int  # error banners that session (an order rejection always raises one)


def clean_paper_sessions(days: Iterable[PaperDay], today: date) -> int:
    """Completed sessions (before today) in which an active strategy traded on paper and nothing raised an error."""
    return sum(1 for d in days if d.session < today and d.paper_trades > 0 and d.errors == 0)


@dataclass(frozen=True)
class LiveInputs:
    env_allow_live: bool  # PAYTIENCE_ALLOW_LIVE=true on the server
    toggle_on: bool  # Settings toggle (stored, typed phrase required to turn on)
    broker_name: str
    broker_reads_back: bool  # positions/fills read-back (CrossTrade yes)
    broker_connected: bool
    paper_sessions: int  # clean completed paper sessions of the active strategies (clean_paper_sessions)
    unconfirmed_verify: int  # rule values still marked VERIFY
    preflight_ok: bool
    rules_error: str | None
    readiness_mode: str = "paper_sessions"  # B1 toggle; anything unknown counts as "paper_sessions" (fails closed)


def readiness_skipped(i: LiveInputs) -> bool:
    return i.readiness_mode == "off"


def checklist(i: LiveInputs) -> list[dict[str, object]]:
    items = [
        ("server_allows_live", i.env_allow_live, "set PAYTIENCE_ALLOW_LIVE=true on the server"),
        ("live_toggle", i.toggle_on, f"turn on the live toggle and type {LIVE_PHRASE!r}"),
        ("broker_reads_back", i.broker_reads_back, f"{i.broker_name} cannot report positions — use CrossTrade"),
        ("broker_connected", i.broker_connected, "connect CrossTrade on the Connections page"),
        (
            "paper_sessions",
            readiness_skipped(i) or i.paper_sessions >= MIN_PAPER_SESSIONS,
            f"{min(i.paper_sessions, MIN_PAPER_SESSIONS)}/{MIN_PAPER_SESSIONS} clean paper sessions, active strategies",
        ),
        ("rules_verified", i.unconfirmed_verify == 0, f"{i.unconfirmed_verify} rule values still marked VERIFY"),
        ("preflight", i.preflight_ok, "pre-flight must pass"),
        ("rules_loaded", i.rules_error is None, i.rules_error or ""),
    ]
    out: list[dict[str, object]] = [{"check": n, "ok": ok, "detail": "" if ok else d} for n, ok, d in items]
    if readiness_skipped(i):
        out[4]["skipped"] = True
        out[4]["detail"] = "skipped: readiness check turned OFF by the user (audit-logged)"
    return out


def live_allowed(i: LiveInputs) -> bool:
    return all(c["ok"] for c in checklist(i))


def can_enable_toggle(phrase: str) -> bool:
    return phrase.strip() == LIVE_PHRASE
