"""D151: pure TradingAgents advisor verdict."""

from __future__ import annotations

import pytest

from app.bias.advisor import AdvisorParams, advisor_verdict, is_proven
from app.bias.policy import Call, LedgerStats

PROVEN = LedgerStats(n=40, hit_rate=0.85, brier=0.2, wilson_lb=0.72)
UNPROVEN = LedgerStats(n=10, hit_rate=0.9, brier=0.1, wilson_lb=0.6)
GATE = AdvisorParams("GATE", 0.70, 30)  # old name: D176 an advisor never blocks, whatever the mode string
ADVISORY = AdvisorParams("ADVISORY", 0.70, 30)


@pytest.mark.parametrize(
    ("call_dir", "side", "want"),
    [
        (1, 1, "AGREE"),
        (-1, 1, "DISAGREE"),
        (0, 1, "NEUTRAL"),
        (-1, -1, "AGREE"),
        (1, -1, "DISAGREE"),
        (0, -1, "NEUTRAL"),
    ],
)
def test_verdicts_and_short_mirror(call_dir, side, want):
    v = advisor_verdict(Call(call_dir, 0.5 + 0.05 * call_dir, False), side, PROVEN, GATE)
    assert v.verdict == want and v.call_direction == call_dir and v.ledger_proven
    assert v.blocks is False  # D176: advice only, a DISAGREE never blocks
    assert v.as_features("Buy", "GATE")["verdict"] == want


def test_no_call_never_blocks():
    v = advisor_verdict(None, 1, PROVEN, GATE)
    assert v.verdict == "NO_CALL" and v.prob_up is None and not v.blocks


def test_unproven_or_advisory_never_blocks():
    c = Call(-1, 0.4, True)
    assert not advisor_verdict(c, 1, UNPROVEN, GATE).blocks
    assert not advisor_verdict(c, 1, None, GATE).ledger_proven
    assert not advisor_verdict(c, 1, PROVEN, ADVISORY).blocks


def test_is_proven_edges():
    assert is_proven(PROVEN, GATE)
    assert not is_proven(LedgerStats(40, 0.9, 0.25, 0.8), GATE)  # Brier must be < 0.25
    assert not is_proven(LedgerStats(40, 0.9, 0.1, 0.69), GATE)
