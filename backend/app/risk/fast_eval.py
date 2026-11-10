"""D87 Fast Evaluation. EVAL stage ONLY — enforced here, in pure code, for every caller (non-negotiable 10).

Four independent mechanisms (each has its own switch in `FastEvalCfg`). All of them can only make the app trade
LESS risk-wise than the rule engine allows or add size under strict conditions; none touches the kill switch,
DLL/MLL, gates, R:R, hedge/news/flat rules (those checks still run after sizing). No martingale: after ANY loss the
size returns to the base and never goes above it; there is no pace escalation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from app.config import FastEvalCfg
from app.risk.consistency import ConsistencyLimits
from app.risk.risk_base import money

D100 = Decimal(100)


def fast_eval_effective(stage: str, global_on: bool) -> bool:
    if stage != "EVAL":
        return False  # never on FUNDED or LIVE, whatever the toggle says
    return global_on


@dataclass(frozen=True)
class FastCtx:
    cushion: Decimal  # risk_base = equity incl. open P&L - current MLL
    mll: Decimal  # the loss limit the cushion is measured against
    last_closed_was_loss: bool
    losses_today: int
    trades_in_stage: int
    profit_frac: Decimal = Decimal(0)  # eval profit so far / profit target (negative while under water)


def ladder_extra(cfg: FastEvalCfg, ctx: FastCtx) -> int:
    """Mechanism 1: extra micros = the highest step whose cushion threshold is met; 0 after any loss."""
    if not cfg.ladder.enabled or ctx.last_closed_was_loss or ctx.losses_today > 0 or ctx.mll <= 0:
        return 0
    extra = 0
    for step in cfg.ladder.steps:
        if ctx.cushion >= step.cushion_frac * ctx.mll:
            extra = step.extra
    return extra


def early_active(cfg: FastEvalCfg, ctx: FastCtx) -> bool:
    """Mechanism 3 window: first N trades and/or below the profit share, cushion above threshold, no loss."""
    e = cfg.early
    # every configured window must hold (AND): the early tier is the tighter of the two when both are set
    in_window = (e.first_trades == 0 or ctx.trades_in_stage < e.first_trades) and (
        e.until_profit_frac is None or ctx.profit_frac < e.until_profit_frac
    )
    return (
        e.enabled
        and in_window
        and ctx.mll > 0
        and ctx.cushion >= e.cushion_frac * ctx.mll
        and not ctx.last_closed_was_loss
        and ctx.losses_today == 0
    )


def fast_contracts(cfg: FastEvalCfg, ctx: FastCtx, base: int) -> int:
    """Fixed-size strategies: base size + ladder + early extras, capped by ladder.max_contracts, never below base
    and never above base after a loss (no martingale)."""
    if ctx.last_closed_was_loss or ctx.losses_today > 0:
        return base
    extra = ladder_extra(cfg, ctx) + (cfg.early.extra_contracts if early_active(cfg, ctx) else 0)
    return max(base, min(base + extra, cfg.ladder.max_contracts))


def fast_risk_pct(cfg: FastEvalCfg, ctx: FastCtx, pct: Decimal) -> Decimal:
    """Score-tier strategies (mechanism 3): raise the selected risk % to early.risk_pct inside the early window.
    Never lowers it; never applies after a loss / below the cushion threshold."""
    r = cfg.early.risk_pct
    if r is None or not early_active(cfg, ctx):
        return pct
    return max(pct, r)


def harvest_limits(lim: ConsistencyLimits | None, cfg: FastEvalCfg, profit_target: Decimal) -> ConsistencyLimits | None:
    """Mechanism 2: the day stop can only move DOWN (tighten); the cap is never changed."""
    if lim is None or not cfg.harvest.enabled:
        return lim
    stop = money(cfg.harvest.day_stop_pct_of_target / D100 * profit_target)
    return replace(lim, day_stop=min(lim.day_stop, stop))


def quality_day_block(cfg: FastEvalCfg, day_pnls: Sequence[Decimal]) -> str | None:
    """Mechanism 4: day_pnls = realised P&L of the previous trading days, oldest first. Returns a skip reason."""
    q = cfg.quality_day
    if not q.enabled or not day_pnls:
        return None
    if q.mode == "prev_day":
        return "FAST_EVAL_QUALITY_DAY" if day_pnls[-1] < 0 else None
    window = day_pnls[-q.trailing_days :]
    return "FAST_EVAL_QUALITY_DAY" if sum(window, Decimal(0)) < 0 else None


def effective_fast_cfg(stage: str, global_on: bool, cfg: FastEvalCfg) -> FastEvalCfg | None:
    return cfg if fast_eval_effective(stage, global_on) else None
