from decimal import Decimal as D

import pytest

from app.indicators.bars import Bar
from app.indicators.order_block import ObConfig, anchor_stop, blocked_by_opposing, find_blocks
from app.indicators.smt import SmtConfig, blocked_by_smt, find_smt

M = 60_000


def bar(i, o, h, lo, c):
    return Bar(i * M, (i + 1) * M, D(o), D(h), D(lo), D(c))


def flat(n, px=100):
    return [bar(i, px, px + 1, px - 1, px) for i in range(n)]


def test_bull_ob_confirmed_at_displacement_close():
    bars = flat(14) + [bar(14, 100, 100.5, 98, 99), bar(15, 99, 106, 99, 105)]
    cfg = ObConfig(swing_bars=5, body_atr=D(2))
    obs = find_blocks(bars, cfg)
    assert len(obs) == 1 and obs[0].bullish and obs[0].low == D(98) and obs[0].high == D("100.5")
    assert obs[0].confirm_ms == bars[15].close_ms and obs[0].origin_ms == bars[14].open_ms
    # no lookahead: before the displacement bar closed there is no block
    assert find_blocks(bars[:15], cfg) == []


def test_mitigation_and_expiry():
    bars = flat(14) + [bar(14, 100, 100.5, 98, 99), bar(15, 99, 106, 99, 105), bar(16, 105, 105, 96, 97)]
    cfg = ObConfig(swing_bars=5, body_atr=D(2))
    assert not any(o.bullish for o in find_blocks(bars, cfg))  # closed below the zone low
    bars2 = bars[:16] + flat(5, 105)
    assert find_blocks(bars2, ObConfig(swing_bars=5, body_atr=D(2), max_age_bars=2)) == []


def test_bear_ob_and_filter_and_anchor():
    bars = flat(14) + [bar(14, 100, 102, 99.5, 101), bar(15, 101, 101, 94, 95)]
    cfg = ObConfig(swing_bars=5, body_atr=D(2))
    obs = find_blocks(bars, cfg)
    assert len(obs) == 1 and not obs[0].bullish
    assert blocked_by_opposing(1, D(99), obs, D(5)) is not None  # long under supply
    assert blocked_by_opposing(1, D(90), obs, D(5)) is None  # too far
    assert blocked_by_opposing(-1, D(99), obs, D(5)) is None  # same side never blocked
    # short anchored above the bear OB high, tighter than the fixed stop
    assert anchor_stop(-1, D(95), D(120), obs, D(1), D("0.25")) == D(103)
    assert anchor_stop(-1, D(95), D(100), obs, D(1), D("0.25")) == D(100)  # never widens
    assert anchor_stop(1, D(95), D(70), obs, D(1), D("0.25")) == D(70)  # no bull OB -> unchanged


def test_bull_anchor_long():
    bars = flat(14) + [bar(14, 100, 100.5, 98, 99), bar(15, 99, 106, 99, 105)]
    obs = find_blocks(bars, ObConfig(swing_bars=5, body_atr=D(2)))
    assert anchor_stop(1, D(105), D(60), obs, D(1), D("0.25")) == D(97)
    assert blocked_by_opposing(-1, D(101), obs, D(5)) is not None


def test_smt():
    a = flat(25)
    b = flat(25)
    a[24] = bar(24, 100, 106, 100, 105)  # A new high, B not
    sig = find_smt(a, b, SmtConfig(lookback=20))
    assert len(sig) == 1 and sig[0].bearish and sig[0].confirm_ms == a[24].close_ms
    assert blocked_by_smt(1, sig, 30, SmtConfig(valid_bars=15)) is not None
    assert blocked_by_smt(-1, sig, 30, SmtConfig(valid_bars=15)) is None
    assert blocked_by_smt(1, sig, 60, SmtConfig(valid_bars=15)) is None
    a[24] = bar(24, 100, 100, 94, 95)
    s2 = find_smt(a, b, SmtConfig(lookback=20))
    assert not s2[0].bearish and blocked_by_smt(-1, s2, 24, SmtConfig()) is not None
    assert find_smt(flat(25), flat(25), SmtConfig()) == []
    with pytest.raises(ValueError):
        find_smt(flat(25), flat(26)[1:], SmtConfig())


def test_structure_filter_verdict():
    from app.config import StructureFilterCfg
    from app.engine.structure_filter import evaluate

    bars = flat(14) + [bar(14, 100, 102, 99.5, 101), bar(15, 101, 101, 94, 95)]
    cfg = StructureFilterCfg(ob_body_atr=D(2), ob_swing_bars=5, ob_dist_pts=D(5))
    assert evaluate(cfg, 1, D(99), D(60), D("0.25"), bars, None).veto == "OB_BLOCK"
    v = evaluate(cfg, -1, D(95), D(120), D("0.25"), bars, None)
    assert v.veto is None and v.anchor_stop == D(104)
    assert evaluate(cfg, -1, D(95), D(100), D("0.25"), bars, None).anchor_stop is None
    # SMT: A new high, B not -> long blocked
    a = flat(25)
    b = flat(25)
    a[24] = bar(24, 100, 106, 100, 105)
    c2 = StructureFilterCfg(ob_filter=False, smt_filter=True)
    assert evaluate(c2, 1, D(105), D(50), D("0.25"), a, b).veto == "SMT_BLOCK"
    assert evaluate(c2, -1, D(105), D(50), D("0.25"), a, b).veto is None
    assert evaluate(c2, 1, D(105), D(50), D("0.25"), a, None).veto is None


def test_mso_div_filter_default_off_and_threshold_bounds():
    from pydantic import ValidationError

    from app.config import StrategyCfg, StructureFilterCfg
    from app.engine.structure_filter import evaluate

    assert StrategyCfg().ai_gate_min_accuracy == D("0.70")
    assert StrategyCfg(ai_gate_min_accuracy=D("0.60")).ai_gate_min_accuracy == D("0.60")
    with pytest.raises(ValidationError):
        StrategyCfg(ai_gate_min_accuracy=D("0.40"))
    cfg = StructureFilterCfg(ob_filter=False, mso_div_filter=True)
    v = evaluate(cfg, 1, D(100), D(90), D("0.25"), flat(60), None)
    assert v.veto is None  # flat bars print no divergence
