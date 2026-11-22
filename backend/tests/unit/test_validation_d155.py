"""D155: Lucid Pro eval consistency 40 % or the 50 % option (day stop = pct − 2 buffer → 48 %)."""

from decimal import Decimal as D

from app.config import load_rules
from app.risk.validation import validate
from app.settings import REPO_ROOT


def test_eval_consistency_50_is_valid_and_day_stop_is_48pct():
    r = load_rules(REPO_ROOT / "config" / "rules" / "lucid_pro_50k.yaml").rules
    r50 = r.model_copy(update={"eval": r.eval.model_copy(update={"consistency_max_day_pct": D(50)})})
    assert validate(r50).ok
    assert r50.eval.consistency_max_day_pct - r50.internal.consistency_day_stop_buffer_pct == D(48)
    bad = r.model_copy(update={"eval": r.eval.model_copy(update={"consistency_max_day_pct": D(1)})})
    assert not validate(bad).ok
