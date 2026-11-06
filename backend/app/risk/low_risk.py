"""Lower-risk mode (user button): risk per trade halved, more losing trades allowed per day. PURE.

Halves every risk % (standard + Evaluation Mode tiers, floor/middle/ceiling) and the $ caps; doubles the daily
loss-streak stop and max trades. The daily $ loss stays about the same (2 × half = 1 full), so DLL/MLL safety is
unchanged; all firm rules, gates, R:R, stops and kill switch are untouched.
"""

from __future__ import annotations

from decimal import Decimal

from app.config import RulesConfig

HALF = Decimal("0.5")


def apply_low_risk(r: RulesConfig) -> RulesConfig:
    i, em = r.internal, r.eval_mode
    internal = i.model_copy(
        update={
            "risk_pct_by_score": {k: v * HALF for k, v in i.risk_pct_by_score.items()},
            "risk_pct_floor": i.risk_pct_floor * HALF,
            "risk_pct_middle": i.risk_pct_middle * HALF,
            "risk_pct_ceiling": i.risk_pct_ceiling * HALF,
            "max_risk_usd": i.max_risk_usd * HALF if i.max_risk_usd is not None else None,
            "max_consecutive_losses_per_day": i.max_consecutive_losses_per_day * 2,
            # D51 (user): Lower risk mode allows its own limit (7/day) — never fewer than normal mode (max 3/day)
            "max_trades_per_day": max(i.max_trades_per_day, i.low_risk_max_trades_per_day),
        }
    )
    eval_mode = em.model_copy(
        update={
            "risk_pct_by_score": {k: v * HALF for k, v in em.risk_pct_by_score.items()},
            "risk_pct_floor": em.risk_pct_floor * HALF,
            "risk_pct_middle": em.risk_pct_middle * HALF,
            "risk_pct_ceiling": em.risk_pct_ceiling * HALF,
            "max_risk_usd": em.max_risk_usd * HALF,
        }
    )
    return r.model_copy(update={"internal": internal, "eval_mode": eval_mode})


def apply_intraday_windows(r: RulesConfig) -> RulesConfig:
    """D37 H1: in normal Intraday mode (low risk, 1:1 and scalp all OFF) each market trades only its
    intraday_windows (best hours). Other modes keep the full windows so their trade count is unchanged."""
    if r.one_to_one_mode.enabled or r.scalp_mode.enabled:
        return r
    inst = {
        k: v.model_copy(update={"windows": v.intraday_windows}) if v.intraday_windows else v
        for k, v in r.instruments.items()
    }
    return r.model_copy(update={"instruments": inst})


def retire_short_modes(r: RulesConfig) -> RulesConfig:
    """D43 (user): Scalp and 1:1 strategies are retired — both lost money after the realistic-fill fix (D39).
    Forced OFF whatever a plan file or an older stored setting says, so only Intraday (+ Lower risk) can trade."""
    return r.model_copy(
        update={
            "one_to_one_mode": r.one_to_one_mode.model_copy(update={"enabled": False}),
            "scalp_mode": r.scalp_mode.model_copy(update={"enabled": False}),
            "eval_mode": r.eval_mode.model_copy(update={"one_to_one": False}),
        }
    )
