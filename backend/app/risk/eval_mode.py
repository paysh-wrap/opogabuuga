"""Evaluation Mode (§11C). EVAL stage ONLY — enforced here, in pure code, for every caller (§1.11)."""

from __future__ import annotations

from typing import Literal

from app.risk.tiers import RiskCfg

Stage = Literal["EVAL", "FUNDED", "LIVE"]
Override = Literal["inherit", "on", "off"]


def eval_mode_effective(stage: str, account_override: str, global_on: bool) -> bool:
    if stage != "EVAL":
        return False  # never on FUNDED or LIVE, whatever the toggles say
    if account_override == "on":
        return True
    if account_override == "off":
        return False
    return global_on


def effective_risk_cfg(
    stage: str, account_override: str, global_on: bool, base_cfg: RiskCfg, eval_cfg: RiskCfg
) -> RiskCfg:
    return eval_cfg if eval_mode_effective(stage, account_override, global_on) else base_cfg


def one_to_one_for(stage: str, account_override: str, global_on: bool, one_to_one_on: bool, eval_1to1: bool) -> bool:
    """D23: 1:1 plans when 1:1 mode is on, or on an EVAL account whose Evaluation Mode is effective + eval 1:1 on."""
    return one_to_one_on or (eval_1to1 and eval_mode_effective(stage, account_override, global_on))
