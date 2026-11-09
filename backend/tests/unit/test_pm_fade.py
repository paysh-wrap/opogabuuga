"""D58 PM_FADE pure rules."""

from decimal import Decimal as D

import pytest

from app.engine import noise as N
from app.engine import pm_fade as PF
from app.engine.trade_plan import Direction


def test_running_vwap_and_sd():
    v = PF.running_vwaps([(D(11), D(9), D(10), D(0)), (D(11), D(9), D(10), D(100)), (D(21), D(19), D(20), D(100))])
    assert v == [None, D(10), D(15)]
    assert PF.dev_sd([D(10), D(10), D(20)], v) == D("2.5")  # devs 0, +5 (first bar has no VWAP) → population sd 2.5
    assert PF.dev_sd([D(1)], [None]) is None


def test_decide_short_long_and_skips():
    kw = dict(band=D(2), tick=D("0.25"), stop_pts=D(124), min_target_ticks=4)
    s = PF.decide(close=D(110), vwap=D(100), sd=D(4), **kw)
    assert s.direction is Direction.SHORT and s.take_profit == D(100) and s.stop == D(234) and s.risk_pts == D(124)
    lo = PF.decide(close=D(90), vwap=D("100.1"), sd=D(4), **kw)
    assert lo.direction is Direction.LONG and lo.take_profit == D(100) and lo.stop == D(-34)
    assert PF.decide(close=D(105), vwap=D(100), sd=D(4), **kw) is None  # inside the band
    assert PF.decide(close=D(110), vwap=None, sd=D(4), **kw) is None
    assert PF.decide(close=D(110), vwap=D(100), sd=D(0), **kw) is None
    assert PF.decide(close=D("100.5"), vwap=D(100), sd=D("0.1"), **kw) == "TARGET_TOO_CLOSE"


def test_stop_pts_for_usd_matches_research():
    assert N.stop_pts_for_usd(D(250), D("0.25"), D("0.50"), D(1), 1) == D(124)
    assert N.stop_pts_for_usd(D(150), D("0.25"), D("0.50"), D(1), 1) == D(74)
    with pytest.raises(ValueError):
        N.stop_pts_for_usd(D(2), D("0.25"), D("0.50"), D(1), 1)
    p = N.plan(Direction.LONG, D(20000), D("0.25"), D("0.01"), D("0.10"), D(124))
    assert p.stop == D(19876) and p.risk_pts == D(124)
