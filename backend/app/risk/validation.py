"""Risk-settings validation (§11). Server-side source of truth; the UI mirrors it. Pure."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.clock import parse_hhmm
from app.config import RulesConfig
from app.risk.risk_base import money

D100 = Decimal(100)


@dataclass
class Validation:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    needs_second_confirmation: bool = False
    dll_tests: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def dll_two_loss_test(
    base: Decimal, ceiling: Decimal, floor: Decimal, max_risk_usd: Decimal | None, margin: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """First loss at ceiling, second at floor on the reduced base, + 2×margin (§11). Returns (l1, l2, total)."""

    def cap(x: Decimal) -> Decimal:
        x = money(x)
        return min(x, max_risk_usd) if max_risk_usd is not None else x

    l1 = cap(ceiling * base)
    l2 = cap(floor * (base - l1))
    return l1, l2, money(l1 + l2 + 2 * margin)


def max_base_for_stage(rules: RulesConfig, stage: str) -> Decimal:
    """EVAL EOD: $1,000 + day stop ($437.50) = $1,437.50; FUNDED: the $3,000 cushion (§11)."""
    if stage == "EVAL":
        day_stop = (
            (rules.eval.consistency_max_day_pct - rules.internal.consistency_day_stop_buffer_pct)
            / D100
            * rules.eval.profit_target
        )
        return money(rules.eval.max_loss_limit + day_stop)
    return money(rules.internal.cushion_target_balance - rules.funded.lock_level)


def validate(rules: RulesConfig) -> Validation:
    v = Validation()
    i, em = rules.internal, rules.eval_mode
    lo, hi = i.risk_pct_absolute_bounds
    for name, pcts in (
        ("standard", (i.risk_pct_floor, i.risk_pct_middle, i.risk_pct_ceiling)),
        ("evaluation", (em.risk_pct_floor, em.risk_pct_middle, em.risk_pct_ceiling)),
    ):
        f, m, c = pcts
        if not (f <= m <= c):
            v.errors.append(f"{name}: floor ≤ middle ≤ ceiling required")
        for p in pcts:
            if not (lo <= p <= hi):
                v.errors.append(f"{name}: {p:.0%} outside {lo:.0%}–{hi:.0%}")
            if p > Decimal("0.11"):
                v.needs_second_confirmation = True
                if name == "standard":
                    v.warnings.append(f"standard risk {p:.0%} > 11% (red warning)")
    for tiers in (i.risk_pct_by_score, em.risk_pct_by_score):
        if any(p > hi for p in tiers.values()):
            v.errors.append("a score tier exceeds the absolute risk bound")
    # never looser than firm rules
    if i.max_consecutive_losses_per_day < 1:
        v.errors.append("max consecutive losses per day must be ≥ 1")
    if i.kill_switch_mll_distance <= 0:
        v.errors.append("kill switch distance must be > 0")
    if i.internal_max_micros > rules.max_contracts.micros:
        v.errors.append("internal max micros exceeds the firm maximum")
    if rules.drawdown_guard.runner_trail_r > Decimal(2):
        v.errors.append("runner trail must be ≤ 2.0R")
    if i.day_lockin_r < Decimal(1):
        v.errors.append("day lock-in must be ≥ 1.0R")
    if i.consistency_day_stop_buffer_pct <= 0:
        v.errors.append("consistency day stop must be below the consistency cap")
    if i.cushion_target_balance < rules.funded.payout.buffer + rules.funded.payout.min_request:
        v.errors.append("cushion must be ≥ payout buffer + minimum payout")
    reopen, flat = parse_hhmm(rules.session.reopen), parse_hhmm(rules.session.flat_by)
    for a, b in i.windows:
        ta, tb = parse_hhmm(a), parse_hhmm(b)
        if not (ta < tb and (tb <= flat or ta >= reopen)):
            v.errors.append(f"window {a}–{b} must be inside the session and before flat time")
    if not (parse_hhmm(i.auto_flatten) < parse_hhmm(i.hard_flat) < flat):
        v.errors.append("auto-flatten < hard flat < firm flat time required")
    # DLL two-loss test at the largest risk base each stage can have
    margin = i.dll_safety_margin
    for label, stage, ceil_, floor_, cap in (
        ("funded", "FUNDED", i.risk_pct_ceiling, i.risk_pct_floor, i.max_risk_usd),
        ("eval_standard", "EVAL", i.risk_pct_ceiling, i.risk_pct_floor, i.max_risk_usd),
        ("eval_mode", "EVAL", em.risk_pct_ceiling, em.risk_pct_floor, em.max_risk_usd),
    ):
        base = max_base_for_stage(rules, stage)
        dll = rules.funded.daily_loss_limit if stage == "FUNDED" else rules.eval.daily_loss_limit
        l1, l2, total = dll_two_loss_test(base, ceil_, floor_, cap, margin)
        v.dll_tests[label] = {
            "base": str(base),
            "loss1": str(l1),
            "loss2": str(l2),
            "total": str(total),
            "dll": str(dll),
        }
        if total > dll:
            v.errors.append(f"DLL test {label}: {l1} + {l2} + 2×{margin} = {total} > {dll}")
    return v
