"""Lucid household account limits (pure). CONFIRMED (Lucid help center, user screenshot 2026-11-24): at most 5 active
FUNDED accounts (all funded plan types combined) and at most 5 active LIVE accounts per household; EVAL accounts are not
counted by those two. Numbers live in config/household.yaml; a missing / unreadable file falls back to the same values."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parents[3] / "config" / "household.yaml"


@dataclass(frozen=True)
class HouseholdLimits:
    max_active_funded: int
    max_active_live: int
    max_total_real: int
    status: str
    source: str


DEFAULT = HouseholdLimits(5, 5, 10, "CONFIRMED", "Lucid help center, user screenshot 2026-11-24")


def load_limits(path: Path = PATH) -> HouseholdLimits:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return HouseholdLimits(
            int(raw["max_active_funded"]),
            int(raw["max_active_live"]),
            int(raw["max_total_real"]),
            str(raw["status"]),
            str(raw["source"]),
        )
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError):
        return DEFAULT


def counts(accounts: list[tuple[str, bool]]) -> dict[str, int]:
    """Active accounts per stage; accounts: (stage, closed_by_firm)."""
    out = {"FUNDED": 0, "LIVE": 0, "EVAL": 0}
    for stage, closed in accounts:
        if not closed:
            out[stage] += 1
    return out


def refusal(limits: HouseholdLimits, stage: str, accounts: list[tuple[str, bool]]) -> str | None:
    """None when one more account of `stage` is allowed, else the message to show. accounts: (stage, closed_by_firm)."""
    if stage not in ("EVAL", "FUNDED", "LIVE"):
        raise ValueError(stage)
    c = counts(accounts)
    if stage == "FUNDED" and c["FUNDED"] >= limits.max_active_funded:
        return (
            f"Lucid allows at most {limits.max_active_funded} active funded accounts per household "
            "(all funded plan types combined, e.g. 3 LucidDirect leaves room for only 2 LucidPro)"
        )
    if stage == "LIVE" and c["LIVE"] >= limits.max_active_live:
        return f"Lucid allows at most {limits.max_active_live} active live accounts per household"
    if sum(c.values()) >= limits.max_total_real:
        return f"Lucid allows at most {limits.max_total_real} accounts in a household (evaluation + funded + live)"
    return None
