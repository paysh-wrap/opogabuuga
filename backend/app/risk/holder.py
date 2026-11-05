"""Holds the effective rules for the running app. Refreshed after every settings save (applies to the next NEW
trade). If stored settings no longer validate, `error` is set and trading must stay blocked (§1.9)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import LoadedRules, RulesConfig
from app.risk.settings_store import SettingsError, effective


@dataclass
class RulesHolder:
    base: LoadedRules
    rules: RulesConfig = field(init=False)
    eval_mode_on: bool = False
    standard_version: int = 0
    firm_version: int = 0
    verified_paths: list[str] = field(default_factory=list)
    error: str | None = None

    def __post_init__(self) -> None:
        self.rules = self.base.rules

    @property
    def source_text(self) -> str:
        return self.base.source_text

    @property
    def verify_paths(self) -> list[str]:
        """Still-unconfirmed VERIFY values (gold badges)."""
        return [p for p in self.base.verify_paths if p not in self.verified_paths]

    def refresh(self, s: Session) -> None:
        try:
            eff = effective(s, self.base)
        except SettingsError as e:
            self.error = f"stored settings are invalid: {e}"
            return
        self.rules, self.eval_mode_on = eff.rules, eff.eval_mode_on
        self.standard_version, self.firm_version, self.verified_paths = (
            eff.standard_version,
            eff.firm_version,
            eff.verified_paths,
        )
        self.error = None
