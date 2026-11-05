def test_one_to_one_for_d23():
    from app.risk.eval_mode import one_to_one_for

    assert one_to_one_for("FUNDED", "inherit", True, True, False)  # global 1:1 mode on
    assert one_to_one_for("EVAL", "inherit", True, False, True)  # eval mode on + eval 1:1
    assert not one_to_one_for("EVAL", "inherit", False, False, True)  # eval mode off
    assert not one_to_one_for("FUNDED", "inherit", True, False, True)  # never funded via eval 1:1
    assert not one_to_one_for("EVAL", "inherit", True, False, False)
