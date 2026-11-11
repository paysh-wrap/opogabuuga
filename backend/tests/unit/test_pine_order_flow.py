"""D95: static checks on pine/Paytience_OrderFlow.pine (no Pine compiler in CI)."""

import re
from pathlib import Path

from app.engine.order_flow import KINDS
from tests.unit.test_pine_static import _scan

SRC = (Path(__file__).resolve().parents[3] / "pine" / "Paytience_OrderFlow.pine").read_text(encoding="utf-8")


def test_header_attribution_and_contract():
    assert SRC.startswith("//@version=6\n") and "PERSONAL USE ONLY" in SRC and "UNVERIFIED" in SRC
    assert '"-ORDER_FLOW-" + dir' in SRC and '"secret":"\' + secret' in SRC  # id ends -DIRECTION (D12)
    assert set(re.findall(r'kind := "([A-Z_]+)"', SRC)) == KINDS
    assert "\t" not in SRC and "request.security_lower_tf" in SRC and "barstate.isconfirmed" in SRC


def test_brackets_and_quotes_balanced():
    stmt = ""
    for ln in (x for x in SRC.splitlines() if x.strip() and not x.lstrip().startswith("//")):
        code, open_str = _scan(ln)
        assert not open_str, ln
        stmt += code
        if (
            stmt.count("(") == stmt.count(")")
            and stmt.count("[") == stmt.count("]")
            and stmt.count("{") == stmt.count("}")
        ):
            stmt = ""
    assert stmt == ""


def test_d96_markets_guard():
    assert 'syminfo.root != "MNQ" and syminfo.root != "MGC"' in SRC and "MGC1!" in SRC
