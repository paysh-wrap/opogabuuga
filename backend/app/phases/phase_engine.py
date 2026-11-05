"""Phase engine (§10): per-stage rules, EVAL pass detection, FUNDED → LIVE trigger, inactivity. Pure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.config import RulesConfig
from app.phases.mll_tracker import DrawdownType, MllState
from app.risk.consistency import largest_day_ok, profitable_days


@dataclass(frozen=True)
class StageRules:
    stage: str
    drawdown_type: DrawdownType
    max_loss: Decimal
    lock_trigger: Decimal | None
    lock_level: Decimal | None
    dll: Decimal | None
    consistency_pct: Decimal | None
    news_hard_breach: bool


def stage_rules(
    rules: RulesConfig, stage: str, drawdown_override: str | None = None, dll_enabled: bool = True
) -> StageRules:
    """Firm numbers from config; an account's own drawdown type (D9) overrides the stage default."""
    if stage == "EVAL":
        e = rules.eval
        dd: DrawdownType = drawdown_override or e.drawdown_type  # type: ignore[assignment]
        return StageRules(
            "EVAL",
            dd,
            e.max_loss_limit,
            e.lock_trigger,
            e.lock_level,
            e.daily_loss_limit if dll_enabled else None,
            e.consistency_max_day_pct,
            news_hard_breach=not e.news_allowed_by_firm,
        )
    if stage == "FUNDED":
        f = rules.funded
        dd = drawdown_override or f.drawdown_type  # type: ignore[assignment]
        cons = rules.internal.funded_consistency_pct if rules.internal.consistency_on_funded else None
        return StageRules(
            "FUNDED",
            dd,
            f.max_loss_limit,
            f.lock_trigger,
            f.lock_level,
            f.daily_loss_limit if dll_enabled else None,
            cons,
            news_hard_breach=True,
        )
    if stage == "LIVE":
        lv = rules.live
        dd = drawdown_override or lv.drawdown_type  # type: ignore[assignment]
        return StageRules(
            "LIVE", dd, lv.max_loss_limit, lv.lock_trigger, lv.lock_level, None, None, news_hard_breach=True
        )
    raise ValueError(f"unknown stage {stage!r}")


def new_mll(sr: StageRules, balance: Decimal) -> MllState:
    return MllState.start(balance, sr.drawdown_type, sr.max_loss, sr.lock_trigger, sr.lock_level)


@dataclass(frozen=True)
class EvalProgress:
    profit: Decimal
    target: Decimal
    profitable_days: int
    min_profitable_days: int
    largest_day_ok: bool
    passed: bool
    extra_profit_needed: Decimal  # if the largest day is > 40% of total, how much more total profit is needed


def eval_progress(day_profits: list[Decimal], target: Decimal, consistency_pct: Decimal, min_days: int) -> EvalProgress:
    total = sum(day_profits, Decimal(0))
    pdays = profitable_days(day_profits)
    ok = largest_day_ok(day_profits, consistency_pct)
    biggest = max(day_profits) if day_profits else Decimal(0)
    need_total = biggest * 100 / consistency_pct if consistency_pct else Decimal(0)
    extra = max(Decimal(0), max(need_total, target) - total).quantize(Decimal("0.01"))
    return EvalProgress(
        total,
        target,
        pdays,
        min_days,
        ok,
        passed=total >= target and ok and pdays >= min_days,
        extra_profit_needed=extra,
    )


def funded_live_move_triggered(day_profit: Decimal, rules: RulesConfig) -> bool:
    return day_profit >= rules.funded.max_daily_profit_live_trigger


def inactivity_alert(last_trade_at: datetime | None, now: datetime, alert_days: int) -> bool:
    return last_trade_at is not None and (now - last_trade_at).days >= alert_days
