"""D156/D157 per-plan "fast pass" (user 2026-11-22; studies docs/results/pass_fastest/beat109/RESULTS.md (150K) and
smaller_plans/RESULTS.md (25K, 100K)). Pure (no I/O).

Only for EVAL-stage accounts (non-negotiable 10: never FUNDED / LIVE) whose own size equals the plan's
the plan cfg's `account_size`, and only while the switch is on. NOISE then trades `noise_contracts` at a
`noise_stop_usd` emergency stop per micro and CANDACE ICT a fixed `candace_contracts`; once the cushion (equity incl.
open P&L - current MLL) is at / below `brake_cushion_usd` they trade the brake sizes (NOISE none when unset).
The size returned here is only the starting size: every Lucid / Paytience check (DLL worst case,
MLL room + kill distance, consistency cap / day stop,
max 1 position, hedge lock, news / flat, firm / internal max) still runs afterwards and can only shrink or skip.
All numbers come from the plan file, never from code."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.config import FastPassCfg, FastPassStep, StrategyCfg

FAST_PASS_STRATEGIES = ("NOISE", "CANDACE_ICT")


@dataclass(frozen=True)
class FastPassSize:
    contracts: int
    stop_usd: Decimal | None  # NOISE emergency stop per micro; None = keep the strategy's own stop (CANDACE)
    braked: bool


def fast_pass_size(
    enabled: bool,
    cfg: FastPassCfg | None,
    stage: str,
    account_size: Decimal,
    strategy: str,
    cushion: Decimal,
    stage_on: bool = False,
) -> FastPassSize | None:
    """The fast-pass starting size, or None when the feature does not apply (then today's sizing is used unchanged).
    D180: FUNDED / LIVE accounts only get it when their own stage switch (`stage_on`) is ON; never EVAL-only again."""
    if not enabled or cfg is None or account_size != cfg.account_size:
        return None
    if stage != "EVAL" and not (stage in ("FUNDED", "LIVE") and stage_on):
        return None
    if strategy not in FAST_PASS_STRATEGIES:
        return None
    if strategy == "NOISE":
        n, braked = _step_size(cfg, cfg.noise_steps, _noise_base(cfg, cushion), cushion)
        return FastPassSize(n, cfg.noise_stop_usd, braked)
    n, braked = _step_size(cfg, cfg.candace_steps, _candace_base(cfg, cushion), cushion)
    return FastPassSize(n, None, braked)


def stage_switch_on(stage: str, funded_on: bool, live_on: bool) -> bool:
    """D180: the per-stage switch that applies to this account's stage (EVAL needs none)."""
    return funded_on if stage == "FUNDED" else live_on if stage == "LIVE" else False


def funded_day_stop_hit(
    on: bool,
    pct: Decimal,
    cfg: FastPassCfg | None,
    stage: str,
    stage_on: bool,
    eval_target: Decimal,
    day_profit: Decimal,
) -> bool:
    """D180 (UNVERIFIED, funded study): 150K only, FUNDED / LIVE with its switch ON: no new entry once today's profit
    reached `pct` of the eval target. Own sub-setting, default OFF. Only ever skips."""
    if not on or cfg is None or cfg.account_size != Decimal(150000) or stage not in ("FUNDED", "LIVE") or not stage_on:
        return False
    return day_profit >= pct / Decimal(100) * eval_target


def late_day_size(
    late_on: bool,
    fast_on: bool,
    cfg: FastPassCfg | None,
    stage: str,
    account_size: Decimal,
    cushion: Decimal,
) -> FastPassSize | None:
    """D166: starting size of the late-day momentum leg, or None = not active (then NO trade is taken). Needs the
    option AND this plan's fast pass ON, EVAL stage, own account size and a `late_contracts` in the plan file; below a
    `late_steps` cushion it trades fewer micros. Every Lucid / Paytience check still runs after (shrink / skip only)."""
    if not (late_on and fast_on) or cfg is None or cfg.late_contracts is None:
        return None
    if stage != "EVAL" or account_size != cfg.account_size:
        return None
    n, braked = _step_size(cfg, cfg.late_steps, cfg.late_contracts, cushion)
    return FastPassSize(n, None, braked)


def _noise_base(cfg: FastPassCfg, cushion: Decimal) -> int:
    """D162 grow (study definition, NOISE only): +1 micro per `noise_grow_per` of cushion beyond the first, capped."""
    if cfg.noise_grow_per is None or cfg.noise_max_contracts is None:
        return cfg.noise_contracts
    extra = int(cushion // cfg.noise_grow_per) - 1
    return min(cfg.noise_max_contracts, cfg.noise_contracts + extra) if extra > 0 else cfg.noise_contracts


def _candace_base(cfg: FastPassCfg, cushion: Decimal) -> int:
    """D163 grow (final_search study, CANDACE only): +1 micro per `candace_grow_per` of cushion beyond first, capped."""
    if cfg.candace_grow_per is None or cfg.candace_max_contracts is None:
        return cfg.candace_contracts
    extra = int(cushion // cfg.candace_grow_per) - 1
    return min(cfg.candace_max_contracts, cfg.candace_contracts + extra) if extra > 0 else cfg.candace_contracts


def fast_pass_day_locked(cfg: FastPassCfg | None, day_profit: Decimal, remaining: Decimal) -> bool:
    """D162 EVAL day lock (same rule as D66 EVAL_DAY_LOCK): True = no new NOISE entry today. Only ever skips."""
    if cfg is None or cfg.day_lock_pct is None:
        return False
    return day_profit > 0 and remaining > 0 and day_profit >= cfg.day_lock_pct * remaining


def fast_pass_lock(cfg: FastPassCfg | None, lock: tuple[Decimal, Decimal] | None) -> tuple[Decimal, Decimal] | None:
    """D162: NOISE profit-lock (trigger, distance) with this plan's own trigger; no lock configured → none."""
    if cfg is None or cfg.noise_lock_trigger_pts is None or lock is None:
        return lock
    return cfg.noise_lock_trigger_pts, lock[1]


def _step_size(cfg: FastPassCfg, steps: tuple[FastPassStep, ...], normal: int, cushion: Decimal) -> tuple[int, bool]:
    """D161: the smallest applicable brake step wins (strict < unless cfg.brake_inclusive); none → the normal size."""
    hit = [x.contracts for x in steps if (cushion <= x.cushion_usd if cfg.brake_inclusive else cushion < x.cushion_usd)]
    return (min(hit), True) if hit else (normal, False)


def plan_fast_pass(st: StrategyCfg, account_size: Decimal) -> tuple[bool, FastPassCfg | None]:
    """The (switch, cfg) pair of the plan whose size equals the account's own size; (False, None) when there is none."""
    for on, cfg in (
        (st.fast_pass_25k, st.fast_pass_25k_cfg),
        (st.fast_pass_50k, st.fast_pass_50k_cfg),
        (st.fast_pass_100k, st.fast_pass_100k_cfg),
        (st.fast_pass_150k, st.fast_pass_150k_cfg),
    ):
        if cfg is not None and cfg.account_size == account_size:
            return on, cfg
    return False, None


def ar_side_by_side(st: StrategyCfg, features: Mapping[str, Any] | None) -> bool:
    """D160: True for an AR-Model Order Flow signal (not the ATR-zone type) while the side-by-side option is on."""
    return st.order_flow and st.order_flow_cfg.ar_side_by_side and "zone" not in (features or {})


def ar_side_cap(size: int, noise: FastPassSize | None) -> int:
    """D160: AR side-by-side size = min(its own size, half of the NOISE fast-pass size when one applies), at least 1.
    Tighten-only: the Lucid fit, DLL / MLL room, consistency and every other pre-trade check still shrink or skip."""
    return size if noise is None else min(size, max(1, noise.contracts // 2))


COMBINED_OF_MAX = 2  # D181: Order Flow adds at most 2 micros beside the main strategy on the same account


def combined_of_size(own: int, firm_cap: int, internal_cap: int, open_qty: int) -> int:
    """D181: Order Flow size in the combined option = min(own, 2, headroom under the account's TOTAL micro cap (firm
    max, internal max; minus the micros already open) and, via ar_side_cap, half the NOISE size); 0 = no headroom."""
    cap = min(firm_cap, internal_cap)  # the fast-pass size caps the MAIN legs; the account cap caps the total
    return max(0, min(own, COMBINED_OF_MAX, cap - open_qty))


def budget_left(cap: Decimal | None, open_usd: Decimal) -> Decimal | None:
    """D181: the per-trade risk budget still free after the risk already open on the account (None = no budget)."""
    return None if cap is None else max(cap - open_usd, Decimal(0))
