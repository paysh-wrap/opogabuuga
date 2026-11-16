"""D145: the OKALA 8020 add-to-winners exception (pure)."""

from decimal import Decimal as D

from app.risk.add_to_winners import AddDecision, OpenLeg, add_allowed


def leg(strategy="OKALA_8020", sign=1, be=True, risk=D(2)):
    return OpenLeg(strategy, sign, be, risk)


def test_other_strategies_keep_position_open():
    assert add_allowed("NOISE", 1, [leg()], D(200), D(22), 2, True).reason == "POSITION_OPEN"
    assert add_allowed("OKALA_8020", 1, [leg(strategy="NOISE")], D(200), D(22), 2, True).reason == "POSITION_OPEN"


def test_opposite_not_at_be_max_adds_and_cap():
    assert add_allowed("OKALA_8020", -1, [leg()], D(200), D(22), 2, True).reason == "OKALA_ADD_OPPOSITE"
    assert add_allowed("OKALA_8020", 1, [leg(be=False)], D(200), D(22), 2, True).reason == "OKALA_ADD_NOT_AT_BE"
    assert add_allowed("OKALA_8020", 1, [leg(be=False)], D(200), D(22), 2, False).ok
    assert add_allowed("OKALA_8020", 1, [leg(), leg(), leg()], D(200), D(22), 2, True).reason == "OKALA_MAX_ADDS"
    assert add_allowed("OKALA_8020", 1, [leg(risk=D(190))], D(200), D(22), 2, True).reason == "OKALA_ADD_CAP"
    assert add_allowed("OKALA_8020", 1, [leg(risk=D(250))], D(200), D(22), 2, True).reason == "OKALA_ADD_CAP"
    assert add_allowed("OKALA_8020", 1, [leg()], D(200), D(0), 2, True).reason == "OKALA_ADD_CAP"


def test_add_sized_from_the_remaining_cap():
    assert add_allowed("OKALA_8020", 1, [leg(risk=D(2)), leg(risk=D(2))], D(200), D(22), 2, True) == AddDecision(
        True, None, 8, 1
    )
