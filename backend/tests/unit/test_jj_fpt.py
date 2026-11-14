"""JJ F.P.T STRAT engine (app/engine/jj_fpt.py) — one test per rule of docs/JJ_FPT_RULES.md (#n)."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

from app.clock import ET
from app.config import JjFptCfg
from app.engine import jj_fpt as JJ
from app.engine.trade_plan import Direction

OPEN = datetime(2026, 11, 10, 9, 30, tzinfo=ET)


def bar(m: int, o: float, h: float, lo: float, c: float) -> JJ.JBar:
    """Bar opening m minutes after 09:30 (m = 0 is the opening candle)."""
    return JJ.JBar(OPEN + timedelta(minutes=m + 1), D(str(o)), D(str(h)), D(str(lo)), D(str(c)))


def cfg(**kw: object) -> JjFptCfg:
    return JjFptCfg(**kw)  # type: ignore[arg-type]


def flat_open(o: float = 100) -> list[JJ.JBar]:
    """A pre-open bar, a doji opening candle (no continuation) and 4 quiet minutes."""
    out = [bar(-1, o, o + 1, o - 1, o), bar(0, o, o + 1, o - 1, o)]
    out += [bar(m, o, o + 0.5, o - 0.5, o) for m in range(1, 5)]
    return out


def run(bars: list[JJ.JBar], c: JjFptCfg | None = None, **s: object) -> JJ.Replay:
    return JJ.replay(bars, 1, JJ.SessionInput("NY", OPEN, **s), c or cfg())  # type: ignore[arg-type]


# ---------------- continuation (#14 – #18) ----------------


def test_opening_candle_colour_breaking_previous_candle_is_a_continuation_25_38() -> None:
    bars = [bar(-1, 100, 101, 99, 100), bar(0, 100, 110, 99.5, 108)]  # green, closes above the previous high
    sig = run(bars).signals
    assert len(sig) == 1 and sig[0].kind == "CONTINUATION" and sig[0].direction is Direction.LONG
    assert (sig[0].stop, sig[0].take_profit) == (D(83), D(146)) and sig[0].tier == "BASE"


def test_opening_body_over_25_uses_50_76() -> None:
    bars = [bar(-1, 100, 101, 99, 100), bar(0, 100, 131, 99.5, 130)]
    s = run(bars).signals[0]
    assert (s.stop_pts, s.target_pts, s.tier) == (D(50), D(76), "BIG_OPEN")


def test_continuation_must_break_the_previous_candle() -> None:
    bars = [bar(-1, 100, 112, 99, 100), bar(0, 100, 110, 99.5, 108)]  # closes below the previous high
    assert run(bars).signals == []


def test_continuation_must_match_the_htf_bias_reverse_of_the_last_hours() -> None:
    bars = [bar(-1, 100, 101, 99, 100), bar(0, 100, 110, 99.5, 108)]
    assert run(bars, htf_bias=-1).signals == []
    assert len(run(bars, htf_bias=1).signals) == 1
    assert len(run(bars, cfg(htf_filter=False), htf_bias=-1).signals) == 1
    assert JJ.htf_bias(D(110), D(100)) == -1 and JJ.htf_bias(D(90), D(100)) == 1 and JJ.htf_bias(D(1), None) is None


def test_no_continuation_into_a_wick_rejecting_that_side() -> None:
    bars = [bar(-1, 100, 101, 99, 100), bar(0, 100, 115, 99.5, 105)]  # upper wick 10 ≥ body 5
    assert run(bars).signals == []
    assert len(run(bars, cfg(wick_rejection_filter=False)).signals) == 1


def test_more_continuations_on_a_break_of_structure_inside_5_minutes_only() -> None:
    bars = [bar(-1, 100, 101, 99, 100), bar(0, 100, 110, 99.5, 108)]
    bars += [bar(1, 108, 112, 107, 111), bar(2, 111, 111.5, 109, 110), bar(3, 110, 115, 110, 114)]  # swing high 112
    sig = run(bars).signals
    assert [x.kind for x in sig] == ["CONTINUATION", "CONTINUATION"] and sig[1].index == 4


def test_no_continuation_in_the_news_session() -> None:
    bars = [bar(-1, 100, 101, 99, 100), bar(0, 100, 110, 99.5, 108)]
    assert run(bars, continuation=False).signals == []


def test_6pm_continuation_only_toward_the_gap_fill_or_once_filled() -> None:
    bars = [bar(-1, 100, 101, 99, 100), bar(0, 100, 110, 99.5, 108)]
    assert run(bars, gap_prior_close=D(90)).signals == []  # gap up → fill is down; a long is against it
    assert len(run(bars, gap_prior_close=D(120)).signals) == 1  # gap down → long fills it
    assert len(run(bars, gap_prior_close=D(100)).signals) == 1  # the opening candle covered the prior close


# ---------------- reversion (#21 – #25) ----------------


def test_displacement_back_to_fair_with_room_30_is_25_38() -> None:
    bars = flat_open() + [bar(5, 140, 146, 139, 145), bar(6, 145, 145, 134, 135)]
    s = run(bars).signals
    assert len(s) == 1 and s[0].kind == "DISPLACEMENT" and s[0].direction is Direction.SHORT
    assert (s[0].stop_pts, s[0].target_pts, s[0].room) == (D(25), D(38), D(35))


def test_room_15_to_30_is_12_5_19_and_under_15_no_trade() -> None:
    mid = flat_open() + [bar(5, 125, 131, 124, 130), bar(6, 130, 130, 119, 120)]  # room 20
    s = run(mid).signals
    assert (s[0].stop_pts, s[0].target_pts, s[0].tier) == (D("12.5"), D(19), "SMALL_ROOM")
    assert run(mid, cfg(small_room_tier=False)).signals == []
    near = flat_open() + [bar(5, 115, 121, 114, 120), bar(6, 120, 120, 109, 110)]  # room 10
    assert run(near).signals == []


def test_displacement_needs_a_larger_body_closing_beyond_an_opposite_colour_wick() -> None:
    small = flat_open() + [bar(5, 140, 151, 139, 150), bar(6, 150, 150, 135, 141)]  # body 9 < 10
    assert run(small).signals == []
    inside = flat_open() + [bar(5, 140, 146, 139, 145), bar(6, 145, 145, 138, 139.5)]  # closes above the wick 139
    assert run(inside).signals == []
    same = flat_open() + [bar(5, 146, 147, 144, 145), bar(6, 145, 145, 134, 135)]  # previous candle red
    assert run(same).signals == []


def test_combined_candles_switch() -> None:
    bars = flat_open() + [bar(5, 140, 151, 139, 150), bar(6, 150, 150, 144, 145), bar(7, 145, 145, 137, 138)]
    assert run(bars).signals == []  # each red body < the green body
    s = run(bars, cfg(combine_candles=2)).signals
    assert len(s) == 1 and s[0].index == 8


def test_break_of_structure_on_a_close_beyond_the_last_swing() -> None:
    bars = flat_open() + [
        bar(5, 130, 132, 128, 131),
        bar(6, 131, 133, 126, 130),  # swing low 126 (body 1: no displacement)
        bar(7, 130, 130.5, 127.5, 129),  # confirms it (red, so the next red is no displacement)
        bar(8, 129, 129.5, 124, 125),  # closes below 126
    ]
    s = run(bars).signals
    assert len(s) == 1 and s[0].kind == "BREAK_OF_STRUCTURE" and s[0].index == 9


def test_only_toward_fair_longs_below() -> None:
    bars = flat_open() + [bar(5, 60, 61, 54, 55), bar(6, 55, 66, 55, 65)]
    s = run(bars, cfg(adapt_fair_price=False)).signals
    assert s[0].direction is Direction.LONG and s[0].take_profit == D(103)


# ---------------- losses (#26, #27) ----------------


def losing_cycles(n: int, p: float = 200) -> list[JJ.JBar]:
    out = flat_open()
    m = 5
    for _ in range(n):
        out += [
            bar(m, p, p + 6, p - 1, p + 5),  # green
            bar(m + 1, p + 5, p + 5.5, p - 3, p - 2),  # red displacement → short at p − 2, stop p + 23
            bar(m + 2, p - 2, p + 24, p - 2.5, p),  # stop hit
        ]
        m += 3
    return out


def test_after_two_losses_only_breaks_of_structure() -> None:
    rep = run(losing_cycles(4), cfg(adapt_fair_price=False))
    assert [x.outcome for x in rep.signals] == ["LOSS", "LOSS"]


def test_three_losses_in_a_row_end_the_session() -> None:
    rep = run(losing_cycles(5), cfg(adapt_fair_price=False, bos_only_after_losses=5))
    assert [x.outcome for x in rep.signals] == ["LOSS", "LOSS", "LOSS"]
    assert rep.stopped_at is not None and rep.notes == ["STOP_3_LOSSES"]


def test_a_win_resets_the_loss_count_and_stop_wins_a_shared_bar() -> None:
    bars = flat_open() + [bar(5, 140, 146, 139, 145), bar(6, 145, 145, 134, 135), bar(7, 135, 161, 96, 100)]
    assert run(bars).signals[0].outcome == "LOSS"  # one bar touches stop and target → stop first
    win = flat_open() + [bar(5, 140, 146, 139, 145), bar(6, 145, 145, 134, 135), bar(7, 135, 136, 96, 100)]
    assert run(win).signals[0].outcome == "WIN"


# ---------------- fair price (#7 – #12) ----------------


def test_fair_is_the_session_open() -> None:
    assert run(flat_open(101)).fair == D(101)


def test_news_day_open_continuing_away_makes_the_open_fair() -> None:
    away = [bar(-1, 100, 101, 99, 100), bar(0, 100, 106, 99.5, 105)]
    assert run(away, news_fair=D(95)).fair == D(100)
    back = [bar(-1, 100, 101, 99, 100), bar(0, 100, 100.5, 96, 97)]
    assert run(back, news_fair=D(95)).fair == D(95)


def test_asia_first_move_to_the_6pm_open_makes_it_fair() -> None:
    up = [bar(-1, 100, 101, 99, 100), bar(0, 100, 103, 99.5, 102)]
    assert run(up, alt_fair=D(110)).fair == D(110)
    down = [bar(-1, 100, 101, 99, 100), bar(0, 100, 100.5, 97, 98)]
    assert run(down, alt_fair=D(110)).fair == D(100)


def test_break_of_structure_away_from_fair_moves_it_to_the_consolidation() -> None:
    bars = flat_open() + [
        bar(5, 80, 81, 78, 79),
        bar(6, 79, 80, 76, 77),  # swing low 76
        bar(7, 77, 79, 77.5, 78.5),
        bar(8, 78, 78, 70, 71),  # breaks it, 29 pt below fair 100
    ]
    rep = run(bars, cfg(consolidation_bars=3))
    assert rep.fair_changes == [(9, D("78.5"))] and rep.fair == D("78.5")
    assert run(bars, cfg(adapt_fair_price=False)).fair_changes == []


def test_window_ends_after_90_minutes() -> None:
    bars = flat_open() + [bar(95, 140, 146, 139, 145), bar(96, 145, 145, 134, 135)]
    assert run(bars).signals == []
    assert len(run(bars, cfg(extend_under_trades=10)).signals) == 1  # #6: past 11:00 while < 10 trades


# ---------------- size (#28, #29) ----------------


def test_same_dollars_on_every_stop() -> None:
    args = (D("0.25"), D("0.5"), D("1.5"), 1)
    assert JJ.contracts_for(D(250), D(25), *args) == 4
    assert JJ.contracts_for(D(250), D(50), *args) == 2
    assert JJ.contracts_for(D(250), D("12.5"), *args) == 9
    assert JJ.contracts_for(D(10), D(25), *args) == 0
