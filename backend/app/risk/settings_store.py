"""Effective rules = YAML (firm + defaults) ⊕ latest Firm Rules version ⊕ latest My Settings version (§11).

Every save is validated (structural + §11 validation), versioned (author, time, diff, note), audited, applies to
the next NEW trade, and can be rolled back in one click. Pillars and firm rules are NOT editable via My Settings.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import audit
from app.clock import Clock
from app.config import LoadedRules, RulesConfig, load_yaml_decimal
from app.models import RiskProfile, RuleProfile
from app.risk.risk_base import money
from app.risk.validation import Validation, dll_two_loss_test, max_base_for_stage, validate

# §11B "My Settings" — the only keys editable from the Risk page.
MY_SETTINGS_KEYS: frozenset[str] = frozenset(
    {
        *(
            f"internal.{k}"
            for k in (
                "risk_pct_by_score",
                "risk_pct_floor",
                "risk_pct_middle",
                "risk_pct_ceiling",
                "warmup_trades",
                "day_lockin_r",
                "dd_floor_pct",
                "streak_floor_losses",
                "streak_release_wins",
                "pause_below_risk_base",
                "dll_safety_margin",
                "max_trades_per_day",
                "max_consecutive_losses_per_day",
                "internal_max_micros",
                "kill_switch_mll_distance",
                "cushion_target_balance",
                "cap_guard_total_above_buffer",
                "consistency_day_stop_buffer_pct",
                "auto_flatten",
                "hard_flat",
                "windows",
                "no_entry_before_news_min",
                "news_flatten_before_min",
                "adverse_half_enabled",
                "adverse_half_at",
                "consistency_on_funded",
                "funded_consistency_pct",
                "funded_consistency_reference_min",
            )
        ),
        "drawdown_guard.mode",
        "drawdown_guard.runner_trail_r",
        "filters.model_fail_cooldown",
        "trade_plan.min_stop_ticks",
        "one_to_one_mode.enabled",
        "behavior.min_hold_seconds",
        "scalp_mode.enabled",
        "scalp_mode.target_r",
        "scalp_mode.max_hold_s",
        "scalp_mode.runner_r",
        "scalp_mode.trail_r",
        *(
            f"eval_mode.{k}"
            for k in (
                "risk_pct_by_score",
                "risk_pct_floor",
                "risk_pct_middle",
                "risk_pct_ceiling",
                "max_risk_usd",
                "warmup_trades",
                "one_to_one",
            )
        ),
        "payouts.frequency",
        "payouts.skim_mode",
        "automation.auto_resume_after_recovery",
    }
)
# §11A Firm Rules (typed confirmation + note). Pillars stay out of both lists.
FIRM_KEYS_PREFIXES = ("purchase", "max_contracts", "eval.", "funded.", "live", "session", "behavior.", "instruments.")
FIRM_PHRASE = "UPDATE FIRM RULES"
EVAL_MODE_PHRASE = "ENABLE EVALUATION MODE"


class SettingsError(ValueError):
    def __init__(self, errors: list[str], validation: Validation | None = None) -> None:
        super().__init__("; ".join(errors))
        self.errors, self.validation = errors, validation


def _set(raw: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur = raw
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = value


def _get(raw: dict[str, Any], dotted: str) -> Any:
    cur: Any = raw
    for p in dotted.split("."):
        cur = cur[p]
    return cur


def _norm(v: Any) -> Any:
    """JSON-safe form of a YAML/Decimal value for storage and diffs (Decimals → str)."""
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, dict):
        return {str(k): _norm(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    return v


def _denorm(v: Any) -> Any:
    if isinstance(v, str):
        return Decimal(v) if v.replace(".", "", 1).lstrip("-").isdigit() else v
    if isinstance(v, dict):
        return {(int(k) if k.isdigit() else k): _denorm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_denorm(x) for x in v]
    return v


@dataclass
class Effective:
    rules: RulesConfig
    standard_version: int
    firm_version: int
    eval_mode_on: bool
    verified_paths: list[str]


def latest(s: Session, kind: str) -> RiskProfile | None:
    return s.execute(
        select(RiskProfile)
        .where(RiskProfile.kind == kind, RiskProfile.active)
        .order_by(RiskProfile.version.desc())
        .limit(1)
    ).scalar_one_or_none()


def latest_firm(s: Session) -> RuleProfile | None:
    return s.execute(select(RuleProfile).order_by(RuleProfile.version.desc()).limit(1)).scalar_one_or_none()


def merged_raw(base: LoadedRules, firm: dict[str, Any], mine: dict[str, Any]) -> dict[str, Any]:
    raw = copy.deepcopy(load_yaml_decimal(base.source_text))
    for k, v in {**firm, **mine}.items():
        _set(raw, k, _denorm(v))
    return raw


def build(raw: dict[str, Any]) -> tuple[RulesConfig, Validation]:
    try:
        cfg = RulesConfig.model_validate(raw)
    except ValidationError as e:  # also wraps the config's own structural ValueErrors
        raise SettingsError([f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()]) from e
    v = validate(cfg)
    if not v.ok:
        raise SettingsError(v.errors, v)
    return cfg, v


def effective(s: Session, base: LoadedRules) -> Effective:
    std, firm, ev = latest(s, "standard"), latest_firm(s), latest(s, "evaluation")
    lab = latest(s, "lab")  # §17: approved Lab tunables (separate layer; My Settings never contain these keys)
    mine = {**(lab.settings if lab else {}), **(std.settings if std else {})}
    cfg, _ = build(merged_raw(base, firm.body_overrides() if firm else {}, mine))
    verified = list(firm.verified_paths) if firm else []
    return Effective(
        cfg,
        std.version if std else 0,
        firm.version if firm else 0,
        bool(ev.settings.get("enabled")) if ev else False,
        verified,
    )


def save_my_settings(
    s: Session,
    base: LoadedRules,
    clock: Clock,
    author: str,
    changes: dict[str, Any],
    note: str,
    confirm_over_11: bool = False,
) -> tuple[RiskProfile, Validation]:
    bad = sorted(set(changes) - MY_SETTINGS_KEYS)
    if bad:
        raise SettingsError([f"not editable in My Settings: {', '.join(bad)}"])
    cur = latest(s, "standard")
    firm = latest_firm(s)
    merged = {**(cur.settings if cur else {}), **{k: _norm(v) for k, v in changes.items()}}
    cfg, v = build(merged_raw(base, firm.body_overrides() if firm else {}, merged))
    std_over_11 = any(
        p > Decimal("0.11") for p in (cfg.internal.risk_pct_ceiling, *cfg.internal.risk_pct_by_score.values())
    )
    if std_over_11 and not confirm_over_11:
        raise SettingsError(["standard risk above 11% needs a second confirmation"], v)
    before = merged_raw(base, firm.body_overrides() if firm else {}, cur.settings if cur else {})
    diff = {k: {"from": _norm(_get(before, k)), "to": _norm(v2)} for k, v2 in changes.items()}
    version = (s.execute(select(func.max(RiskProfile.version)).where(RiskProfile.kind == "standard")).scalar() or 0) + 1
    if cur:
        cur.active = False
    row = RiskProfile(
        kind="standard", version=version, settings=merged, author=author, note=note, diff=diff, active=True
    )
    s.add(row)
    audit.record(s, clock, author, "risk.settings_saved", f"standard v{version}", {"diff": diff, "note": note})
    s.flush()
    return row, v


def rollback(s: Session, base: LoadedRules, clock: Clock, author: str, version: int) -> RiskProfile:
    target = s.execute(
        select(RiskProfile).where(RiskProfile.kind == "standard", RiskProfile.version == version)
    ).scalar_one_or_none()
    if target is None:
        raise SettingsError([f"no My Settings version {version}"])
    firm = latest_firm(s)
    build(merged_raw(base, firm.body_overrides() if firm else {}, target.settings))  # still valid today?
    cur = latest(s, "standard")
    if cur:
        cur.active = False
    nv = (s.execute(select(func.max(RiskProfile.version)).where(RiskProfile.kind == "standard")).scalar() or 0) + 1
    row = RiskProfile(
        kind="standard",
        version=nv,
        settings=dict(target.settings),
        author=author,
        note=f"rollback to v{version}",
        diff={"rollback_to": version},
        active=True,
    )
    s.add(row)
    audit.record(s, clock, author, "risk.rollback", f"standard v{nv}", {"to": version})
    s.flush()
    return row


def set_eval_mode(
    s: Session, clock: Clock, author: str, enabled: bool, phrase: str, has_eval_accounts: bool
) -> RiskProfile:
    if enabled and not has_eval_accounts:
        raise SettingsError(["no EVAL accounts — Evaluation Mode applies to EVAL accounts only"])
    if enabled and phrase != EVAL_MODE_PHRASE:
        raise SettingsError([f'type "{EVAL_MODE_PHRASE}" to enable'])
    cur = latest(s, "evaluation")
    if cur:
        cur.active = False
    nv = (s.execute(select(func.max(RiskProfile.version)).where(RiskProfile.kind == "evaluation")).scalar() or 0) + 1
    row = RiskProfile(
        kind="evaluation",
        version=nv,
        settings={"enabled": enabled},
        author=author,
        note="enable" if enabled else "disable",
        diff={"enabled": enabled},
        active=True,
    )
    s.add(row)
    audit.record(s, clock, author, "risk.eval_mode", "global", {"enabled": enabled})
    s.flush()
    return row


def save_firm_rules(
    s: Session,
    base: LoadedRules,
    clock: Clock,
    author: str,
    changes: dict[str, Any],
    verify: list[str],
    phrase: str,
    note: str,
) -> RuleProfile:
    if phrase != FIRM_PHRASE:
        raise SettingsError([f'type "{FIRM_PHRASE}" to confirm'])
    if not note.strip():
        raise SettingsError(["a note is required"])
    bad = sorted(k for k in changes if not k.startswith(FIRM_KEYS_PREFIXES))
    unknown_verify = sorted(set(verify) - set(base.verify_paths))
    if bad or unknown_verify:
        raise SettingsError([f"not a firm rule: {', '.join(bad + unknown_verify)}"])
    cur = latest_firm(s)
    overrides = {**(cur.body_overrides() if cur else {}), **{k: _norm(v) for k, v in changes.items()}}
    std = latest(s, "standard")
    build(merged_raw(base, overrides, std.settings if std else {}))
    verified = sorted(set(cur.verified_paths if cur else []) | set(verify))
    nv = (cur.version if cur else 0) + 1
    row = RuleProfile(
        version=nv, body=RuleProfile.encode_overrides(overrides), verified_paths=verified, author=author, note=note
    )
    s.add(row)
    audit.record(
        s, clock, author, "rules.firm_updated", f"v{nv}", {"changes": overrides, "verified": verify, "note": note}
    )
    s.flush()
    return row


# ---------- Impact Preview (§11) ----------
def losses_to_pause(
    start: Decimal, first_pct: Decimal, then_pct: Decimal, cap: Decimal | None, pause_below: Decimal
) -> int:
    base, n = start, 0
    pct = first_pct
    while base >= pause_below and n < 100:
        loss = money(pct * base)
        loss = min(loss, cap) if cap is not None else loss
        base -= loss
        n += 1
        pct = then_pct
    return n


def impact_preview(cfg: RulesConfig, kind: str) -> dict[str, Any]:
    cap: Decimal | None
    if kind == "evaluation":
        c, bases, stage = cfg.eval_mode, (Decimal(1000), Decimal(750), Decimal(500)), "EVAL"
        tiers, floor, ceiling, cap = c.risk_pct_by_score, c.risk_pct_floor, c.risk_pct_ceiling, c.max_risk_usd
    else:
        i = cfg.internal
        bases, stage = (Decimal(1000), Decimal(2000), Decimal(3000)), "FUNDED"
        tiers, floor, ceiling, cap = i.risk_pct_by_score, i.risk_pct_floor, i.risk_pct_ceiling, i.max_risk_usd

    def usd(p: Decimal, b: Decimal) -> str:
        x = money(p * b)
        return str(min(x, cap) if cap is not None else x)

    margin = cfg.internal.dll_safety_margin
    l1, l2, _ = dll_two_loss_test(Decimal(1000), ceiling, floor, cap, margin)
    big = max_base_for_stage(cfg, stage)
    b1, b2, btotal = dll_two_loss_test(big, ceiling, floor, cap, margin)
    return {
        "kind": kind,
        "risk_by_tier": {str(b): {str(s): usd(p, b) for s, p in sorted(tiers.items())} for b in bases},
        "worst_day_at_1000": str(money(l1 + l2)),
        "dll_test_at_max_base": {
            "base": str(big),
            "loss1": str(b1),
            "loss2": str(b2),
            "total": str(btotal),
            "dll": str(cfg.eval.daily_loss_limit),
        },
        "losses_to_pause_from_1000": losses_to_pause(
            Decimal(1000), ceiling, floor, cap, cfg.internal.pause_below_risk_base
        ),
        "monte_carlo": None,  # P(pass ≤15/≤20 sessions), P(MLL hit) need backtest data — Phase 8
        "monte_carlo_note": "Available after the Phase 8 backtest has data.",
    }
