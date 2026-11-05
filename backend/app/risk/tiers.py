"""Risk % selection (§9). Pure. Same function for standard and Evaluation Mode profiles (§11C)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.config import EvalModeCfg, InternalCfg
from app.risk.risk_base import money

Kind = Literal["standard", "evaluation"]


@dataclass(frozen=True)
class RiskCfg:
    kind: Kind
    tiers: tuple[tuple[int, Decimal], ...]  # (min score, pct), ascending
    floor: Decimal
    middle: Decimal
    ceiling: Decimal
    max_risk_usd: Decimal | None
    warmup_trades: int

    def tier(self, score: Decimal) -> Decimal | None:
        pct = None
        for threshold, p in self.tiers:
            if score >= threshold:
                pct = p
        return pct

    @classmethod
    def standard(cls, c: InternalCfg) -> RiskCfg:
        return cls(
            "standard",
            tuple(sorted(c.risk_pct_by_score.items())),
            c.risk_pct_floor,
            c.risk_pct_middle,
            c.risk_pct_ceiling,
            c.max_risk_usd,
            c.warmup_trades,
        )

    @classmethod
    def evaluation(cls, c: EvalModeCfg) -> RiskCfg:
        return cls(
            "evaluation",
            tuple(sorted(c.risk_pct_by_score.items())),
            c.risk_pct_floor,
            c.risk_pct_middle,
            c.risk_pct_ceiling,
            c.max_risk_usd,
            c.warmup_trades,
        )


@dataclass(frozen=True)
class RiskCtx:
    first_trade_today: bool
    last_closed_was_loss: bool
    losses_today: int
    today_net_r: Decimal
    dd_from_peak_base_pct: Decimal  # drawdown of risk base from its peak, in %
    trades_in_stage: int
    consecutive_losses: int  # across days
    wins_since_streak_floor: int  # wins since the streak-floor period started
    in_streak_floor: bool
    low_expectancy_cap: bool = False  # §14: rolling-50 E < 0.20R → floor %


@dataclass(frozen=True)
class FloorRules:
    day_lockin_r: Decimal
    dd_floor_pct: Decimal
    streak_floor_losses: int
    streak_release_wins: int


def streak_floor_active(ctx: RiskCtx, r: FloorRules) -> bool:
    """After N consecutive losses the floor applies until M wins (§9)."""
    if ctx.consecutive_losses >= r.streak_floor_losses:
        return True
    return ctx.in_streak_floor and ctx.wins_since_streak_floor < r.streak_release_wins


def ceiling_allowed(ctx: RiskCtx, cfg: RiskCfg, r: FloorRules) -> bool:
    return (
        ctx.first_trade_today
        and not ctx.last_closed_was_loss
        and not streak_floor_active(ctx, r)
        and ctx.trades_in_stage >= cfg.warmup_trades
    )


def force_floor(ctx: RiskCtx, cfg: RiskCfg, r: FloorRules) -> bool:
    return (
        ctx.losses_today > 0
        or ctx.today_net_r >= r.day_lockin_r
        or ctx.dd_from_peak_base_pct >= r.dd_floor_pct
        or ctx.trades_in_stage < cfg.warmup_trades
        or streak_floor_active(ctx, r)
        or ctx.low_expectancy_cap
    )


def select_risk_pct(score: Decimal, ctx: RiskCtx, cfg: RiskCfg, r: FloorRules) -> Decimal | None:
    """§9 reference implementation (binding)."""
    pct = cfg.tier(score)
    if pct is None:
        return None
    if pct == cfg.ceiling and not ceiling_allowed(ctx, cfg, r):
        pct = cfg.middle
    if force_floor(ctx, cfg, r):
        pct = cfg.floor
    return pct


def risk_usd(pct: Decimal, base: Decimal, cfg: RiskCfg) -> Decimal:
    usd = money(pct * base)
    if cfg.max_risk_usd is not None:
        usd = min(usd, cfg.max_risk_usd)
    return usd
