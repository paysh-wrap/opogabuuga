"""Auto-pause + auto-resume rules (§13). Pure."""

from __future__ import annotations

NEVER_AUTO_RESUME = {
    "KILL_SWITCH",
    "POSITION_MISMATCH",
    "MANUAL_HEDGE",
    "STOP_MODIFY_FAILED",
    "RISK_BASE_BELOW_PAUSE",
    "MLL_BREACH",
    "FLATTEN_FAILED",
    "ORPHAN_POSITION",
}
RESUME_AT_RESET = {"DAY_STOP", "DLL_LIMIT", "CONSECUTIVE_LOSSES", "MAX_TRADES", "CONSISTENCY_DAY_STOP"}
RESUME_ON_HEALTH = {"FEED_STALE", "BROKER_DISCONNECTED", "ORDER_REJECTS"}


def can_auto_resume(
    reason: str,
    *,
    live: bool,
    healthy_heartbeats: int,
    preflight_ok: bool,
    after_reset: bool,
    auto_resume_paper: bool,
    auto_resume_live: bool,
) -> bool:
    if reason in NEVER_AUTO_RESUME:
        return False
    if reason in RESUME_AT_RESET:
        return after_reset  # daily stops reset at 18:00 ET
    if reason in RESUME_ON_HEALTH:
        allowed = auto_resume_live if live else auto_resume_paper
        return allowed and healthy_heartbeats >= 3 and preflight_ok
    return False  # unknown reasons need a human
