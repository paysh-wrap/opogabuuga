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


class DrawdownPair(BaseModel):
    """Session 22: same strategy + simulator with an EOD-trailing vs an intraday-trailing loss floor (regular table)."""

    model_config = ConfigDict(frozen=True)
    eod: EraOdds
    intraday: EraOdds


class DrawdownTypes(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: str
    plans: dict[str, DrawdownPair]


class OddsFile(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: int
    study: str
    source: str
    plans: dict[str, dict[str, TableOdds]]
    drawdown_types: DrawdownTypes | None = None  # session 22 (optional: an older file without it still loads)


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


def drawdown_compare(plan_stem: str) -> dict[str, Any]:
    """Session 22 UI payload: EOD vs intraday trailing drawdown for the active plan (`current`, None when not measured)
    plus every measured plan (`rows`), all from config/eval_odds.yaml (D137: no figure is hard-coded in the UI)."""
    f = load_odds()
    dt = f.drawdown_types if f is not None else None
    if dt is None:
        return {"current": None, "rows": [], "source": None, "text": NOT_MEASURED}

    def row(stem: str, d: DrawdownPair) -> dict[str, Any]:
        return {
            "plan": stem,
            "eod": {"pass": d.eod.all.pass_, "bust": d.eod.all.bust, "j_pass": d.eod.j.pass_, "j_bust": d.eod.j.bust},
            "intraday": {
                "pass": d.intraday.all.pass_,
                "bust": d.intraday.all.bust,
                "j_pass": d.intraday.j.pass_,
                "j_bust": d.intraday.j.bust,
            },
        }

    cur = dt.plans.get(plan_stem)
    text = (
        NOT_MEASURED
        if cur is None
        else f"EOD trailing pass {_n(cur.eod.all.pass_)}% / bust {_n(cur.eod.all.bust)}% "
        f"(last 12 mo {_n(cur.eod.j.pass_)}/{_n(cur.eod.j.bust)}) · intraday trailing pass "
        f"{_n(cur.intraday.all.pass_)}% / bust {_n(cur.intraday.all.bust)}% "
        f"(last 12 mo {_n(cur.intraday.j.pass_)}/{_n(cur.intraday.j.bust)})"
    )
    return {
        "current": None if cur is None else row(plan_stem, cur),
        "rows": [row(k, v) for k, v in sorted(dt.plans.items())],
        "source": dt.source,
        "text": text,
    }
