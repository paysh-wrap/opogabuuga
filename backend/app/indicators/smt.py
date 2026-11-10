"""SMT divergence between two correlated instruments (MNQ vs MES). PURE, Decimal, closed bars only.

Bars of both instruments must be aligned (same open_ms). At bar i (confirmed on ITS close — event time = that bar's close_ms):
  bearish SMT: A closes a new `lookback`-bar high while B does not (or the reverse)  -> weakness, blocks LONGs
  bullish SMT: A closes a new `lookback`-bar low while B does not (or the reverse)   -> strength, blocks SHORTs
"new high" = close_i > max(close of the previous `lookback` bars) (only past bars are used).
A signal stays in force for `valid_bars` bars after its confirmation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.indicators.bars import Bar


@dataclass(frozen=True)
class SmtConfig:
    lookback: int = 20
    valid_bars: int = 15


@dataclass(frozen=True)
class SmtSignal:
    bearish: bool
    index: int
    confirm_ms: int


def find_smt(a: Sequence[Bar], b: Sequence[Bar], cfg: SmtConfig) -> list[SmtSignal]:
    n = min(len(a), len(b))
    out: list[SmtSignal] = []
    for i in range(cfg.lookback, n):
        if a[i].open_ms != b[i].open_ms:
            raise ValueError("bars not aligned")
        pa = [x.c for x in a[i - cfg.lookback : i]]
        pb = [x.c for x in b[i - cfg.lookback : i]]
        a_hi, b_hi = a[i].c > max(pa), b[i].c > max(pb)
        a_lo, b_lo = a[i].c < min(pa), b[i].c < min(pb)
        if a_hi != b_hi:
            out.append(SmtSignal(True, i, a[i].close_ms))
        elif a_lo != b_lo:
            out.append(SmtSignal(False, i, a[i].close_ms))
    return out


def blocked_by_smt(direction_sign: int, signals: Sequence[SmtSignal], last_index: int, cfg: SmtConfig) -> SmtSignal | None:
    """FILTER: LONG blocked by a recent bearish SMT, SHORT by a recent bullish SMT."""
    for s in reversed(signals):
        if last_index - s.index > cfg.valid_bars:
            break
        if (direction_sign > 0 and s.bearish) or (direction_sign < 0 and not s.bearish):
            return s
    return None
