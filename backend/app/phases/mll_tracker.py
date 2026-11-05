"""Maximum Loss Limit tracker (§10). Pure. EOD accounts trail only on the once-per-session EOD call."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

DrawdownType = Literal["eod", "intraday"]


@dataclass
class MllState:
    drawdown_type: DrawdownType
    max_loss: Decimal
    peak: Decimal
    mll: Decimal
    lock_trigger: Decimal | None
    lock_level: Decimal | None
    locked: bool = False

    @classmethod
    def start(
        cls,
        balance: Decimal,
        drawdown_type: DrawdownType,
        max_loss: Decimal,
        lock_trigger: Decimal | None,
        lock_level: Decimal | None,
    ) -> MllState:
        return cls(drawdown_type, max_loss, balance, balance - max_loss, lock_trigger, lock_level)


def update_mll(st: MllState, equity: Decimal, eod: bool = False) -> None:
    """§10 reference implementation (binding)."""
    if st.locked:
        return
    if st.drawdown_type == "intraday" or (st.drawdown_type == "eod" and eod):
        st.peak = max(st.peak, equity)
        st.mll = st.peak - st.max_loss
        if st.lock_trigger and st.peak >= st.lock_trigger:
            assert st.lock_level is not None
            st.mll, st.locked = st.lock_level, True


def breached(st: MllState, equity: Decimal) -> bool:
    """Any touch of the MLL — intraday too, even on EOD accounts — is a breach (§9)."""
    return equity <= st.mll


def mll_distance(st: MllState, equity: Decimal) -> Decimal:
    return equity - st.mll
