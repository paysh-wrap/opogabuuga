"""Holds the effective rules for the running app. Refreshed after every settings save (applies to the next NEW
trade). If stored settings no longer validate, `error` is set and trading must stay blocked (§1.9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import LoadedRules, RulesConfig
from app.risk.settings_store import SettingsError, effective
from app.settings import REPO_ROOT

log = structlog.get_logger()
RULES_DIR = REPO_ROOT / "config" / "rules"


@dataclass
class RulesHolder:
    base: LoadedRules
    rules: RulesConfig = field(init=False)
    eval_mode_on: bool = False
    fast_eval_on: bool = False  # D87 (EVAL stage only; pure check in risk/fast_eval)
    standard_version: int = 0
    firm_version: int = 0
    verified_paths: list[str] = field(default_factory=list)
    error: str | None = None
    low_risk: bool = False
    plan: str = ""  # file stem of the loaded rules (config/rules/<plan>.yaml) = the ACTIVE plan (Risk UI edits it)
    # D168: every OTHER plan an account uses is loaded once per refresh (same overlays as the active one)
    plan_rules: dict[str, RulesConfig] = field(default_factory=dict)
    plan_errors: dict[str, str] = field(default_factory=dict)
    _bases: dict[str, LoadedRules] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.rules = self.base.rules

    @property
    def source_text(self) -> str:
        return self.base.source_text

    @property
    def verify_paths(self) -> list[str]:
        """Still-unconfirmed VERIFY values (gold badges)."""
        return [p for p in self.base.verify_paths if p not in self.verified_paths]

    def _overlay(self, s: Session, rules: RulesConfig) -> RulesConfig:
        """Household overlays shared by every plan: instrument buttons, payout settings, low-risk / intraday windows."""
        from app.automation.state import get_setting
        from app.risk.low_risk import apply_intraday_windows, apply_low_risk

        rules = self._apply_instrument_toggles(s, rules)
        rules = self._apply_payout_settings(s, rules)
        return apply_low_risk(rules) if bool(get_setting(s, "risk.low_risk", False)) else apply_intraday_windows(rules)

    def refresh(self, s: Session) -> None:
        if not self._load_plan(s):
            return  # error set: trading stays blocked
        try:
            eff = effective(s, self.base)
        except SettingsError as e:
            self.error = f"stored settings are invalid: {e}"
            return
        from app.risk.low_risk import retire_short_modes

        rules, self.eval_mode_on = retire_short_modes(eff.rules), eff.eval_mode_on
        self.fast_eval_on = eff.fast_eval_on
        try:
            self.rules = self._overlay(s, rules)
        except ValueError as e:  # pydantic ValidationError: stored payout settings invalid → block trading
            self.error = f"stored payout settings are invalid: {e}"
            return
        from app.automation.state import get_setting

        self.low_risk = bool(get_setting(s, "risk.low_risk", False))
        self.standard_version, self.firm_version, self.verified_paths = (
            eff.standard_version,
            eff.firm_version,
            eff.verified_paths,
        )
        self.error = None
        self._refresh_account_plans(s)

    # ---------- D168: per-account plans ----------
    @staticmethod
    def available_plans() -> list[str]:
        return sorted(p.stem for p in RULES_DIR.glob("*.yaml"))

    def plan_for(self, a: Any) -> str:
        """The plan an account uses: its own `plan` field, else inferred from its size, else the active plan."""
        from app.risk.account_plan import resolve_plan

        bal = getattr(a, "starting_balance", None)
        return resolve_plan(getattr(a, "plan", None), bal, self.plan, self.available_plans())

    def _refresh_account_plans(self, s: Session) -> None:
        """Load every other plan the accounts use ONCE (cached in `_bases`); a missing / invalid plan is recorded in
        `plan_errors` — that account's NEW entries stay blocked (no silent fallback to another plan)."""
        from app.models import Account

        needed = {self.plan_for(a) for a in s.execute(select(Account)).scalars()} - {self.plan}
        self.plan_rules, self.plan_errors = {}, {}
        for name in sorted(needed):
            try:
                self.plan_rules[name] = self._build_plan(s, name)
            except (ValueError, SettingsError, OSError) as e:
                self.plan_errors[name] = f"rule plan {name!r} is invalid: {e}"
                log.error("rules.account_plan_invalid", plan=name, error=str(e))

    def ensure_account_plan(self, s: Session, a: Any) -> None:
        """Load just this account's plan if it is not cached yet (account created / plan changed); no full refresh."""
        name = self.plan_for(a)
        if name == self.plan or name in self.plan_rules:
            return
        try:
            self.plan_rules[name] = self._build_plan(s, name)
            self.plan_errors.pop(name, None)
        except (ValueError, SettingsError, OSError) as e:
            self.plan_errors[name] = f"rule plan {name!r} is invalid: {e}"
            log.error("rules.account_plan_invalid", plan=name, error=str(e))

    def _build_plan(self, s: Session, name: str) -> RulesConfig:
        from app.config import load_rules
        from app.risk.low_risk import retire_short_modes

        path = RULES_DIR / f"{name}.yaml"
        if not path.is_file() or path.parent != RULES_DIR:
            raise ValueError(f"rule plan {name!r} not found")
        if name not in self._bases:
            self._bases[name] = load_rules(path)
        eff = effective(s, self._bases[name], apply_firm=False)
        return self._overlay(s, retire_short_modes(eff.rules))

    def rules_for_name(self, s: Session, name: str) -> RulesConfig:
        """Rules of a named plan (used when an account is being created); raises ValueError if unusable."""
        if name == self.plan:
            return self.rules
        return self.plan_rules.get(name) or self._build_plan(s, name)

    def rules_for(self, a: Any) -> RulesConfig:
        """Effective rules for ONE account (its own plan's MLL / DLL / target / consistency / payouts / fast pass).
        Trading paths must call `account_error` first; this returns the active rules only for display when the
        account's plan is unusable."""
        name = self.plan_for(a)
        if name == self.plan:
            return self.rules
        return self.plan_rules.get(name, self.rules)

    def account_error(self, a: Any) -> str | None:
        name = self.plan_for(a)
        if name == self.plan:
            return None
        if name in self.plan_errors:
            return self.plan_errors[name]
        if name not in self.plan_rules:
            return f"rule plan {name!r} is not loaded"
        return None

    def bad_accounts(self, s: Session) -> list[dict[str, str]]:
        """Accounts whose plan is unusable (banner + block)."""
        from app.models import Account

        out = []
        for a in s.execute(select(Account)).scalars():
            e = self.account_error(a)
            if e:
                out.append({"account": a.broker_account_id, "plan": self.plan_for(a), "error": e})
        return out

    def _apply_instrument_toggles(self, s: Session, rules: RulesConfig) -> RulesConfig:
        """UI market buttons (Gold / Nasdaq / US30 / S&P): AppSetting "instruments.enabled" = {symbol: bool}."""
        from app.automation.state import get_setting

        tog = get_setting(s, "instruments.enabled")
        if not isinstance(tog, dict):
            return rules
        inst = {
            k: v.model_copy(update={"enabled": bool(tog[k])}) if k in tog else v for k, v in rules.instruments.items()
        }
        return rules.model_copy(update={"instruments": inst})

    def _apply_payout_settings(self, s: Session, rules: RulesConfig) -> RulesConfig:
        """Payouts page (§14): AppSetting "payouts.settings" = {skim_mode, frequency}. Re-validated by the pydantic
        model on every load; amounts, buffer and caps stay rule values (never editable here)."""
        from app.automation.state import get_setting
        from app.config import PayoutsCfg

        ov = get_setting(s, "payouts.settings")
        if not isinstance(ov, dict):
            return rules
        allowed = ("skim_mode", "frequency", "mode", "min_sessions_between", "min_pct_of_cap")  # D65
        keys = {k: ov[k] for k in allowed if k in ov}
        pc = PayoutsCfg.model_validate({**rules.payouts.model_dump(), **keys})
        return rules.model_copy(update={"payouts": pc})

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
