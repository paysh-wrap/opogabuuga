"""D89: Lucid's official payout-eligibility consistency rule (pure functions)."""

from datetime import datetime
from decimal import Decimal as D
from zoneinfo import ZoneInfo

from app.risk.consistency import (
    ConsistencyLimits,
    consistency_percentage,
    live_day_stop_hit,
    payout_consistency,
    payout_consistency_text,
    payout_limit,
    payout_rule_applies,
)

NY = ZoneInfo("America/New_York")
CUTOFF = datetime(2025, 11, 28, 15, 0, tzinfo=NY)


def test_formula_matches_lucid_example():  # $1,000 / $4,000 = 25%
    days = [D(1000), D(1000), D(1000), D(1000)]
    assert consistency_percentage(days) == D(25)
    c = payout_consistency(days, D(40))
    assert c.eligible and c.pct == D(25) and c.still_needed == 0


def test_losing_days_count_in_account_profit_and_no_profit_is_not_eligible():
    assert consistency_percentage([D(1000), D(-200), D(600)]) == D(1000) / D(1400) * 100
    assert consistency_percentage([]) is None and consistency_percentage([D(-5), D(-1)]) is None
    c = payout_consistency([D(-5)], D(40))
    assert not c.eligible and c.pct is None and c.needed_cycle_profit == 0 and c.still_needed == 0
    assert "No profitable day" in payout_consistency_text(c)


def test_exactly_at_the_limit_is_eligible_and_just_above_is_not():  # VERIFY in DECISIONS D89
    assert payout_consistency([D(400), D(300), D(300)], D(40)).eligible  # 400 / 1000 = 40%
    over = payout_consistency([D(401), D(300), D(299)], D(40))
    assert not over.eligible


def test_what_is_still_needed():
    c = payout_consistency([D(1000), D(500)], D(40))  # largest 1,000 → needs 2,500 cycle profit
    assert not c.eligible and c.needed_cycle_profit == D(2500) and c.still_needed == D(1000)
    assert c.limit == D(40)
    t = payout_consistency_text(c)
    assert "$2,500.00" in t and "$1,000.00 more" in t and "40%" in t
    # keep trading exactly what is needed -> eligible at the limit
    assert payout_consistency([D(1000), D(500), D(1000)], D(40)).eligible
    assert "Consistency met" in payout_consistency_text(
        payout_consistency([D(100), D(100), D(100), D(100), D(100)], D(40))
    )
    # a non-whole-dollar need rounds UP to the next whole dollar (never under-states)
    assert payout_consistency([D(100)], D(35)).needed_cycle_profit == D(286)  # 285.71...


def test_limit_40_after_cutoff_35_on_or_before_unknown_stricter():
    args = (D(40), D(35), CUTOFF)
    assert payout_limit(datetime(2025, 11, 28, 15, 0, 1, tzinfo=NY), *args) == (D(40), True)
    assert payout_limit(CUTOFF, *args) == (D(35), True)  # "on or before"
    assert payout_limit(datetime(2025, 1, 5, tzinfo=NY), *args) == (D(35), True)
    assert payout_limit(None, *args) == (D(35), False)  # unknown -> stricter, flag for VERIFY
    assert payout_limit(None, D(35), D(40), CUTOFF) == (D(35), False)  # stricter whichever way round


def test_rule_applies_on_funded_only():
    assert payout_rule_applies("FUNDED", True)
    assert not payout_rule_applies("LIVE", True)  # gone once promoted to Live
    assert not payout_rule_applies("EVAL", True)
    assert not payout_rule_applies("FUNDED", False)


def test_live_day_stop_hit_n6():
    lim = ConsistencyLimits(D(500), D("437.50"))
    assert not live_day_stop_hit(D(300), D(100), lim)
    assert live_day_stop_hit(D(300), D("137.50"), lim)  # exactly the day stop
    assert live_day_stop_hit(D(0), D(600), lim)
