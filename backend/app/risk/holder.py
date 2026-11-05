"""Holds the effective rules for the running app. Refreshed after every settings save (applies to the next NEW
trade). If stored settings no longer validate, `error` is set and trading must stay blocked (§1.9)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import LoadedRules, RulesConfig
from app.risk.settings_store import SettingsError, effective
from app.settings import REPO_ROOT

RULES_DIR = REPO_ROOT / "config" / "rules"


@dataclass
class RulesHolder:
    base: LoadedRules
    rules: RulesConfig = field(init=False)
    eval_mode_on: bool = False
    standard_version: int = 0
    firm_version: int = 0
    verified_paths: list[str] = field(default_factory=list)
    error: str | None = None
    low_risk: bool = False
    plan: str = ""  # file stem of the loaded rules (config/rules/<plan>.yaml)

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
        if not self._load_plan(s):
            return  # error set: trading stays blocked
        try:
            eff = effective(s, self.base)
        except SettingsError as e:
            self.error = f"stored settings are invalid: {e}"
            return
        self.rules, self.eval_mode_on = eff.rules, eff.eval_mode_on
        self._apply_instrument_toggles(s)
        from app.automation.state import get_setting
        from app.risk.low_risk import apply_low_risk

        self.low_risk = bool(get_setting(s, "risk.low_risk", False))
        if self.low_risk:
            self.rules = apply_low_risk(self.rules)
        self.standard_version, self.firm_version, self.verified_paths = (
            eff.standard_version,
            eff.firm_version,
            eff.verified_paths,
        )
        self.error = None

    def _apply_instrument_toggles(self, s: Session) -> None:
        """UI market buttons (Gold / Nasdaq / US30 / S&P): AppSetting "instruments.enabled" = {symbol: bool}."""
        from app.automation.state import get_setting

        tog = get_setting(s, "instruments.enabled")
        if not isinstance(tog, dict):
            return
        inst = {
            k: v.model_copy(update={"enabled": bool(tog[k])}) if k in tog else v
            for k, v in self.rules.instruments.items()
        }
        self.rules = self.rules.model_copy(update={"instruments": inst})

    def _load_plan(self, s: Session) -> bool:
        """The selected Lucid plan (AppSetting "rules.plan" = file stem in config/rules/) becomes the base rules."""
        from app.automation.state import get_setting
        from app.config import load_rules

        plan = get_setting(s, "rules.plan")
        if not isinstance(plan, str) or not plan or plan == self.plan:
            return True
        path = RULES_DIR / f"{plan}.yaml"
        if not path.is_file() or path.parent != RULES_DIR:
            self.error = f"rule plan {plan!r} not found"
            return False
        self.base, self.plan = load_rules(path), plan
        self.rules = self.base.rules
        return True
