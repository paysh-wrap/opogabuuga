"""D137: which equity the kill switch watches (pure)."""

from decimal import Decimal as D

import pytest

from app.risk.eod_balance import watched_equity


@pytest.mark.parametrize(
    "dd,closed_only,expected",
    [
        ("eod", False, D(24050)),  # default: balance + open P&L
        ("eod", True, D(25000)),  # D137: EOD account, toggle on: closed balance only
        ("intraday", True, D(24050)),  # intraday accounts are unaffected by the toggle
        ("intraday", False, D(24050)),
    ],
)
def test_watched_equity(dd, closed_only, expected):
    assert watched_equity(D(25000), D(-950), dd, closed_only) == expected
