"""D179: loads config/early_closes.yaml (missing / unreadable file = no early closes, nothing changes)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.risk.early_close import EarlyClose

PATH = Path(__file__).resolve().parents[2] / "config" / "early_closes.yaml"


@lru_cache(maxsize=1)
def table() -> EarlyClose | None:
    try:
        raw = yaml.safe_load(PATH.read_text(encoding="utf-8")) or {}
        days = {str(k): str(v["close_et"]) for k, v in (raw.get("days") or {}).items()}
        return EarlyClose(days, int(raw["no_entry_before_min"]), int(raw["flatten_before_min"]))
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError):
        return None
