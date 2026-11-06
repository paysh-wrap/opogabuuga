from decimal import Decimal as D
from pathlib import Path

from app.config import load_rules
from app.risk.low_risk import apply_low_risk
from app.risk.validation import validate

RULES = Path(__file__).resolve().parents[3] / "config" / "rules"


def test_low_risk_halves_risk_and_doubles_loss_allowance():
    for f in RULES.glob("lucid_*.yaml"):
        base = load_rules(f).rules
        lo = apply_low_risk(base)
        assert lo.internal.risk_pct_ceiling == base.internal.risk_pct_ceiling / 2
        assert lo.internal.risk_pct_by_score[60] == base.internal.risk_pct_by_score[60] / 2
        assert lo.eval_mode.max_risk_usd == base.eval_mode.max_risk_usd / 2
        assert lo.internal.max_consecutive_losses_per_day == base.internal.max_consecutive_losses_per_day * 2
        cap = base.internal.low_risk_max_trades_per_day  # D51: Lower risk uses its own limit (Pro/Flex: 7)
        assert lo.internal.max_trades_per_day == max(base.internal.max_trades_per_day, cap)
        if f.stem.startswith(("lucid_pro_", "lucid_flex_")):
            assert base.internal.max_trades_per_day == 3 and lo.internal.max_trades_per_day == 7
        assert lo.eval.max_loss_limit == base.eval.max_loss_limit  # firm rules untouched
        if base.internal.max_risk_usd is not None:
            assert lo.internal.max_risk_usd == base.internal.max_risk_usd * D("0.5")
        assert validate(lo).ok, (f.name, validate(lo).errors)
