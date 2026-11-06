import pytest

from app.automation.controller import override_allows


@pytest.mark.parametrize(
    ("override", "actor", "mode", "manual", "ok"),
    [
        (None, "automation", "FULL", False, True),
        ("SEMI", "automation", "FULL", False, False),  # SEMI account never auto-executed
        ("OFF", "automation", "FULL", False, False),
        ("SEMI", "user", "FULL", False, True),  # approval in FULL is for the SEMI accounts…
        (None, "user", "FULL", False, False),  # …the others were already auto-executed
        (None, "user", "SEMI", False, True),
        ("SEMI", "user", "SEMI", False, True),
        ("OFF", "user", "SEMI", False, False),  # OFF: approvals never trade it
        ("OFF", "user", "OFF", True, True),  # manual ticket = the user's explicit order
    ],
)
def test_override_only_more_restrictive(override, actor, mode, manual, ok):
    assert override_allows(override, actor, mode, manual) is ok
