"""D76 LunqFX: optional OB + SMT structure check on a LunqFX PASS. PURE (no I/O). Closed bars only.
It is an ADDED optional filter: the G1-G8 gates and the TradePlan builder are unchanged. It can only
- veto a PASS (OB_BLOCK / SMT_BLOCK), and
- (anchor_stop) tighten the stop to just beyond a same-side order block, only if the rebuilt R:R stays inside
  rr_min..rr_max. It never widens risk and never moves the target."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from app.config import LunqStructureCfg
from app.engine import structure_filter as SF
from app.engine.trade_plan import TradePlan
from app.indicators.bars import Bar


@dataclass(frozen=True)
class LunqStructureResult:
    veto: str | None  # applied veto (None when off or nothing blocks)
    plan: TradePlan  # plan to trade (original unless anchor_stop applied)
    features: dict[str, object]  # shadow log


def check(
    cfg: LunqStructureCfg,
    plan: TradePlan,
    rr_min: Decimal,
    rr_max: Decimal,
    tick: Decimal,
    mnq: Sequence[Bar],
    mes: Sequence[Bar] | None,
    mso_enabled: bool = False,
) -> LunqStructureResult:
    v = SF.evaluate(cfg.filter, plan.direction.sign, plan.entry, plan.stop, tick, mnq, mes, mso_enabled)
    anchored: TradePlan | None = None
    if v.anchor_stop is not None:
        risk = abs(plan.entry - v.anchor_stop)
        tighter = Decimal(0) < risk < plan.risk_pts
        if tighter:
            rr = abs(plan.take_profit - plan.entry) / risk
            if rr_min <= rr <= rr_max:
                anchored = replace(plan, stop=v.anchor_stop, risk_pts=risk, rr=rr)
    feats: dict[str, object] = {
        "lunq_structure": {
            "would_block": v.veto,
            "anchor_stop": None if anchored is None else str(anchored.stop),
            "anchor_rr": None if anchored is None else str(anchored.rr),
        }
    }
    use = anchored if (cfg.anchor_stop and anchored is not None) else plan
    return LunqStructureResult(v.veto if cfg.enabled else None, use, feats)


__all__ = ["LunqStructureResult", "check"]
