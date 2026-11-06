import pytest

from app.market.openbb_feed import parse_output, summarize


def test_summarize_and_errors():
    s = summarize({"MGC": [["2026-11-04", 4073.0], ["2026-11-05", 4072.1]], "MNQ": {"error": "HTTPError"}, "X": []})
    assert s["MGC"]["last"] == 4072.1 and s["MGC"]["change"] == -0.9 and s["MGC"]["series"] == [4073.0, 4072.1]
    assert s["MNQ"] == {"error": "HTTPError"} and s["X"] == {"error": "NO_DATA"}


def test_parse_output():
    assert parse_output('noise\nOBB{"MGC": []}\n') == {"MGC": []}
    with pytest.raises(ValueError):
        parse_output("nothing")
