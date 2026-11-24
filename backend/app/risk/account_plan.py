"""D168: which rule plan an account uses (PURE). An explicit `plan` wins; otherwise it is inferred from the account
size (starting balance) inside the active plan's family (lucid_pro_25k → lucid_pro_<size>k); else the active plan."""

from __future__ import annotations

import re
from collections.abc import Iterable
from decimal import Decimal

_SIZE = re.compile(r"_(\d+)k$")


def plan_family(plan: str) -> str:
    return _SIZE.sub("", plan)


def plan_size(plan: str) -> Decimal | None:
    m = _SIZE.search(plan)
    return Decimal(m.group(1)) * 1000 if m else None


def infer_plan(balance: Decimal | None, active: str, available: Iterable[str]) -> str:
    if balance is None or balance <= 0:
        return active
    cand = f"{plan_family(active)}_{int(balance / 1000)}k"
    if Decimal(int(balance / 1000)) * 1000 == balance and cand in set(available):
        return cand
    return active


def resolve_plan(explicit: str | None, balance: Decimal | None, active: str, available: Iterable[str]) -> str:
    return explicit if explicit else infer_plan(balance, active, available)
