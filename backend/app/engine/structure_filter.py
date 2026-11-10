"""D76: composes the pure OB + SMT indicators into one verdict for a NOISE / PM_FADE entry. PURE. Closed bars only.
Can only BLOCK. The anchor stop is informational (shadow) — it is returned only when tighter than the fixed stop."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.config import StructureFilterCfg
from app.indicators.bars import Bar
from app.indicators.order_block import ObConfig, anchor_stop, blocked_by_opposing, find_blocks
from app.indicators.smt import SmtConfig, blocked_by_smt, find_smt


@dataclass(frozen=True)
class StructureVerdict:
    veto: str | None  # "OB_BLOCK" | "SMT_BLOCK" | None
    anchor_stop: Decimal | None


def _agg(bars: Sequence[Bar], n: int) -> list[Bar]:
    if n <= 1:
        return list(bars)
    out: list[Bar] = []
    for i in range(0, len(bars) - n + 1, n):
        g = bars[i : i + n]
        out.append(Bar(g[0].open_ms, g[-1].close_ms, g[0].o, max(x.h for x in g), min(x.l for x in g), g[-1].c))
    return out


def evaluate(
    cfg: StructureFilterCfg,
    sign: int,
    price: Decimal,
    fixed_stop: Decimal,
    tick: Decimal,
    mnq: Sequence[Bar],
    mes: Sequence[Bar] | None,
) -> StructureVerdict:
    """`mnq`/`mes`: closed 1-minute bars up to and including the decision bar (oldest first)."""
    obs = find_blocks(_agg(mnq, cfg.ob_tf_min), ObConfig(body_atr=cfg.ob_body_atr, swing_bars=cfg.ob_swing_bars))
    veto: str | None = None
    if cfg.ob_filter and blocked_by_opposing(sign, price, obs, cfg.ob_dist_pts) is not None:
        veto = "OB_BLOCK"
    if veto is None and cfg.smt_filter and mes:
        have = {b.open_ms for b in mes}
        a = [b for b in mnq if b.open_ms in have]
        bm = {b.open_ms: b for b in mes}
        b2 = [bm[x.open_ms] for x in a]
        sc = SmtConfig(cfg.smt_lookback, cfg.smt_valid_bars)
        if len(a) > cfg.smt_lookback and blocked_by_smt(sign, find_smt(a, b2, sc), len(a) - 1, sc) is not None:
            veto = "SMT_BLOCK"
    anchored = anchor_stop(sign, price, fixed_stop, obs, cfg.anchor_buffer_pts, tick)
    return StructureVerdict(veto, anchored if anchored != fixed_stop else None)


__all__ = ["StructureVerdict", "evaluate"]
