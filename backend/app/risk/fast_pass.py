"""D156 "150K fast pass" (user 2026-11-22; study docs/results/pass_fastest/brake150/RESULTS.md row U1). Pure (no I/O).

Only for EVAL-stage accounts (non-negotiable 10: never FUNDED / LIVE) whose own size equals the plan's
`fast_pass_150k_cfg.account_size`, and only while the switch is on. NOISE then trades `noise_contracts` at a
`noise_stop_usd` emergency stop per micro and CANDACE ICT a fixed `candace_contracts`; once the cushion (equity incl.
open P&L - current MLL) is <= `brake_cushion_usd` both trade `brake_contracts`. The size returned here is only the
starting size: every Lucid / Paytience check (DLL worst case, MLL room + kill distance, consistency cap / day stop,
max 1 position, hedge lock, news / flat, firm / internal max) still runs afterwards and can only shrink or skip.
All numbers come from the plan file, never from code."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.config import FastPass150kCfg

FAST_PASS_STRATEGIES = ("NOISE", "CANDACE_ICT")


@dataclass(frozen=True)
class FastPassSize:
    contracts: int
    stop_usd: Decimal | None  # NOISE emergency stop per micro; None = keep the strategy's own stop (CANDACE)
    braked: bool


def fast_pass_size(
    enabled: bool,
    cfg: FastPass150kCfg | None,
    stage: str,
    account_size: Decimal,
    strategy: str,
    cushion: Decimal,
) -> FastPassSize | None:
    """The fast-pass starting size, or None when the feature does not apply (then today's sizing is used unchanged)."""
    if not enabled or cfg is None or stage != "EVAL" or account_size != cfg.account_size:
        return None
    if strategy not in FAST_PASS_STRATEGIES:
        return None
    braked = cushion <= cfg.brake_cushion_usd
    if strategy == "NOISE":
        return FastPassSize(cfg.brake_contracts if braked else cfg.noise_contracts, cfg.noise_stop_usd, braked)
    return FastPassSize(cfg.brake_contracts if braked else cfg.candace_contracts, None, braked)
