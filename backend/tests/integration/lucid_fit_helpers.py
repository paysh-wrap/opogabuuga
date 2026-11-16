"""Shared check for the D143-style Lucid fit tables of the rule-sheet strategies (D144+)."""

from __future__ import annotations

from decimal import Decimal as D


def fit(k: int, stage: str, cfg_attr: str, losses: int, stops: tuple[int, int]) -> tuple[str, list[int]]:
    from app.config import load_rules
    from app.engine.lucid_fit import contracts_for, trade_risk_usd
    from app.phases.phase_engine import firm_max_micros, stage_rules
    from app.settings import REPO_ROOT

    r = load_rules(REPO_ROOT / "config" / "rules" / f"lucid_pro_{k}k.yaml").rules
    c, i = getattr(r.strategy, cfg_attr), r.internal
    sr = stage_rules(r, stage)
    assert sr.drawdown_type == "eod"
    day_stop = D("0.38") * r.eval.profit_target if stage == "EVAL" else None
    got = trade_risk_usd(sr.max_loss, c.risk_pct_of_drawdown, losses, sr.dll, c.dll_use_pct,
                         sr.max_loss - i.kill_switch_mll_distance, r.strategy.max_trade_risk_usd, day_stop)  # fmt: skip
    # the worst day (`losses` stops) fits the DLL x dll_use_pct and the MLL room minus the kill distance
    assert losses * got <= sr.max_loss - i.kill_switch_mll_distance
    if sr.dll is not None:
        assert losses * got <= sr.dll * c.dll_use_pct + D("0.01")
    m = r.instrument("MNQ")
    slip = m.slippage_ticks or r.trade_plan.slippage_ticks
    cap = min(firm_max_micros(r, stage, D(0)), i.internal_max_micros)
    return str(got), [min(contracts_for(got, D(x), m.tick, m.tick_value, m.fee_rt, slip), cap) for x in stops]
