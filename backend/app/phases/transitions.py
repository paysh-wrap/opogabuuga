"""Stage transitions (§10). Pure: returns the actions the caller must perform (persist, audit, notify)."""

from __future__ import annotations

from dataclasses import dataclass, field

ORDER = {"EVAL": 0, "FUNDED": 1, "LIVE": 2}


@dataclass(frozen=True)
class TransitionPlan:
    allowed: bool
    reason: str = ""
    actions: list[str] = field(default_factory=list)


def plan_transition(
    from_stage: str | None, to_stage: str, eval_mode_override: str, any_household_live: bool, closed_by_firm: bool
) -> TransitionPlan:
    if to_stage not in ORDER:
        return TransitionPlan(False, f"unknown stage {to_stage}")
    if closed_by_firm:
        return TransitionPlan(False, "account flattened/closed by the firm — never re-enter")
    actions = ["reset_mll", "record_stage_history", "audit", "notify", "disarm"]
    if from_stage == "EVAL" and to_stage != "EVAL":
        actions.append("eval_mode_off")  # §10: Evaluation Mode forced OFF away from EVAL
        if eval_mode_override != "inherit":
            actions.append("eval_mode_override_reset")
    if to_stage == "LIVE" or any_household_live:
        actions.append("block_household_sim_accounts")  # §10: any LIVE account blocks household sim accounts
    actions.append("semi_auto_sessions_reset")  # §13: first 5 sessions of each stage are OFF/SEMI only
    return TransitionPlan(True, "", actions)
