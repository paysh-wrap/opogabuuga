"""D151: TradingAgents ADVISOR in front of the D142-D150 strategies (pure, no I/O, no network).

The day's call is the stored BiasDecision (bias/ledger.py reads it, bias/policy.combine turns it into a Call); this
module only compares that call with a signal's side. GATE may block only a DISAGREE while the ledger is proven
(bias/ledger.proven: ≥ min_calls scored calls, Wilson lower bound ≥ the threshold, Brier < 0.25). Tighten-only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.bias.policy import Call, LedgerStats, Policy

Verdict = Literal["AGREE", "DISAGREE", "NEUTRAL", "NO_CALL"]


@dataclass(frozen=True)
class AdvisorParams:
    mode: str  # OFF | ADVISORY | GATE
    min_accuracy: float  # strategy.ai_gate_min_accuracy (D77)
    min_calls: int = Policy(bias_matters=True).min_calls


@dataclass(frozen=True)
class AdvisorVerdict:
    verdict: Verdict
    prob_up: float | None
    call_direction: int  # +1 / −1 / 0 (0 also for NO_CALL)
    ledger_proven: bool
    blocks: bool  # True only for GATE + proven + DISAGREE

    def as_features(self, label: str | None, mode: str) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "prob_up": self.prob_up,
            "label": label,
            "ledger_proven": self.ledger_proven,
            "mode": mode,
            "blocks": self.blocks,
        }


def is_proven(st: LedgerStats | None, cfg: AdvisorParams) -> bool:
    return st is not None and st.n >= cfg.min_calls and st.wilson_lb >= cfg.min_accuracy and st.brier < 0.25


def advisor_verdict(
    call: Call | None, signal_direction: int, ledger_state: LedgerStats | None, cfg: AdvisorParams
) -> AdvisorVerdict:
    """AGREE / DISAGREE / NEUTRAL / NO_CALL of today's call vs the signal side (+1 long, −1 short)."""
    proven = is_proven(ledger_state, cfg)
    if call is None:
        return AdvisorVerdict("NO_CALL", None, 0, proven, False)
    if call.direction == 0:
        v: Verdict = "NEUTRAL"
    elif call.direction == signal_direction:
        v = "AGREE"
    else:
        v = "DISAGREE"
    blocks = v == "DISAGREE" and cfg.mode == "GATE" and proven
    return AdvisorVerdict(v, call.prob_up, call.direction, proven, blocks)
