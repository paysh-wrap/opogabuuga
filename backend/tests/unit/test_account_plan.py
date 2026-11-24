"""D168: which rule plan an account uses (pure)."""

from decimal import Decimal as D

from app.risk.account_plan import infer_plan, plan_family, plan_size, resolve_plan

AVAIL = ["lucid_pro_25k", "lucid_pro_50k", "lucid_pro_100k", "lucid_pro_150k", "lucid_flex_25k", "lucid_daily_25k"]


def test_family_and_size():
    assert plan_family("lucid_pro_25k") == "lucid_pro"
    assert plan_family("lucid_daily") == "lucid_daily"
    assert plan_size("lucid_pro_150k") == D(150000)
    assert plan_size("lucid_daily") is None


def test_inferred_from_the_account_size_inside_the_active_family():
    assert infer_plan(D(100000), "lucid_pro_25k", AVAIL) == "lucid_pro_100k"
    assert infer_plan(D(50000), "lucid_pro_150k", AVAIL) == "lucid_pro_50k"
    assert infer_plan(D(25000), "lucid_flex_25k", AVAIL) == "lucid_flex_25k"


def test_falls_back_to_the_active_plan():
    assert infer_plan(None, "lucid_pro_25k", AVAIL) == "lucid_pro_25k"
    assert infer_plan(D(0), "lucid_pro_25k", AVAIL) == "lucid_pro_25k"
    assert infer_plan(D(75000), "lucid_pro_25k", AVAIL) == "lucid_pro_25k"  # no such file
    assert infer_plan(D(27500), "lucid_pro_25k", AVAIL) == "lucid_pro_25k"  # not a whole size
    assert infer_plan(D(50000), "lucid_flex_25k", AVAIL) == "lucid_flex_25k"  # family has no 50k file here
    assert infer_plan(D(100000), "lucid_daily_25k", AVAIL) == "lucid_daily_25k"


def test_explicit_plan_always_wins():
    assert resolve_plan("lucid_pro_50k", D(150000), "lucid_pro_25k", AVAIL) == "lucid_pro_50k"
    assert resolve_plan("", D(150000), "lucid_pro_25k", AVAIL) == "lucid_pro_150k"
    assert resolve_plan(None, D(150000), "lucid_pro_25k", AVAIL) == "lucid_pro_150k"
