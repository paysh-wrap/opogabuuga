"""GALA PRICE ACTION engine (D144): one test per rule id of docs/GALA_RULES.md that is built, on hand-built bars."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.config import GalaPaCfg
from app.engine import gala_pa as G
from app.engine.trade_plan import Direction

TICK = D("0.25")
D1 = date(2026, 10, 12)  # Mon (history)
D2 = date(2026, 10, 13)  # Tue (today)
CFG = GalaPaCfg(pivot_lookback=1, trend_swing_lookback=1)
UP_ROWS = [  # hourly o, h, l, c — swings HH + HL; levels 103 LOW, 115 HIGH, 109 LOW (109 HIGH is pierced, A6)
    (100, 105, 99, 104),
    (104, 110, 103, 109),
    (109, 109.5, 102, 103),
    (103, 112, 102.5, 111),
    (111, 116, 110, 115),
    (115, 115.5, 108, 109),
    (109, 113, 108.5, 112),
]


def C(o, h, lo, c, start=None, minutes=5, gap=False):
    st = start or datetime(2026, 10, 13, 9, 40, tzinfo=G.ET)
    return G.Candle(st, st + timedelta(minutes=minutes), D(str(o)), D(str(h)), D(str(lo)), D(str(c)), gap)


def _hour(d, k, o, h, lo, c, mins=60):
    st = datetime(d.year, d.month, d.day, 9, 30, tzinfo=G.ET) + timedelta(minutes=60 * k)
    o, h, lo, c = (D(str(x)) for x in (o, h, lo, c))
    out: list[G.GBar] = []
    for m in range(mins):
        p = o + (c - o) * D(m) / D(mins - 1)
        prev = out[-1].c if out else o
        hi, lw = max(prev, p), min(prev, p)
        hi = h if m == mins // 3 else hi
        lw = lo if m == 2 * mins // 3 else lw
        out.append(G.GBar(st + timedelta(minutes=m + 1), prev, hi, lw, p))
    return out


def history(rows=UP_ROWS, d=D1):
    out: list[G.GBar] = []
    for k, r in enumerate(rows):
        out += _hour(d, k, *r, mins=30 if k == 6 else 60)
    return out


def five(start_min, o, h, lo, c):
    """Five 1-minute bars making one 5-minute candle that starts `start_min` minutes after 09:30 today."""
    st = datetime(2026, 10, 13, 9, 30, tzinfo=G.ET) + timedelta(minutes=start_min)
    o, h, lo, c = (D(str(x)) for x in (o, h, lo, c))
    return [
        G.GBar(st + timedelta(minutes=1), o, max(o, h if o == h else o), o, o),
        G.GBar(st + timedelta(minutes=2), o, h, o, o),
        G.GBar(st + timedelta(minutes=3), o, o, lo, o),
        G.GBar(st + timedelta(minutes=4), o, o, o, o),
        G.GBar(st + timedelta(minutes=5), o, max(o, c), min(o, c), c),
    ]


def today_break_retest(after=()):
    bars = five(0, 113, 113.5, 112.5, 113)  # 09:30–09:35 (B1 skipped)
    bars += five(5, 113, 116.25, 113, 116)  # 09:35–09:40 the break: close 116 > 115
    bars += five(10, 116, 117, 114.5, 117)  # 09:40–09:45 retest: wick to 114.5, body above 115
    for i, x in enumerate(after):
        bars += five(15 + 5 * i, *x)
    return bars


# ---------------------------------------------------------------- A2 / A3 / A4 / A6 / A7


def test_a7_rth_only_and_the_overnight_gap_is_one_candle():
    pre = G.GBar(datetime(2026, 10, 13, 8, 0, tzinfo=G.ET), D(1), D(999), D(0), D(1))  # pre-market: ignored
    first = G.GBar(datetime(2026, 10, 13, 9, 31, tzinfo=G.ET), D(113), D(113), D(113), D(113))
    pc = G.hourly_plan_candles([*history(), pre], first, 5)
    assert len(pc) == 8 and pc[-1].gap and (pc[-1].o, pc[-1].c) == (D(112), D(113))
    assert all(c.h != 999 for c in pc)
    two = G.hourly_plan_candles(history() + history(d=date(2026, 10, 9)), None, 5)
    assert sum(c.gap for c in two) == 1  # two sessions → one gap candle between them, none after (no today)


def test_a2_trend_from_highs_and_lows():
    pc = G.hourly_plan_candles(history(), None, 5)
    assert G.trend(pc, 1) == 1
    down = [(-o, -lo, -h, -c) for o, h, lo, c in UP_ROWS]
    pc_dn = G.hourly_plan_candles(history(down), None, 5)
    assert G.trend(pc_dn, 1) == -1


def test_a3_choppy_trend_is_no_trade():
    chop = [
        C(100, 110, 95, 105),
        C(105, 108, 90, 100),
        C(100, 112, 96, 101),
        C(101, 109, 92, 103),
        C(103, 111, 91, 102),
    ]
    assert G.trend(chop, 1) == 0  # higher high with lower low
    assert G.trend(chop[:2], 1) == 0  # not enough swings
    rep = G.replay_day(history([(100, 101, 99, 100)] * 7), today_break_retest(), CFG, TICK)
    assert rep.skip == "GALA_NO_TREND" and rep.signals == []


def test_a4_level_is_the_open_of_the_colour_change_candle_at_a_body_pivot():
    pc = [C(100, 105, 99, 104), C(104, 130, 103, 109), C(109, 109.5, 80, 103), C(103, 104, 101, 102)]
    lv = G.pivot_levels(pc, 1)
    assert [(x.price, x.kind) for x in lv] == [(D(109), "HIGH")]  # the red candle's OPEN — wicks (130, 80) ignored
    assert G.pivot_levels(pc, 2) == []  # needs 2 closed candles each side
    green = [C(110, 111, 105, 106), C(106, 107, 100, 101), C(101, 108, 100, 107), C(107, 109, 106, 108)]
    assert [(x.price, x.kind) for x in G.pivot_levels(green, 1)] == [(D(101), "LOW")]


def test_a6_a_body_through_the_level_deletes_it():
    pc = [C(100, 105, 99, 104), C(104, 110, 103, 109), C(109, 109.5, 102, 103), C(103, 104, 101, 102)]
    assert G.pivot_levels(pc, 1)
    pierced = [*pc, C(102, 112, 101, 111)]  # body 102–111 crosses 109
    assert all(x.price != D(109) for x in G.pivot_levels(pierced, 1))
    wick_only = [*pc, C(102, 112, 101, 108)]  # only the wick passes 109 → kept
    assert any(x.price == D(109) for x in G.pivot_levels(wick_only, 1))


def test_a8_closer_level_picks_the_setup():
    lv = [G.Level(D(115), "HIGH", D2), G.Level(D(109), "LOW", D2)]  # type: ignore[arg-type]
    assert G.choose_setup(1, D(113), lv) == ("BREAK_RETEST", D(115))
    assert G.choose_setup(1, D(110), lv) == ("BOUNCE", D(109))
    assert G.choose_setup(-1, D(110), lv) == ("BREAK_RETEST", D(109))
    assert G.choose_setup(-1, D(114), lv) == ("REJECTION", D(115))
    assert G.choose_setup(1, D(120), lv) == ("BOUNCE", D(115))  # only a level below
    assert G.choose_setup(-1, D(100), lv) == ("REJECTION", D(109))
    assert G.choose_setup(1, D(100), []) is None


def test_a5_open_level_is_optional_and_a9_news_skips_the_day():
    rep = G.replay_day(history(), today_break_retest(), replace_cfg(use_open_level=True), TICK)
    assert any(x.kind == "OPEN" for x in rep.levels)
    rep = G.replay_day(history(), today_break_retest(), CFG, TICK, news_first_hour=True)
    assert rep.skip == "GALA_NEWS_FIRST_HOUR"


def replace_cfg(**kw):
    return CFG.model_copy(update=kw)


# ---------------------------------------------------------------- C2 / C4 / C5 / C6 / C7 / C8


def test_c2_perfect_entry_candle():
    assert G.perfect_entry(C(116, 117, 114.5, 117), D(115), 1, D(10))
    assert not G.perfect_entry(C(116, 117, 115.5, 117), D(115), 1, D(10))  # no touch (C3: missed)
    assert not G.perfect_entry(C(114, 117, 113, 117), D(115), 1, D(10))  # body below the level
    assert not G.perfect_entry(C(116, 117, 100, 117), D(115), 1, D(10))  # wick far through
    assert G.perfect_entry(C(114, 115.5, 113, 113.5), D(115), -1, D(10))  # SHORT mirror
    assert not G.perfect_entry(C(116, 117, 114, 115.5), D(115), -1, D(10))


def test_c4_big_wick_hammer_is_skipped():
    assert G.hammer(C(116, 117, 110, 117), 1, D(2), TICK)  # 6 pt wick, 1 pt body
    assert not G.hammer(C(116, 118, 115, 118), 1, D(2), TICK)
    assert G.hammer(C(114, 120, 113.5, 113.5), -1, D(2), TICK)
    bars = five(0, 113, 113.5, 112.5, 113) + five(5, 113, 116.25, 113, 116) + five(10, 116, 117, 110, 116.5)
    assert G.replay_day(history(), bars, CFG, TICK).signals == []


def test_c5_break_then_retest_gives_the_entry():
    rep = G.replay_day(history(), today_break_retest(), CFG, TICK)
    assert (rep.setup, rep.level) == ("BREAK_RETEST", D(115))
    [s] = rep.signals
    assert s.direction == Direction.LONG and s.entry == D(117)
    assert s.time == datetime(2026, 10, 13, 9, 45, tzinfo=G.ET)


def test_c5_close_back_through_cancels_the_break():
    bars = five(0, 113, 113.5, 112.5, 113) + five(5, 113, 116.25, 113, 116) + five(10, 116, 116, 113, 114)
    bars += five(15, 114, 116.5, 114.5, 116)  # this is a new break, not a retest
    assert G.replay_day(history(), bars, CFG, TICK).signals == []
    c = [C(113, 116, 113, 116), C(116, 117, 114, 114.5), C(114.5, 115.5, 114, 115.25)]
    assert G.find_entry(c, "BREAK_RETEST", D(115), 1, CFG, TICK) is None
    late = [C(113, 116, 113, 116)] + [C(116, 118, 116, 117)] * 6 + [C(116, 117, 114.5, 117)]
    assert G.find_entry(late, "BREAK_RETEST", D(115), 1, CFG, TICK) is None  # retest after max_retest_bars


def test_c6_stop_at_the_lowest_wick_of_the_retest_candles():
    c = [C(113, 116, 113, 116), C(116, 117, 114.75, 117), C(117, 117.5, 114.5, 117.5)]
    # candle 1: touches but fails C2? low 114.75 ≤ 115, body ≥ 115 → it IS perfect → entry there, its own wick
    assert G.find_entry(c, "BREAK_RETEST", D(115), 1, CFG, TICK) == (1, D("114.75"))
    c2 = [C(113, 116, 113, 116), C(116, 116.5, 113.5, 116.25), C(116, 117.5, 114.5, 117.5)]  # 1st wick 1.5 pt…
    hit = G.find_entry(c2, "BREAK_RETEST", D(115), 1, replace_cfg(max_wick_through_pts=D(1)), TICK)
    assert hit == (2, D("113.5"))  # …too deep for the entry, but the group's lowest wick sets the stop


def test_c7_bounce_needs_bodies_above_and_wicks_below():
    c = [C(111, 111.5, 108.5, 110), C(110, 111, 108.75, 111)]
    assert G.find_entry(c, "BOUNCE", D(109), 1, CFG, TICK) == (1, D("108.5"))
    assert G.find_entry(c[:1], "BOUNCE", D(109), 1, CFG, TICK) is None  # one candle is not enough
    broken = [C(111, 111.5, 108.5, 110), C(110, 110, 107, 108)]
    assert G.find_entry(broken, "BOUNCE", D(109), 1, CFG, TICK) is None


def test_c8_rejection_short_mirrors():
    c = [C(114, 115.5, 113, 114.5), C(114.5, 115.25, 113.5, 114)]
    assert G.find_entry(c, "REJECTION", D(115), -1, CFG, TICK) == (1, D("115.5"))


# ---------------------------------------------------------------- B1 / B2


def test_b1_first_five_minutes_are_skipped():
    bars = five(0, 113, 116.25, 113, 116) + five(5, 116, 117, 114.5, 117)  # break in the first candle
    assert G.replay_day(history(), bars, CFG, TICK).signals == []
    assert G.replay_day(history(), bars, replace_cfg(skip_first_minutes=0), TICK).signals


def test_b2_entries_only_inside_the_window_and_time_exit():
    rep = G.replay_day(history(), today_break_retest(), replace_cfg(window_end="09:40"), TICK)
    assert rep.signals == []
    flat = [(117, 117.5, 116.5, 117)] * 13  # never hits stop or 2R
    [s] = G.replay_day(history(), today_break_retest(flat), replace_cfg(max_hold_minutes=60), TICK).signals
    assert s.outcome == "TIME" and s.exit_time == s.time + timedelta(minutes=60)


# ---------------------------------------------------------------- D1 / D3


def test_d1_stop_one_tick_past_the_wick_and_d3_target_2r():
    [s] = G.replay_day(history(), today_break_retest(), CFG, TICK).signals
    assert s.stop == D("114.25") and s.stop_pts == D("2.75")
    assert s.take_profit == D("122.5") and s.rr == D(2)


# ---------------------------------------------------------------- E1 / E2 / E3


def _stop_then_retry(n):
    seq: list[tuple] = []
    for _ in range(n):
        seq += [(117, 117, 114, 114.5), (114.5, 116.25, 114.5, 116), (116, 117, 114.5, 117)]  # stop, re-break, retest
    return seq


def test_e3_a_winner_ends_the_day():
    win = [(117, 123, 117, 122.75), (116, 118, 114.5, 118), (117, 119, 114.5, 118.5)]  # TP, then a bounce off 115
    rep = G.replay_day(history(), today_break_retest(win), CFG, TICK)
    assert [s.outcome for s in rep.signals] == ["TP"]
    no_trim = replace_cfg(stop_after_win=False, trim_at_target=False)
    rep = G.replay_day(history(), today_break_retest(win), no_trim, TICK)
    assert [s.setup for s in rep.signals] == ["BREAK_RETEST", "BOUNCE"]  # A8 re-picked from where price is
    rep = G.replay_day(history(), today_break_retest(win), replace_cfg(stop_after_win=False), TICK)
    [s] = rep.signals  # D152: the runner (stop 117 by 09:50) is flat at 09:51 — the bounce needed the 09:50 candle
    assert s.runner is not None and s.runner.exit_time == _t(9, 51) and s.done_at == _t(9, 51)


def test_e1_two_attempts_per_setup():
    rep = G.replay_day(history(), today_break_retest(_stop_then_retry(3)), CFG, TICK)
    assert [s.attempt for s in rep.signals] == [1, 2] and all(s.outcome == "STOP" for s in rep.signals)


def test_e2_max_trades_a_day():
    rep = G.replay_day(
        history(), today_break_retest(_stop_then_retry(3)), replace_cfg(max_attempts_per_setup=2, max_trades_per_day=1),
        TICK,
    )  # fmt: skip
    assert len(rep.signals) == 1
    with pytest.raises(ValueError):
        GalaPaCfg(max_trades_per_day=4)  # E2: 4 or more is overtrading


def test_replay_is_deterministic_bar_by_bar():
    bars = today_break_retest([(117, 123, 117, 122.75)])
    full = G.replay_day(history(), bars, CFG, TICK).signals
    upto = G.replay_day(history(), [b for b in bars if b.close_time <= full[0].time], CFG, TICK).signals
    assert [(s.time, s.entry, s.stop) for s in upto] == [(s.time, s.entry, s.stop) for s in full]
    assert upto[0].outcome == "OPEN" and full[0].outcome == "TP"
    assert G.replay_day(history(), [], CFG, TICK).skip == "GALA_NO_BARS"
    assert G.replay_day(history(), bars[1:], CFG, TICK).skip == "GALA_NO_OPEN"
    assert replace(full[0], exit_price=None).won is False


# ---------------------------------------------------------------- D4 / D5 trim at 2R + candle-by-candle stop (D152)


def _t(h, m):
    return datetime(2026, 10, 13, h, m, tzinfo=G.ET)


TREND_RUN = [  # after the 09:45 entry (117, stop 114.25, 2R 122.5, runner target 4R = 128)
    (117, 123, 117, 122.75),  # 09:45–09:50: 2R reached at 09:47 → trim
    (122.75, 124, 122, 123.5),  # 09:50–09:55
    (123.5, 125, 123, 124.5),  # 09:55–10:00
    (124.5, 124.5, 120, 121),  # 10:00–10:05: low 120 at 10:03
]


def test_d4_trim_at_2r_then_d5_stop_to_each_candle_open_until_above_entry():
    [s] = G.replay_day(history(), today_break_retest(TREND_RUN), CFG, TICK).signals
    assert (s.outcome, s.exit_time, s.exit_price) == ("TP", _t(9, 47), D("122.5"))  # leg A / 1 micro: all at 2R
    r = s.runner
    assert r is not None and s.runner_target == r.target == D(128)
    # trim → last closed candle's open (116, the retest); 09:50 → 117 (= entry, not above yet); 09:55 → 122.75
    assert r.stops == [(_t(9, 47), D(116)), (_t(9, 50), D(117)), (_t(9, 55), D("122.75"))]
    assert (r.outcome, r.exit_time, r.exit_price) == ("STOP", _t(10, 3), D("122.75"))  # above entry: it stays (D5)
    assert r.stop_at(_t(9, 46)) is None and r.stop_at(_t(9, 52)) == D(117) and s.done_at == _t(10, 3)


def test_d5_gap_keep_trailing_after_entry():
    keep = replace_cfg(runner_trail_after_entry=True)
    [s] = G.replay_day(history(), today_break_retest(TREND_RUN), keep, TICK).signals
    assert s.runner is not None and s.runner.stops[-1] == (_t(10, 0), D("123.5"))
    assert (s.runner.outcome, s.runner.exit_price) == ("STOP", D("123.5"))


def test_d5_a_candle_open_at_or_through_the_price_is_not_used():
    red = [
        (117, 123, 117, 122.75),  # trim 09:47 (stop 116), 09:50 → 117
        (122.75, 123, 121, 121.5),  # red: its open is above the price → not a stop (stays 117)
        (121.5, 122, 120, 121),  # red again → stays 117
        (121, 122, 120.5, 121.75),  # green: open 121 is behind the close → stop 121 at 10:05
        (121.75, 121.75, 119, 119.5),  # 10:08 low 119 → runner out at 121
    ]
    [s] = G.replay_day(history(), today_break_retest(red), CFG, TICK).signals
    r = s.runner
    assert r is not None
    assert r.stops == [(_t(9, 47), D(116)), (_t(9, 50), D(117)), (_t(10, 5), D(121))]
    assert (r.outcome, r.exit_time, r.exit_price) == ("STOP", _t(10, 8), D(121))


def test_runner_far_target_and_time_exit():
    up = [(117, 123, 117, 122.75), (122.75, 129, 122.75, 128.5)]
    [s] = G.replay_day(history(), today_break_retest(up), CFG, TICK).signals
    assert s.runner is not None and (s.runner.outcome, s.runner.exit_price) == ("TP", D(128))
    flat = [(117, 123, 117, 122.75)] + [(122.75, 123, 122.5, 122.75)] * 12  # never stopped, never 4R
    [s] = G.replay_day(history(), today_break_retest(flat), CFG, TICK).signals
    assert s.runner is not None and (s.runner.outcome, s.runner.exit_time) == ("TIME", _t(10, 45))  # B2 60 min
    assert s.runner.exit_price == D("122.75")


def test_trim_off_is_the_single_2r_bracket_and_open_runner_is_open():
    [s] = G.replay_day(history(), today_break_retest(TREND_RUN), replace_cfg(trim_at_target=False), TICK).signals
    assert s.runner is None and s.runner_target is None and s.outcome == "TP" and s.done_at == _t(9, 47)
    bars = today_break_retest(TREND_RUN)
    [s] = G.replay_day(history(), [b for b in bars if b.close_time <= _t(9, 52)], CFG, TICK).signals
    assert s.runner is not None and s.runner.outcome == "OPEN" and s.done_at is None
    [s] = G.replay_day(history(), [b for b in bars if b.close_time <= _t(9, 46)], CFG, TICK).signals
    assert s.outcome == "OPEN" and s.runner is None and s.done_at is None


def test_runner_replay_bar_by_bar_equals_the_full_day():
    bars = today_break_retest(TREND_RUN)
    [full] = G.replay_day(history(), bars, CFG, TICK).signals
    assert full.runner is not None
    for b in bars:
        if not (full.runner.trim_time <= b.close_time <= _t(10, 5)):
            continue
        [x] = G.replay_day(history(), [y for y in bars if y.close_time <= b.close_time], CFG, TICK).signals
        assert x.runner is not None
        assert x.runner.stops == [m for m in full.runner.stops if m[0] <= b.close_time]  # live = backtest


def test_runner_target_must_be_beyond_the_trim():
    with pytest.raises(ValueError):
        GalaPaCfg(runner_target_r=D(2))
    assert GalaPaCfg().trim_at_target is True and GalaPaCfg().runner_trail_after_entry is False
