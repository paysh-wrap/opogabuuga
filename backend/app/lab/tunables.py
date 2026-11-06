"""§17.2 TUNABLE_PARAMS registry (PURE). The Lab may only ever change these keys, inside these bounds, by at most
max_param_step_pct of the range per proposal. Everything else — pillars (§17.1), firm rules, risk %, Evaluation Mode,
cooldown, lock-in, payout keys, windows, R:R window — is rejected here and by tests."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D
from typing import Any


@dataclass(frozen=True)
class Tunable:
    lo: D
    hi: D
    step: D  # one neighbour move
    is_int: bool = False


TUNABLE_PARAMS: dict[str, Tunable] = {
    "score.min_score": Tunable(D(55), D(70), D(3), True),
    "score.neutral_min_score": Tunable(D(70), D(85), D(3), True),
    "score.osc_strength_min": Tunable(D(10), D(30), D(5), True),
    "score.tp_rate_min": Tunable(D("0.35"), D("0.55"), D("0.05")),
    "score.div_lookback_bars": Tunable(D(3), D(12), D(1), True),
    "filters.c1_min_range_atr": Tunable(D("0.4"), D("1.0"), D("0.1")),
    "trade_plan.stop_buffer_ticks": Tunable(D(2), D(8), D(1), True),
    "trade_plan.min_stop_ticks": Tunable(D(12), D(40), D(4), True),
    "entry.max_wait_bars": Tunable(D(3), D(10), D(1), True),
    "entry.limit_timeout_bars": Tunable(D(2), D(8), D(1), True),
    "internal.no_entry_before_news_min": Tunable(D(10), D(30), D(5), True),
}


def get_path(raw: Any, dotted: str) -> Any:
    cur = raw
    for k in dotted.split("."):
        cur = cur[k] if isinstance(cur, dict) else getattr(cur, k)
    return cur


def current_values(cfg: Any) -> dict[str, D]:
    return {k: D(str(get_path(cfg, k))) for k in TUNABLE_PARAMS}


def validate_diff(diff: dict[str, Any], current: dict[str, D], max_step_pct: D) -> list[str]:
    """Empty list = allowed. Non-tunable keys, out-of-bounds values and oversized steps are all rejected."""
    errs: list[str] = []
    for k, v in diff.items():
        t = TUNABLE_PARAMS.get(k)
        if t is None:
            errs.append(f"{k}: not a Lab tunable (pillar or user setting)")
            continue
        new = D(str(v))
        if not (t.lo <= new <= t.hi):
            errs.append(f"{k}: {new} outside {t.lo}–{t.hi}")
        if t.is_int and new != new.to_integral_value():
            errs.append(f"{k}: must be a whole number")
        old = current.get(k)
        if old is not None and abs(new - old) > (t.hi - t.lo) * max_step_pct / 100:
            errs.append(f"{k}: step {old}→{new} larger than {max_step_pct}% of the range")
    return errs


def neighbours(current: dict[str, D], max_step_pct: D) -> list[dict[str, D]]:
    """One-parameter moves (± one step) that pass validate_diff. Parameters currently outside their bounds (set by
    the user, e.g. an approved plan value) are left alone — the Lab never pulls a user choice back into range."""
    out: list[dict[str, D]] = []
    for k, t in TUNABLE_PARAMS.items():
        cur = current.get(k)
        if cur is None or not (t.lo <= cur <= t.hi):
            continue
        for new in (cur - t.step, cur + t.step):
            d = {k: new}
            if not validate_diff(d, current, max_step_pct):
                out.append(d)
    return out
