"""D166 late-day momentum engine (pure): trend vs ATR gate, 15:00 entry only, stop / target, flat time, no lookahead."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo

import pytest

from app.config import FastPassCfg, LateDayCfg
from app.engine import late_day as LD
from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction
from app.risk.fast_pass import late_day_size

ET = ZoneInfo("America/New_York")
CFG = LateDayCfg()
TICK = D("0.25")


def _at(day: date, hh: int, mm: int) -> datetime:
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=ET)


def session(day: date, open_px: D, trend: D, width: D = D(10), after: D = D(0)) -> list[MBar]:
    """390 one-minute bars (closes 09:31 .. 16:00). Close of the 13:30 bar = open + trend; flat after, then `after`."""
    out: list[MBar] = []
    prev = open_px
    for i in range(390):
        t = _at(day, 9, 31) + timedelta(minutes=i)
        c = open_px + trend * D(i + 1) / D(240) if i < 240 else open_px + trend + after * D(i - 239) / D(150)
        out.append(MBar(t, prev, max(prev, c) + width / 2, min(prev, c) - width / 2, c, D(1)))
        prev = c
    return out


def history(n: int = 5, rng: D = D(100)) -> list[MBar]:
    out: list[MBar] = []
    for k in range(n):
        d = date(2026, 10, 5) + timedelta(days=k)
        out += session(d, D(20000), D(0), rng)  # high - low = rng
    return out


DAY = date(2026, 10, 13)
AT = _at(DAY, 15, 0)


def test_long_with_the_trend():
    today = session(DAY, D(20000), D(20))  # +20 pt >= 0.1 x ~100 ATR
    x = LD.decide(history(), today, CFG, TICK, AT)
    assert x is not None and x.direction is Direction.LONG
    assert x.entry == today[329].c and x.risk_pts == D(60) and x.stop == x.entry - 60
    assert x.take_profit == x.entry + 180 and x.rr == D(3) and x.trend_pts == D(20) and x.atr == D(100)


def test_short_with_the_trend():
    x = LD.decide(history(), session(DAY, D(20000), D(-20)), CFG, TICK, AT)
    assert (
        x is not None and x.direction is Direction.SHORT and x.stop == x.entry + 60 and x.take_profit == x.entry - 180
    )


@pytest.mark.parametrize("trend", [D(0), D(5), D("-9.5")])
def test_small_or_zero_trend_no_trade(trend):
    assert LD.decide(history(), session(DAY, D(20000), trend), CFG, TICK, AT) is None  # < 0.1 x 100


def test_threshold_is_inclusive():
    assert LD.decide(history(), session(DAY, D(20000), D(10)), CFG, TICK, AT) is not None  # == 0.1 x ATR


def test_only_on_the_entry_bar():
    today = session(DAY, D(20000), D(20))
    for hh, mm in ((14, 59), (15, 1), (13, 30), (9, 31)):
        assert LD.decide(history(), today, CFG, TICK, _at(DAY, hh, mm)) is None


def test_needs_history_and_uses_last_14_sessions():
    today = session(DAY, D(20000), D(20))
    assert LD.decide(history(2), today, CFG, TICK, AT) is None  # fewer than min_history_days sessions
    old = session(date(2026, 9, 1), D(20000), D(0), D(1000))  # a huge session older than 14 sessions is ignored
    h = old + history(4)
    assert LD.average_range([D(1000)] + [D(100)] * 14, 14, 3) == D(100)
    assert LD.decide(h, today, LateDayCfg(atr_days=3), TICK, AT) is not None
    assert LD.decide(h, today, LateDayCfg(atr_days=14), TICK, AT) is None  # mean (1000 + 4x100) / 5 = 280 -> 28 > 20


def test_missing_reference_or_open_bar_no_trade():
    today = session(DAY, D(20000), D(20))
    no_ref = [b for b in today if b.close_time != _at(DAY, 13, 30)]
    assert LD.decide(history(), no_ref, CFG, TICK, AT) is None
    no_open = [b for b in today if b.close_time != _at(DAY, 9, 31)]
    assert LD.decide(history(), no_open, CFG, TICK, AT) is None
    assert LD.decide(history(), [b for b in today if b.close_time < AT], CFG, TICK, AT) is None  # entry bar missing
    assert LD.decide(history(), [], CFG, TICK, AT) is None


def test_no_lookahead_later_bars_do_not_change_the_signal():
    base = session(DAY, D(20000), D(20))
    known = [b for b in base if b.close_time <= AT]
    x1 = LD.decide(history(), known, CFG, TICK, AT)
    crash = [MBar(b.close_time, b.o, b.h, D(1), D(1), b.v) for b in base[330:]]  # a crash after the entry bar
    x2 = LD.decide(history(), known + crash, CFG, TICK, AT)
    assert x1 is not None and x1 == x2  # bars strictly after `at` are ignored even when present


def test_history_of_the_same_day_is_ignored():
    today = session(DAY, D(20000), D(20))
    assert LD.session_ranges(history() + today, DAY) == [D(100)] * 5  # only sessions strictly before today


def test_flat_time():
    assert LD.is_flat_time(_at(DAY, 15, 59), CFG) and not LD.is_flat_time(_at(DAY, 15, 58), CFG)


def test_stop_rounds_away_from_entry_on_the_tick_grid():
    cfg = LateDayCfg(stop_pts=D("60.1"))
    x = LD.decide(history(), session(DAY, D(20000), D(20)), cfg, TICK, AT)
    assert x is not None and x.risk_pts == D("60.25") and x.stop % TICK == 0


def test_cfg_defaults_match_the_study():
    c = LateDayCfg()
    assert (c.symbol, c.ref_close, c.entry_at, c.flat_at, c.stop_pts, c.min_range_atr, c.atr_days) == (
        "MNQ", "13:30", "15:00", "15:59", D(60), D("0.1"), 14,
    )  # fmt: skip


FP = FastPassCfg(
    account_size=D(100000), noise_contracts=3, noise_stop_usd=D(100), candace_contracts=3, late_contracts=2,
    late_steps=[{"cushion_usd": 1000, "contracts": 1}], brake_inclusive=False,
)  # fmt: skip


def test_late_size_needs_option_fast_pass_eval_own_size():
    big = D(3000)
    assert late_day_size(True, True, FP, "EVAL", D(100000), big).contracts == 2
    assert late_day_size(False, True, FP, "EVAL", D(100000), big) is None  # option off
    assert late_day_size(True, False, FP, "EVAL", D(100000), big) is None  # plan's fast pass off
    assert late_day_size(True, True, FP, "FUNDED", D(100000), big) is None  # EVAL only
    assert late_day_size(True, True, FP, "LIVE", D(100000), big) is None
    assert late_day_size(True, True, FP, "EVAL", D(50000), big) is None  # own size only
    assert late_day_size(True, True, None, "EVAL", D(100000), big) is None
    inert = FP.model_copy(update={"late_contracts": None, "late_steps": ()})
    assert late_day_size(True, True, inert, "EVAL", D(100000), big) is None  # plan without a late size


def test_late_size_cushion_brake():
    n = lambda c: late_day_size(True, True, FP, "EVAL", D(100000), D(c))  # noqa: E731
    assert (n(1000).contracts, n(1000).braked) == (2, False)  # strictly below only
    assert (n(999).contracts, n(999).braked) == (1, True)
    assert n(999).stop_usd is None


def test_cfg_validation():
    with pytest.raises(ValueError, match="late_steps need late_contracts"):
        FastPassCfg(account_size=D(1), noise_contracts=1, noise_stop_usd=D(1), candace_contracts=1,
                    late_steps=[{"cushion_usd": 5, "contracts": 1}])  # fmt: skip
    with pytest.raises(ValueError, match="tighten-only"):
        FastPassCfg(account_size=D(1), noise_contracts=1, noise_stop_usd=D(1), candace_contracts=1,
                    late_contracts=1, late_steps=[{"cushion_usd": 5, "contracts": 2}])  # fmt: skip
