"""D137: evaluation pass / bust odds per plan x size table x EOD-toggle state (config/eval_odds.yaml, written from the
research in docs/results/session21/eod_toggle/RESULTS.md). I/O is allowed here (file read); everything is
pydantic-validated and cached. A missing file, an unknown plan/table or a `study` starting with PLACEHOLDER all mean
"not measured yet" -> `odds()` returns None and the UI says so. Nothing in the UI quotes a pass / bust figure that does
not come from this file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ODDS_PATH = Path(__file__).resolve().parents[2] / "config" / "eval_odds.yaml"
TABLES = ("regular", "suggested", "high", "regular_fade_on")
NOT_MEASURED = "not measured yet"


class Era(BaseModel):
    """One era of the study: shares of finished evaluations (percent) and the median days."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)
    pass_: float = Field(alias="pass")
    bust: float
    stuck: float = 0
    open: float = 0
    days: float = 0


class EraOdds(BaseModel):
    """The three eras of one (plan, table, toggle) cell: all = whole study, is = in-sample, j = judged / last 12 mo."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)
    all: Era
    is_: Era = Field(alias="is")
    j: Era


class TableOdds(BaseModel):
    model_config = ConfigDict(frozen=True)
    contracts: int
    brake: str | None = None
    eod_on: EraOdds
    eod_off: EraOdds


class OddsFile(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: int
    study: str
    source: str
    plans: dict[str, dict[str, TableOdds]]


@lru_cache(maxsize=1)
def load_odds(path: Path = ODDS_PATH) -> OddsFile | None:
    """The parsed file, or None when it is missing, invalid or still the placeholder."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        f = OddsFile.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError, TypeError):
        return None
    return None if f.study.startswith("PLACEHOLDER") else f


def odds(plan_stem: str, table: str, eod_on: bool) -> EraOdds | None:
    f = load_odds()
    if f is None:
        return None
    t = f.plans.get(plan_stem, {}).get(table)
    if t is None:
        return None
    return t.eod_on if eod_on else t.eod_off


def table_for(high_risk: bool, suggested_on: bool) -> str:
    """The size table the Strategy page has active (D64 high risk, D127 suggested, else regular)."""
    return "high" if high_risk else "suggested" if suggested_on else "regular"


def _n(x: float) -> str:
    return f"{x:.0f}" if float(x).is_integer() else f"{x:.1f}"


def odds_text(o: EraOdds | None, eod_on: bool) -> str:
    """Short UI text: 'pass 70% / bust 30% · last 12 mo 55/45 · EOD toggle OFF' (or 'not measured yet')."""
    if o is None:
        return NOT_MEASURED
    return (
        f"pass {_n(o.all.pass_)}% / bust {_n(o.all.bust)}% · last 12 mo {_n(o.j.pass_)}/{_n(o.j.bust)} "
        f"· EOD toggle {'ON' if eod_on else 'OFF'}"
    )


def odds_view(plan_stem: str, table: str, eod_on: bool) -> dict[str, Any]:
    """API payload for one cell: always has `text`; numbers are null when not measured."""
    o = odds(plan_stem, table, eod_on)
    return {
        "plan": plan_stem,
        "table": table,
        "eod_on": eod_on,
        "text": odds_text(o, eod_on),
        "pass_pct": None if o is None else o.all.pass_,
        "bust_pct": None if o is None else o.all.bust,
        "last12_pass_pct": None if o is None else o.j.pass_,
        "last12_bust_pct": None if o is None else o.j.bust,
    }
