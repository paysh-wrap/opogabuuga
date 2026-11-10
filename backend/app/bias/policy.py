"""Bias gating policy (proposal, aibias). PURE — no I/O, no clock.

Two noisy daily forecasters (TradingAgents rating, Vibe-Trading outlook) are combined into ONE call per market,
scored afterwards against the session's real open→close direction (calibration ledger), and allowed to BLOCK a
side only when (a) the market's policy says the bias matters (MGC yes, MNQ no — D53 hindsight split), (b) both
tools agree strongly, and (c) the ledger proves the combined call is accurate (Wilson lower bound ≥ gate_min_acc
over ≥ min_calls scored calls). Otherwise the call is ADVISORY: both sides stay open (score-only use at most).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

TA_SIDE = {"BUY": 1, "OVERWEIGHT": 1, "HOLD": 0, "UNDERWEIGHT": -1, "SELL": -1}
TA_STRONG = {"BUY", "SELL"}
VT_SIDE = {"LONG": 1, "NEUTRAL": 0, "SHORT": -1}


@dataclass(frozen=True)
class Call:
    direction: int  # +1 long, -1 short, 0 none
    prob_up: float  # calibrated-ish P(close > open), shrunk toward 0.5
    agree_strong: bool


@dataclass(frozen=True)
class Policy:
    bias_matters: bool  # per market: MGC True, MNQ False
    min_calls: int = 30
    gate_min_acc: float = 0.60  # Wilson lower bound required to let the bias block
    vt_min_conf: int = 60
    shrink: float = 0.5  # weight kept from the raw tool probability (rest → 0.5 prior)


def combine(ta_raw: str | None, vt_dir: str | None, vt_conf: int | None, pol: Policy) -> Call:
    t = TA_SIDE.get((ta_raw or "").strip().upper(), 0)
    v = VT_SIDE.get((vt_dir or "").upper(), 0)
    conf = vt_conf or 0
    p_ta = 0.5 + 0.1 * t * (2 if (ta_raw or "").strip().upper() in TA_STRONG else 1)
    p_vt = 0.5 + v * (conf / 100 - 0.5) if v and conf > 50 else 0.5
    p = 0.5 + pol.shrink * ((p_ta + p_vt) / 2 - 0.5)
    strong = t != 0 and t == v and (ta_raw or "").strip().upper() in TA_STRONG and conf >= pol.vt_min_conf
    d = 1 if p > 0.5 else -1 if p < 0.5 else 0
    return Call(d, round(p, 4), strong)


def score(prob_up: float, direction: int, outcome_up: bool) -> tuple[int | None, float]:
    """(hit or None when the call had no direction, Brier score) for one session."""
    y = 1.0 if outcome_up else 0.0
    hit = None if direction == 0 else int((direction > 0) == outcome_up)
    return hit, round((prob_up - y) ** 2, 6)


def wilson_lower(hits: float, n: int, z: float = 1.645) -> float:
    if n == 0:
        return 0.0
    ph = hits / n
    den = 1 + z * z / n
    c = ph + z * z / (2 * n)
    r = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return (c - r) / den


@dataclass(frozen=True)
class LedgerStats:
    n: int
    hit_rate: float
    brier: float
    wilson_lb: float


def ledger_stats(rows: Sequence[tuple[int | None, float]], window: int = 60) -> LedgerStats:
    rows = list(rows)[-window:]
    hits = [h for h, _ in rows if h is not None]
    n = len(hits)
    hr = sum(hits) / n if n else 0.0
    br = sum(b for _, b in rows) / len(rows) if rows else 0.25
    return LedgerStats(n, round(hr, 4), round(br, 4), round(wilson_lower(sum(hits), n), 4))


def gate(call: Call, stats: LedgerStats, pol: Policy) -> tuple[str, str]:
    """→ (mapped bias for the engine, reason). Blocks a side ONLY when every condition holds."""
    if not pol.bias_matters:
        return "NEUTRAL", "ADVISORY_MARKET"  # MNQ: direction-of-day doesn't change win rate
    if not call.agree_strong or call.direction == 0:
        return "NEUTRAL", "ADVISORY_NO_AGREEMENT"
    if stats.n < pol.min_calls:
        return "NEUTRAL", "ADVISORY_WARMUP"
    if stats.wilson_lb < pol.gate_min_acc or stats.brier >= 0.25:
        return "NEUTRAL", "ADVISORY_UNPROVEN"
    return ("LONG_ONLY" if call.direction > 0 else "SHORT_ONLY"), "GATED"
