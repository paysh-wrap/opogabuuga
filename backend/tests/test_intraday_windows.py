"""D37 H1: intraday_windows apply only in normal Intraday mode."""

from pathlib import Path

from app.config import load_rules
from app.risk.low_risk import apply_intraday_windows

PLAN = Path(__file__).resolve().parents[2] / "config/rules/lucid_pro_25k.yaml"


def _r():
    return load_rules(PLAN).rules


def test_intraday_mode_uses_best_hours():
    r = apply_intraday_windows(_r())
    assert r.instrument("MGC").windows == r.instrument("MGC").intraday_windows
    assert r.instrument("MNQ").windows == r.instrument("MNQ").intraday_windows


def test_one_to_one_and_scalp_keep_full_hours():
    base = _r()
    for key in ("one_to_one_mode", "scalp_mode"):
        r = base.model_copy(update={key: getattr(base, key).model_copy(update={"enabled": True})})
        assert apply_intraday_windows(r).instrument("MGC").windows == base.instrument("MGC").windows


def test_market_without_intraday_windows_unchanged():
    r = apply_intraday_windows(_r())
    assert r.instrument("MES").windows == _r().instrument("MES").windows
