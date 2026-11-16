"""BRUNI STRUCTURE risk overlays (docs/BRUNI_RULES.md F2/F3/F5), OFF by default, tighten-only, BRUNI only. PURE.

No Kelly (F4: prop accounts use fixed risk) and no VAM (F7) — not built on purpose.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal


def autocorr_strength(conditional_wr: Decimal, unconditional_wr: Decimal) -> tuple[int, str]:
    """F2: sign (+1 positive: overall > after-a-loss; −1 negative; 0 none) and strength from the gap in win-rate
    points: 0–2 NONE, 3–4 WEAK, 5–6 SOLID, 7–8 STRONG, 9+ EXTREME (suspect an error)."""
    gap = unconditional_wr - conditional_wr
    a = abs(gap)
    strength = "NONE" if a < 3 else "WEAK" if a < 5 else "SOLID" if a < 7 else "STRONG" if a < 9 else "EXTREME"
    sign = 0 if strength == "NONE" else (1 if gap > 0 else -1)
    return sign, strength


def autocorr_multiplier(
    conditional_wr: Decimal | None,
    unconditional_wr: Decimal | None,
    last_won: bool | None,
    cut: Mapping[str, Decimal],
) -> Decimal:
    """F3, tighten-only: POSITIVE autocorrelation → after a LOSS trade smaller (cut[strength]); NEGATIVE → after a
    WIN smaller. Never above 1 (the 'raise after a win' half is not built: the Lucid-fit size is the ceiling).
    EXTREME (suspect data) and missing stats → 1."""
    if conditional_wr is None or unconditional_wr is None or last_won is None:
        return Decimal(1)
    sign, strength = autocorr_strength(conditional_wr, unconditional_wr)
    if sign == 0 or strength == "EXTREME":
        return Decimal(1)
    shrink = (sign > 0 and not last_won) or (sign < 0 and last_won)
    return min(Decimal(1), cut.get(strength, Decimal(1))) if shrink else Decimal(1)


def shield_account(eligible: Sequence[int], iso_week: int, used_this_week: int | None) -> int | None:
    """F5 drawdown shield: ONE active account per week — the one already used this week, else rotate by week."""
    if not eligible:
        return None
    if used_this_week is not None:
        return used_this_week if used_this_week in eligible else None
    ids = sorted(eligible)
    return ids[iso_week % len(ids)]
