"""Reconcile (§4, §13): broker positions vs the positions our open trades expect. Pure.

Mismatch → pause the account (never auto-resumes). A position we didn't open (manual trade) is counted in risk;
if it is opposite to another household position in the same super-group it's a hedge → loud alert."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mismatch:
    account: str
    symbol: str
    expected: int
    actual: int
    kind: str  # MISSING | UNEXPECTED | SIZE


def reconcile(expected: dict[tuple[str, str], int], actual: dict[tuple[str, str], int]) -> list[Mismatch]:
    out = []
    for key in sorted(set(expected) | set(actual)):
        e, a = expected.get(key, 0), actual.get(key, 0)
        if e == a:
            continue
        kind = "UNEXPECTED" if e == 0 else "MISSING" if a == 0 else "SIZE"
        out.append(Mismatch(key[0], key[1], e, a, kind))
    return out
