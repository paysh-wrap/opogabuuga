from decimal import Decimal as D

from app.config import LunqStructureCfg, StructureFilterCfg
from app.engine.lunq_structure import check
from app.engine.trade_plan import Direction, TradePlan
from app.indicators.bars import Bar

M = 60_000


def bar(i, o, h, lo, c):
    return Bar(i * M, (i + 1) * M, D(o), D(h), D(lo), D(c))


def flat(n, px=100):
    return [bar(i, px, px + 1, px - 1, px) for i in range(n)]


BULL = flat(14) + [bar(14, 100, 100.5, 98, 99), bar(15, 99, 106, 99, 105)]  # bull OB 98..100.5
F = StructureFilterCfg(ob_body_atr=D(2), ob_swing_bars=5, ob_dist_pts=D(5), anchor_buffer_pts=D(1))


def plan(d, entry, stop, tp):
    r = abs(entry - stop)
    return TradePlan(Direction(d), D(entry), D(stop), D(tp), r, abs(D(tp) - D(entry)) / r)


def test_default_off_never_blocks_but_logs():
    p = plan("SHORT", 101, 110, 80)  # short right above demand -> would block
    r = check(LunqStructureCfg(filter=F), p, D("1.75"), D(3), D("0.25"), BULL, None)
    assert r.veto is None and r.plan == p
    assert r.features["lunq_structure"]["would_block"] == "OB_BLOCK"


def test_enabled_blocks():
    p = plan("SHORT", 101, 110, 80)
    r = check(LunqStructureCfg(enabled=True, filter=F), p, D("1.75"), D(3), D("0.25"), BULL, None)
    assert r.veto == "OB_BLOCK"


def test_anchor_tightens_only_inside_rr_window():
    # long 105, stop 90 (15 pts), tp 135 (2R). Anchor 97 -> 8 pts -> 3.75R > 3 -> rejected
    p = plan("LONG", 105, 90, 135)
    cfg = LunqStructureCfg(anchor_stop=True, filter=F)
    r = check(cfg, p, D("1.75"), D(3), D("0.25"), BULL, None)
    assert r.plan == p and r.features["lunq_structure"]["anchor_stop"] is None
    # tp 125 (20 pts): 1.33R fixed; anchored 8 pts -> 2.5R -> applied, target unchanged
    p2 = plan("LONG", 105, 90, 125)
    r2 = check(cfg, p2, D("1.75"), D(3), D("0.25"), BULL, None)
    assert r2.plan.stop == D(97) and r2.plan.take_profit == D(125) and r2.plan.rr == D("2.5")
    assert r2.plan.risk_pts < p2.risk_pts
    # computed but not applied when anchor_stop is off
    r3 = check(LunqStructureCfg(filter=F), p2, D("1.75"), D(3), D("0.25"), BULL, None)
    assert r3.plan == p2 and r3.features["lunq_structure"]["anchor_stop"] == "97.00"


def test_anchor_never_widens():
    p = plan("LONG", 105, 100, 115)  # stop already tighter than OB anchor
    r = check(LunqStructureCfg(anchor_stop=True, filter=F), p, D("1.75"), D(3), D("0.25"), BULL, None)
    assert r.plan == p
