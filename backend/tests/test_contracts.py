from datetime import date
from types import SimpleNamespace

import pytest

from app.config import load_rules
from app.contracts import front_contract, is_roll_day, order_contract, roll_date, third_friday


@pytest.mark.parametrize(
    ("today", "want"),
    [
        (date(2026, 11, 5), "MGCZ6"),
        (date(2026, 11, 25), "MGCZ6"),
        (date(2026, 11, 26), "MGCG7"),  # 2 business days before Dec FND (Nov 30)
        (date(2026, 12, 31), "MGCG7"),
        (date(2027, 1, 27), "MGCJ7"),  # Feb FND = Jan 29 2027 → roll Jan 27
    ],
)
def test_gold_front_month(today: date, want: str) -> None:
    assert front_contract("MGC", "GJMQVZ", "fnd", 2, today) == want


@pytest.mark.parametrize(
    ("today", "want"),
    [
        (date(2026, 11, 5), "MNQZ6"),
        (date(2026, 12, 9), "MNQZ6"),
        (date(2026, 12, 10), "MNQH7"),  # 8 days before Dec 18 expiry
        (date(2027, 3, 10), "MNQH7"),
        (date(2027, 3, 11), "MNQM7"),  # Mar 19 expiry − 8
    ],
)
def test_nasdaq_front_month(today: date, want: str) -> None:
    assert front_contract("MNQ", "HMUZ", "expiry", 8, today) == want


def test_helpers() -> None:
    assert third_friday(2026, 12) == date(2026, 12, 18)
    assert roll_date(2027, 1, "fnd", 0) == date(2026, 12, 31)  # January contract: FND in prior December
    assert is_roll_day("HMUZ", "expiry", 8, date(2026, 12, 10))
    assert not is_roll_day("HMUZ", "expiry", 8, date(2026, 12, 11))
    with pytest.raises(ValueError, match="roll rule"):
        roll_date(2026, 12, "bogus", 1)
    with pytest.raises(ValueError, match="months"):
        front_contract("MGC", "ZZ1", "fnd", 2, date(2026, 1, 1))


def test_order_contract() -> None:
    assert order_contract("MGC", None, date(2026, 11, 5)) is None
    pinned = SimpleNamespace(months="GJMQVZ", roll="fnd", roll_days=2, override="MGCG7")
    assert order_contract("MGC", pinned, date(2026, 11, 5)) == "MGCG7"


def test_every_plan_trades_real_contracts() -> None:
    from pathlib import Path

    for f in sorted(Path(__file__).resolve().parents[2].joinpath("config/rules").glob("*.yaml")):
        rules = load_rules(f).rules
        for k in ("MGC", "MNQ"):
            c = order_contract(k, rules.instruments[k].contract, date(2026, 11, 5))
            assert c is not None and not c.endswith("!"), (f.name, k, c)
