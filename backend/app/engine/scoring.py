"""Score (§6) — decides SIZE, not direction. Weights come from config (tunable within §17.2 bounds).

Normalised so the maximum attainable score is 100. Optional items (session-open C1, SMT) count only when their
weight > 0 (allowed only after the §16.6 addition gate).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

D0, D100 = Decimal(0), Decimal(100)


@dataclass(frozen=True)
class ScoreInputs:
    cisd_before_c2_close: bool
    choch_after_sweep: bool
    bos_after_sweep: bool
    osc: Decimal | None
    own_tp_rate: Decimal | None  # None → fewer than the minimum samples
    bias_aligned: bool
    htf_agrees: bool
    session_open_c1: bool = False
    smt_divergence: bool = False
    bias_known: bool = True  # False on a NEUTRAL day: no side to agree with (D35)


@dataclass(frozen=True)
class ScoreResult:
    score: Decimal
    earned: dict[str, Decimal]
    max_points: Decimal


def compute_score(
    x: ScoreInputs,
    weights: dict[str, Decimal],
    osc_strength_min: Decimal,
    tp_rate_min: Decimal,
    session_open_weight: Decimal,
    smt_weight: Decimal,
    exclude_unknown: bool = False,
) -> ScoreResult:
    """exclude_unknown (D35): items that cannot be known yet — bias on a NEUTRAL day, own T2 rate before
    tp_rate_min_samples — are left out of the maximum instead of scoring 0. A known miss still scores 0."""
    w = weights
    earned = {
        "cisd_before_c2_close": w["cisd_before_c2_close"] if x.cisd_before_c2_close else D0,
        "structure_after_sweep": w["choch_after_sweep"]
        if x.choch_after_sweep
        else (w["bos_only"] if x.bos_after_sweep else D0),
        "osc_strength": w["osc_strength"] if x.osc is not None and abs(x.osc - 50) >= osc_strength_min else D0,
        "own_tp_rate": w["own_tp_rate"] if x.own_tp_rate is not None and x.own_tp_rate >= tp_rate_min else D0,
        "bias_aligned": w["bias_aligned"] if x.bias_aligned else D0,
        "htf_mso_agrees": w["htf_mso_agrees"] if x.htf_agrees else D0,
    }
    max_points = (
        w["cisd_before_c2_close"]
        + w["choch_after_sweep"]
        + w["osc_strength"]
        + w["own_tp_rate"]
        + w["bias_aligned"]
        + w["htf_mso_agrees"]
    )
    if exclude_unknown:
        if not x.bias_known:
            del earned["bias_aligned"]
            max_points -= w["bias_aligned"]
        if x.own_tp_rate is None:
            del earned["own_tp_rate"]
            max_points -= w["own_tp_rate"]
    if session_open_weight > 0:
        earned["session_open_c1"] = session_open_weight if x.session_open_c1 else D0
        max_points += session_open_weight
    if smt_weight > 0:
        earned["smt"] = smt_weight if x.smt_divergence else D0
        max_points += smt_weight
    total = sum(earned.values(), D0)
    score = (total * D100 / max_points).quantize(Decimal("0.01")) if max_points > 0 else D0
    return ScoreResult(score, earned, max_points)
